# Absolute imports only

## Decision: ban every relative import, not just parent-relative ones

`[tool.ruff.lint]` selects `TID`, and
`[tool.ruff.lint.flake8-tidy-imports]` sets `ban-relative-imports = "all"`.
Both halves are needed: selecting `TID` alone leaves TID252 on its default
setting.

## Context: why it came up

The house standard is "absolute imports only — no relative paths". Ruff's
TID252 enforces that, but its default is `ban-relative-imports = "parents"`,
which flags `from ..thing import X` and lets `from .base import X` straight
through. Selecting `TID` and stopping there looks like the standard is
enforced while the most common form of relative import — the single-dot
sibling import — is still allowed.

## Alternatives considered

- **Leave TID unselected.** The standard would rest on review alone. Rejected:
  the point of the gate is that a linter catches what review forgets.
- **Select `TID` and take the `"parents"` default.** Measured on a sibling repo
  with existing relative imports: `"parents"` reports ≈49 violations, `"all"`
  reports 172. The 123-violation gap is entirely single-dot sibling imports —
  exactly the case the standard means to ban. Rejected: it enforces a rule
  nobody wrote.
- **`"all"`.** Chosen.

## Reasoning: why this option won

`"all"` is the only setting that matches the standard as written. It also
matches how this project's own code is already structured: `src/` and `tests/`
pass under `"all"` with no violations, so adopting it here costs nothing and
locks the shape in for every project generated from the template.

An absolute import names the module the same way from every file that imports
it, so a symbol can be grepped for by one spelling, and moving a module
produces an import error at the moved file rather than a silently different
resolution.

## Trade-offs accepted

A project adopting this template that already uses relative imports has work
to do. `ruff check --fix` will not do it: TID252's fix is classed **unsafe**,
so the migration needs `ruff check --fix --unsafe-fixes` followed by a run of
the test suite.

The fix is unsafe for a real reason. Rewriting `from .base import X` to
`from mypackage.base import X` hard-codes the package's name at the import
site, so it changes behaviour if the package is ever imported under a
different name — vendored under another namespace, or imported both as a
top-level package and as a submodule of something else. That is rare, and a
test run is enough to catch it, but it is why the rewrite is not applied by
plain `--fix`.

## Supersedes

Nothing. First record in this area.
