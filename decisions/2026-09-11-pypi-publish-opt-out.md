# PyPI publishing opt-out

## Decision: gate `publish` on a repository variable, defaulting to publish

`.github/workflows/release.yaml` adds `vars.PYPI_PUBLISH != 'false'` to the
`publish` job's condition. An unset variable publishes, so a project generated
from the template publishes with no configuration at all. The template
repository itself sets the variable to `false`.

## Context: why it came up

The template's own release of 0.1.1 (2026-09-11, run 34624877064) failed on
`pypa/gh-action-pypi-publish` with `invalid-publisher`: *valid token, but no
corresponding publisher*. The `pypi` environment exists on the repository, so
OIDC minted a token fine — PyPI simply has no trusted publisher whose claims
match `repo:<owner>/<repo>@<id>:environment:pypi` for a template that has no
distribution and never will. Every release the template cuts would end on a
red job.

The Releases explanation already said "a project that will never publish
should delete it". That instruction cannot apply to the template itself, which
has to keep the job working for the projects it generates.

## Alternatives considered

- **Compare `github.repository` against the template's name.** The obvious
  guard, and a trap specific to this repository. `./bootstrap`'s placeholder
  sweep rewrites the template's project name to the new one everywhere, so the
  guard would arrive in the generated project comparing against *its own*
  name and disable its publishing permanently — silently, as a skipped job.
- **A marker file in the tree** (`.no-publish`, or a `pyproject.toml` key).
  *Use this template* copies files, so the opt-out would follow the generated
  project and would depend on `./bootstrap` to remove it. That makes the
  default rest on a script only some users run: anyone who copies the template
  without bootstrapping inherits the opt-out.
- **`github.event.repository.is_template == false`.** Zero configuration and
  semantically exact — the template repository is flagged `isTemplate: true`,
  generated ones are not. Rejected as too clever: it reads as a check about
  repository metadata rather than about intent to publish, it gives a
  publishing project no way to turn the job off short of deleting it, and it
  changes behaviour if anyone ever flags a downstream repository as a template.
- **Opt-in (`vars.PYPI_PUBLISH == 'true'`).** Proposed first and rejected: it
  puts the configuration on the common case, and a generated project would be
  quietly non-publishing until someone noticed a skipped job.
- **Delete the `publish` job from the template.** Throws away the OIDC
  publishing wiring that is part of what the template is for.

## Reasoning

The opt-out has to live somewhere that cannot reach a repository generated
from the template. *Repository-scoped* variables have exactly that property:
*Use this template* copies files and branches, never variables, secrets,
environments or rulesets. So the default is structural rather than maintained
— no copy path carries the template's opt-out into a new project, and nothing
in `./bootstrap` has to remember to undo it.

The guarantee is about the repository scope specifically, not about variables
in general. `vars` also resolves *organization* variables, and generated
projects are required to live under `yo61`, so an org-level `PYPI_PUBLISH` set
to `false` would opt out every project at once. That is the one route by which
an opt-out can reach a generated repository, and it is a deliberate act by an
org admin rather than something inherited.

Defaulting to publish keeps the configuration on the exception. `!= 'false'`
rather than `== 'true'` makes the empty string that an unset variable
evaluates to the publishing case.

The prose that ships with this decision is written to survive the placeholder
sweep. A comment reading "there is no `<template-name>` distribution on PyPI"
is true in the template and a confident falsehood in every project generated
from it, because `sed` rewrites the name and nothing rewrites the claim around
it. Propagating files say "the template repository" instead, which holds on
both sides of the sweep.

## Trade-offs accepted

- The behaviour is set in repository settings, not in the tree, so reading
  `release.yaml` does not tell you whether this repository publishes. Hence
  the comment on the job and the notes in the Releases explanation and
  `README.md`.
- The comparison is string equality against `false`. Actions compares
  case-insensitively, so `False` and `FALSE` also opt out, but `0`, `no` and
  `off` publish. Anyone setting one of those gets the opposite of what they
  meant.
- A generated project still fails its first release until a PyPI trusted
  publisher exists — the opt-in variant would have fixed that too. The failure
  is at least loud and names the right cause.
- The switch is a `gh variable set`/`delete` away in either direction and
  leaves no history in the tree. Restoring the template's ability to publish
  is therefore cheap; so is losing the opt-out by accident, which puts the
  template's releases back on the red `invalid-publisher` that prompted this.
  Anyone with repository admin can do either, and nothing in the repository
  records that it happened.

## Supersedes

Nothing. Amends the "a project that will never publish should delete it"
guidance in `docs/site/content/docs/explanation/releases.mdx`.
