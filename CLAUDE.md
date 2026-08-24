# python-template

Project instructions. The global `~/.claude/CLAUDE.md` still applies; this
covers what it cannot know.

## Gate

`task dev:check` — ruff, ruff format --check, ty, pytest. Run it before every
commit. `task --list` shows everything else.

CI runs the prek hooks from `.pre-commit-config.yaml` rather than restating
them, so a local `task dev:hooks` is the same check CI runs.

## Lazy imports in `cli.py`

Every command module is imported *inside* `_build_app()`, never at module
scope. `main()` short-circuits on `__complete` and answers without building the
cyclopts App. Moving an import to module scope silently costs every tab-press;
`tests/test_cli.py::test_complete_fast_path_does_not_build_the_app` guards it.

## Commits

Conventional. Types: `build chore ci deps docs feat fix perf refactor revert
style test`. `deps` is non-standard and deliberate — it routes dependency
updates to a visible Dependencies changelog section, where `chore(deps)` would
be hidden and cut no release.

## Agent scaffolding

- `decisions/` — decision records. Grep it before making a choice that
  outlives today's task; add a record when you make a new one.
- `quality/criteria.md` — the criteria a task is checked against before it is
  called done.
- `docs/superpowers/` — specs and plans.

## Placeholders

Before `./bootstrap` runs, `pythontemplate` and `python-template` are live
values, not markers. Any new file must use those exact spellings or the
bootstrap smoke test will fail.
