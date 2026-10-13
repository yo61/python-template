# Python version matrix follows the development pin

## Decision: widen the pytest matrix in the same PR that bumps `.python-version`

When Renovate raises `.python-version` to a new minor Python, that PR also adds
the version to the `pytest` matrix in `.github/workflows/ci.yaml` and updates
the CI section of `README.md`. If the new version fails the matrix, close the
bump PR and keep `.python-version` on the previous minor until the dependencies
catch up. Do not merge the pin without the matrix entry.

## Context: why it came up

Renovate bumped `.python-version` from 3.14 to 3.15 (#58) and it merged on
green CI. The pin selects the interpreter for local development and the `lint`
job only; the matrix is listed by hand and stayed at 3.11–3.14. The result was
that the interpreter everyone develops on was outside the range CI tests.

The matrix comment already says to widen it by hand. Nothing tied that to the
event that makes it due.

## Alternatives considered

- **Have Renovate update the matrix too.** A custom regex manager could
  rewrite the list. Rejected: adding a supported Python is a support decision,
  and a newly released Python is the point where a dependency without wheels
  for it breaks `uv sync`. That needs a person to look at the result, which a
  bump that also widens the matrix would hide inside one green or red run.
- **Leave the matrix until a separate support review.** Leaves a gap of
  unknown length where local `task dev:check` is the only test on the pinned
  version, and CI cannot report a failure local runs miss.
- **Keep `.python-version` on the oldest supported Python.** Testing the floor
  locally is defensible, but it turns down every Renovate bump forever and
  means development never meets the new interpreter until users do.

## Reasoning

The bump PR is the one moment the gap opens, and it already arrives as a PR
that needs merging by hand. Making the matrix entry part of accepting it costs
one line and turns the new version's CI run into the check for whether the
pin should move at all. A project whose dependencies are not ready finds out
before the pin lands rather than after.

## Trade-offs accepted

- Merging a Python bump is no longer a single click; each project's bump PR
  needs the matrix line added by hand.
- One more matrix job per pull request for as long as the old floor is kept.
- uv can lag a CPython release: at 3.15.0 its managed downloads offered only
  3.15.0rc3, so CI tested the release candidate while a Mac with Homebrew's
  3.15.0 tested the final. Accepted as temporary; it clears when uv ships the
  final build.

## Supersedes

Nothing.
