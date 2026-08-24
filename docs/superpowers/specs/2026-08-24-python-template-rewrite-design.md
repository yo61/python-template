# python-template rewrite — design

Date: 2026-08-24
Status: approved, pending implementation plan

## Context

`yo61/python-template` is an unmodified clone of `BrianPugh/python-template`.
Of its 336 commits, 176 are Brian Pugh's, 158 are dependabot's, and one is
Robin's (a dependabot merge). Last substantive change: 2025-06-30.

Nothing in it matches how yo61 Python projects are actually built. The four
current Python repos — `jobhound`, `unifictl`, `gh-release-stats`,
`flux-homelab` — have converged on a shared toolchain that exists nowhere in
the template:

| | template (2025-06) | current repos (2026-08) |
|---|---|---|
| deps/venv | poetry + poetry-dynamic-versioning | uv + `uv.lock`, `UV_FROZEN=1` |
| build backend | poetry-core + Cython `build.py` | hatchling, `src/` layout |
| types | pyright | ty |
| lint | ruff, pydocstyle/numpy, 120 cols | ruff `E,F,I,UP,B,SIM,RUF`, 100 cols |
| task runner | none | Taskfile (`task dev:check`) |
| toolchain pin | none | `mise.toml` |
| versioning | git tags → dynamic | release-please + CHANGELOG + manifest |
| commits | unenforced | commitlint, conventional |
| CI actions | float on tags | SHA-pinned, `persist-credentials: false` |
| workflow audit | none | actionlint + zizmor |
| Python | `^3.9` | `>=3.11`, matrix 3.11–3.14 |
| docs | Sphinx + ReadTheDocs | Fumadocs → GitHub Pages (go-udap) |
| extras | Cython, Docker, Codecov | none |

This is a replacement, not an upgrade.

## Goals

- The template encodes the yo61 house toolchain so new projects inherit it
  without re-deriving it.
- The template repo is itself a working, CI-green project.
- CI proves the *generated* project works, not just the template.
- Docs ship as Fumadocs, structured after Diátaxis, published to GitHub Pages.

## Non-goals

- Supporting C extensions, Sphinx, ReadTheDocs, Docker, or Codecov. No current
  repo uses any of them.
- Preserving upstream git history. Explicitly waived.
- Shell-completion machinery or MCP scaffolding (see Deferred).

## Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | Full rewrite; discard upstream content and history | Nothing of yo61's is in it |
| D2 | GitHub template repo + `./bootstrap` script | Template stays a runnable project, so CI can test it; `copier` cannot |
| D3 | Flat CLI by default; `bootstrap` prompts for DDD layering | Layers are earned, but the prompt makes day-one adoption one keystroke |
| D4 | DDD layering documented in the shipped docs site | The template ships docs; this is what they are for |
| D5 | Fumadocs at `docs/site/`, Diátaxis sections, Pages deploy | Follows `go-udap`, the only in-repo docs-site precedent |
| D6 | Section named `explanation`, not `concepts` | Canonical Diátaxis; matches `homelab-docs` |
| D7 | CI shape follows `gh-release-stats`, not `jobhound` | Running prek hooks in CI means local and CI cannot drift |
| D8 | Ship `sync-lockfile` release job | Mandatory for any uv + release-please repo (see below) |

`isFork: false` on the GitHub repo, so it can be flipped to a template
repository. Its description ("Clone of BrianPugh/python-template") must change.

## Repo layout

```
.bootstrap-defaults          non-interactive answers, used by CI
bootstrap                    interactive init; deletes itself on success
CLAUDE.md                    project-level agent instructions
CHANGELOG.md
LICENSE                      Apache-2.0
README.md
Taskfile.yml
mise.toml
pyproject.toml
uv.lock
.python-version              3.13
.pre-commit-config.yaml
.release-please-manifest.json
release-please-config.json
commitlint.config.mjs
.github/
  dependabot.yml             uv · pre-commit · github-actions · npm(/docs/site)
  workflows/{ci,release,docs}.yaml
src/pythontemplate/
  __init__.py                __version__
  cli.py                     lazy get_app(), main(), __complete fast path
  commands/{__init__,hello}.py
  py.typed
tests/{test_cli,test_hello}.py
docs/
  site/                      Fumadocs (Next static export, pnpm)
  superpowers/{specs,plans}/
decisions/
quality/criteria.md
```

## Python core

`pyproject.toml`: uv + hatchling, `packages = ["src/pythontemplate"]`,
`requires-python = ">=3.11"`, Apache-2.0 with `license-files`.

- ruff: `line-length = 100`, `target-version = "py311"`,
  `select = ["E","F","I","UP","B","SIM","RUF"]`, `quote-style = "double"`.
  This is the jobhound/unifictl set. `gh-release-stats` additionally selects
  `N`, `S`, `W` and then needs per-file ignores to stay quiet; not worth
  inheriting into a template.
- ty: `[tool.ty.rules]` present but empty — strict by default.
- pytest: `testpaths = ["tests"]`,
  `addopts = "-ra --strict-markers --strict-config"`, plus the cyclopts
  `filterwarnings` ignore both existing CLIs carry.
- dev group: `pytest>=8`, `pytest-cov>=5`, `ruff>=0.6`, `ty>=0.0.1a8`,
  `hypothesis>=6`. Loose pins, as jobhound/unifictl.

### The lazy entry point

`cli.py` seeds the house pattern both CLIs use and that a template reader
would not invent:

- `_build_app()` imports every command module *inside the function body*.
- `get_app()` memoises it; `app()` proxies so tests can patch it.
- `main()` short-circuits on `sys.argv[1] == "__complete"` and dispatches
  straight to the completion handler, skipping the App build entirely.

In jobhound this saves ~38 ms of questionary/prompt_toolkit imports on every
tab-press. The template ships the pattern with one example command; it does
not ship the shell stubs.

## Quality gates

`Taskfile.yml` follows jobhound's: `dev:lint`, `dev:fmt`, `dev:fmt-check`,
`dev:typecheck`, `dev:test`, `dev:check`, `dev:hooks`, `dev:hooks-install`;
plus `docs:dev`, `docs:serve`, `docs:build` from go-udap; plus `dev:imports`
when DDD layering is enabled.

`.pre-commit-config.yaml`: the shared base hooks, then ruff / ty / pytest as
`local` hooks invoked via `uv run --no-sync` so their versions come from
`uv.lock` and there is no second `rev:` to keep aligned. commitlint at
`commit-msg`, pytest at `pre-push`, actionlint, zizmor.

**New:** `shellcheck` and `shfmt -i 2 -bn -ci -sr` hooks. The template ships a
bash script and no current repo lints shell.

### CI (`ci.yaml`)

| job | detail |
|---|---|
| `lint` | single Python; `j178/prek-action` with `SKIP: zizmor`; `uv sync --frozen` first so the `uv run --no-sync` hooks have a venv |
| `pytest` | matrix 3.11–3.14 |
| `bootstrap` | see Testing below |
| `test` | aggregator, `needs: [lint, pytest, bootstrap]`; the single name the branch ruleset requires |
| `commitlint` | `yo61/commitlint-github-action`, digest-pinned |
| `zizmor` | own job |

Chosen over jobhound's single `task dev:check` matrix, which runs ruff and ty
four times and restates the hook list in a second place.

## Release

release-please with `release-type: python`, `include-v-in-tag`,
`bump-minor-pre-major`, and the 13-entry `changelog-sections` map that makes
`deps` a visible section while hiding `chore`/`ci`/`refactor`/etc.

Token comes from the `SEMANTIC_RELEASE_APP` GitHub App, not `GITHUB_TOKEN`, so
the Release PR fires `pull_request` workflows and branch protection can pass.

Publishing: `uv build` + `pypa/gh-action-pypi-publish` via trusted publishing
against a `pypi` environment. No `dispatch-homebrew` — that is jobhound-specific.

### `sync-lockfile` (required, not optional)

release-please rewrites the version in `pyproject.toml` but knows nothing about
`uv.lock`, so the self-referencing editable pin goes stale and the next
`uv run` on `main` silently rewrites it (jobhound #66).

- Cannot be fixed with release-please `extra-files`: `uv lock` strips comments.
- Cannot use `git commit` from the runner: a `required_signatures` ruleset
  rejects unsigned commits and no GPG key is provisioned.

So the job runs `uv lock` on the release PR branch and pushes via the GraphQL
`createCommitOnBranch` mutation, which GitHub signs with the App-flow key. The
request is assembled with `jq --rawfile` and submitted via
`gh api graphql --input`, because inline `-f content=` exceeds `MAX_ARG_STRLEN`
once the lockfile passes ~95 KB, and `-f content=@file` does not expand for
GraphQL variables.

Every uv + release-please + signed-commits repo hits this. The template ships
the fix.

## Docs site

`docs/site/`, modelled on `go-udap`: Fumadocs + Next static export
(`output: 'export'`), pnpm, `trailingSlash: true`, `images.unoptimized`.

`basePath` defaults to `/<repo-name>` and is re-exported as
`NEXT_PUBLIC_BASE_PATH` / `NEXT_PUBLIC_SITE_URL` so client code can prefix the
static-search fetch and the OG-image and `llms.mdx` URLs. Local dev strips it
via `BASE_PATH=`. **This is the single most breakage-prone placeholder in the
template** — get it wrong and the site 404s its own assets only once deployed.

Carried over from go-udap: the `llms.txt`, `llms-full.txt` and
`llms.mdx/docs/[[...slug]]` routes (agent-native), and `pnpm-workspace.yaml`
with its security `overrides`.

`docs.yaml` builds on changes under `docs/site/**` and deploys to Pages on push
to `main`; PRs build without deploying.

### Diátaxis sections

Root `meta.json` order: `tutorials`, `how-to`, `reference`, `explanation`,
`contributing`. Each seeded with an `index.mdx`.

Two pages carry real content rather than placeholder text:

- `contributing/docs-style.mdx` — adapted from go-udap's existing style guide:
  the three archetypes (Procedure / Explainer / Reference), their canonical
  heading shapes, and the universal rules (no H1 in body, no `Step N —`
  prefixes, no standalone numbered H2s). Adapted, not copied: go-udap's
  text names `concepts/*` as the Explainer example, which must become
  `explanation/*` here per D6.
- `how-to/add-ddd-layers.mdx` — what import-linter does, the layer and
  forbidden contract syntax, why the `cli` module must be excluded from the
  layers list, and the fact that import-linter is scope-blind so a lazy
  function-scoped import is caught exactly like a top-level one.

## Bootstrap

`bootstrap`: bash, `set -euo pipefail`, shellcheck- and shfmt-clean.

Prompts (defaults derived from the git remote):

```
Project name  [my-tool]
Package name  [my_tool]
CLI command   [my-tool]
Description
Author        [Robin Bowes]
DDD layering? [y/N]
```

Actions:

1. Rewrite placeholders across ~14 files (pyproject, README, Taskfile,
   LICENSE, release-please-config, CLAUDE.md, workflows, `next.config.mjs`,
   `layout.shared.tsx`, docs `index.mdx`, tests).
2. `git mv src/pythontemplate src/<pkg>`.
3. Set the Fumadocs `basePath` to `/<repo>`.
4. Reset `CHANGELOG.md` and `.release-please-manifest.json` to `0.0.0`.
5. Clear template-specific `docs/superpowers/specs/` and `decisions/` content
   (this spec must not propagate into every generated project).
6. On `y`: create `commands/ application/ domain/ infrastructure/`, uncomment
   the `[tool.importlinter]` block, add `import-linter` to the dev group, add
   `dev:imports` to the Taskfile and the matching prek hook.
7. `uv sync`, `prek install --hook-type pre-commit --hook-type commit-msg
   --hook-type pre-push`.
8. Delete itself *and* `.bootstrap-defaults`, then commit.

Non-interactive mode (`--defaults`, optionally `--ddd`) reads
`.bootstrap-defaults` so CI can drive it.

## Agent scaffolding

The folder system the global CLAUDE.md describes, which jobhound already uses:

- `decisions/` — one `YYYY-MM-DD-topic.md` per decision affecting more than a
  single task.
- `quality/criteria.md` — the quality gate, seeded with the format header and
  no criteria. Criteria are earned from real review findings; jobhound's file
  says so explicitly and the template should not pre-populate guesses.
- `docs/superpowers/{specs,plans}/` — brainstorming and planning output.

Each seeded with a short README explaining the convention rather than dummy
content, and cleared of template-specific files by `bootstrap` (step 5).

A tracked root `CLAUDE.md` covers what the global file cannot know: that
`task dev:check` is the gate, the lazy-import rule in `cli.py`, and the
conventional-commit type list including `deps`.

## Testing

- The template repo is a working project: `task dev:check` is green on it.
- **`bootstrap` CI job:** copy the tree to a temp dir, run
  `./bootstrap --defaults` and `./bootstrap --defaults --ddd` in two copies,
  then `task dev:check` in each output, and `pnpm build` on one.
  This is the job that stops the template rotting — the classic failure is a
  new file whose placeholder nobody added to the rewrite list, which is
  invisible until someone generates a project from it.
- `tests/test_cli.py` monkeypatches `sys.argv` and calls `main()`, exercising
  the production argv-reading branch and the `__complete` fast path.

## Assumptions

Reversible, but recorded:

- `requires-python = ">=3.11"`, matrix to 3.14 — follows all four repos rather
  than the global CLAUDE.md's "Runtime: 3.14".
- Loose dev-group pins, as jobhound/unifictl, not `gh-release-stats`' exact `==`.
- Apache-2.0 (jobhound, unifictl) over MIT (gh-release-stats).
- A tracked root `CLAUDE.md`. **This is an addition, not a distillation** — no
  current repo tracks one; all four have untracked `.claude/`.

## Deferred

- Shell-completion stubs and `completion install` (jobhound). The
  `__complete` fast path stays as the hook to build on.
- MCP scaffolding: jobhound's optional `mcp` extra and second entry point.

## Follow-ups (other repos)

Raised during design; not part of this work. Tracked as
[yo61/jobhound#166](https://github.com/yo61/jobhound/issues/166) and
[yo61/go-udap#210](https://github.com/yo61/go-udap/issues/210).

### jobhound: adopt import-linter (yo61/jobhound#166)

Measured, not assumed — unifictl's two contracts run against jobhound's tree:

- `DDD layers` (`commands → application → domain`) **KEPT**. 90 files, 318
  dependencies, zero violations. Adopting it is a pure config addition.
- `Infrastructure imports neither domain nor application` **BROKEN**, 8
  violations: `repository → domain.opportunities`, `meta_io → domain.slug_value`,
  `storage.git_local → application.snapshots`, and others.

Recommendation: adopt the layers contract, reject the forbidden one. In
unifictl `infrastructure` is an isolated private-API client mirroring an
external contract; in jobhound it is the persistence layer, and a repository
that cannot import the entities it persists is not a repository. The forbidden
contract is a unifictl-specific constraint, not a house rule — and the template
should not present it as one.

### go-udap: docs structure and style (yo61/go-udap#210)

go-udap does not need bringing into line — it is the most developed statement
of the house style, and `contributing/docs-style.mdx` is the only style guide
in the fleet. Reconciliation needed in two places:

- go-udap names its explanation section `concepts`; homelab-docs and this
  template use `explanation`. Renaming go-udap's also means updating
  `docs-style.mdx`, which references "every `concepts/*` page", the root
  `meta.json`, and any inbound links.
- Both sites already agree on ordering (`tutorials, how-to, reference, …`);
  go-udap adds `contributing`, which the template adopts.
