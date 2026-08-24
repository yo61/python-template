# python-template

A template for yo61 Python projects. It ships a package skeleton, a
`cyclopts`-based CLI, and a working toolchain for linting, type checking,
testing, releases and docs, so a new project starts with the gate already in
place instead of being built up commit by commit.

Full documentation: <https://yo61.github.io/python-template/>

## Getting started

Create a new repository from this template — either the **Use this template**
button on GitHub, or:

```bash
gh repo create my-tool --template yo61/python-template --private --clone
cd my-tool
```

Then run the bootstrap script:

```bash
./bootstrap
```

It asks for a project name, package name, CLI command name, description and
author, then rewrites every file, commits the result, and deletes itself.
`./bootstrap --defaults` skips the prompts and uses `.bootstrap-defaults`
instead, which is what CI uses to smoke-test the template itself.

Alongside the placeholder rewrite it strips the parts that only make sense in
the template: `bootstrap` and `.bootstrap-defaults`, `scripts/test-bootstrap.sh`
and its `bootstrap` CI job, the design records under `docs/superpowers/`, and
the `Placeholders` section of `CLAUDE.md`. It replaces this README with a short
one for the new project and rewrites the `LICENSE` copyright line to the
current year and the author you gave it.

Two things worth knowing before you run it:

- **It is destructive and one-way.** It rewrites files in place and `git
  commit`s the result. There's no undo short of `git reset --hard && git clean
  -fd` before the commit lands; the script prints that hint if it fails
  part-way through.
- `scripts/test-bootstrap.sh` (the smoke test CI runs) generates its test
  projects from the **committed** tree via `git archive HEAD`, not the
  working directory. If you're iterating on `bootstrap` itself, commit your
  changes before running the smoke test, or you'll get a false pass against
  the previous commit.

Once bootstrap has run, the next step is:

```bash
task dev:check
```

## Toolchain

| Purpose | Tool |
| --- | --- |
| Dependency and virtualenv management | [`uv`](https://docs.astral.sh/uv/) |
| Build backend | [`hatchling`](https://hatch.pypa.io/) |
| Lint and format | [`ruff`](https://docs.astral.sh/ruff/) |
| Static types | [`ty`](https://github.com/astral-sh/ty) |
| Tests | [`pytest`](https://docs.pytest.org/) |
| CLI framework | [`cyclopts`](https://cyclopts.readthedocs.io/) |
| Task runner | [`Taskfile`](https://taskfile.dev/) |
| Tool version pinning | [`mise`](https://mise.jdx.dev/) |
| Git hooks | [`prek`](https://github.com/j178/prek) |
| Releases | [`release-please`](https://github.com/googleapis/release-please) |
| Commit linting | [`commitlint`](https://commitlint.js.org/) |
| Docs site | [Fumadocs](https://fumadocs.dev/) |

`mise.toml` pins the versions of `uv`, `task`, `node` and `pnpm` so a fresh
clone gets the same toolchain without a separate install step, provided
`mise` is active in the shell.

## Tasks

`task --list` shows every task with its description. The ones you'll use
most:

- `task dev:check` — the gate: `ruff check`, `ruff format --check`, `ty
  check`, `pytest`. Run it before every commit; CI runs the same checks via
  the prek hooks in `.pre-commit-config.yaml`.
- `task dev:lint` / `task dev:fmt` / `task dev:fmt-check` / `task
  dev:typecheck` / `task dev:test` — the individual gate steps, for when you
  only need one of them.
- `task dev:hooks` — run every prek hook against every file, the same set CI
  runs.
- `task dev:hooks-install` — install the pre-commit, commit-msg and pre-push
  git hooks locally.

## Agent scaffolding

`CLAUDE.md` holds the project instructions an agent reads first. Three
directories back it up, and all three ship into the generated project:

- `decisions/` — decision records for choices that outlive a single task.
- `quality/criteria.md` — the criteria a task is checked against before it is
  called done.
- `docs/superpowers/` — specs and plans. The template's own are removed by
  `bootstrap`; the `README.md` explaining the layout stays.

## Docs site

The docs live in `docs/site/`, built with Fumadocs and deployed to GitHub
Pages at <https://yo61.github.io/python-template/> on every push to `main`.

- `task docs:dev` — run the site locally with hot reload at
  `http://localhost:3000`, with the GitHub Pages `basePath` stripped so
  assets resolve at the root.
- `task docs:serve` — production-build the site without the `basePath` and
  serve it locally, close to what a reader gets in production.
- `task docs:build` — production build with the real `/python-template`
  `basePath`, matching what CI builds.

## DDD layering

`./bootstrap` asks `DDD layering? [y/N]`. Answering yes creates
`application/`, `domain/` and `infrastructure/` packages alongside the flat
`commands/` package, uncomments an `import-linter` contract in
`pyproject.toml` that enforces the layering as a build failure rather than a
convention, and wires a `dev:imports` task and matching prek hook into the
gate. Answering no (the default) leaves the flat layout in place — start flat
and add layers later if the domain logic grows enough to justify it. See
[How to add DDD layers](https://yo61.github.io/python-template/how-to/add-ddd-layers)
for the full walkthrough, including the gotchas around lazy imports in
`cli.py` and where the import-linter contract should and shouldn't be
tightened.

## CI

Every pull request runs lint, the pytest matrix (Python 3.11 through 3.14),
and a bootstrap smoke test that generates two projects from the template
(one flat, one with DDD layering) and runs the full gate on each, catching
any file that uses a placeholder the bootstrap script doesn't know about.
`commitlint` and `zizmor` run as separate checks. `release-please` and
Dependabot handle releases and dependency updates.

## Releases

Two things have to be true before the Release workflow can do anything:

- **The repository has to live under the `yo61` org.** `release.yaml` gates
  its first job on `github.repository_owner == 'yo61'`, so anywhere else it
  runs, reports success, and does nothing. Fork it elsewhere and that line is
  the one to change.
- **The secrets and the environment have to exist.** The workflow mints a
  GitHub App token from `SEMANTIC_RELEASE_APP_CLIENT_ID` and
  `SEMANTIC_RELEASE_APP_PRIVATE_KEY`, and publishes from a `pypi` environment
  using PyPI trusted publishing. Without the two secrets the release PR is
  never opened; without the environment (and a matching trusted publisher on
  PyPI) the publish step fails.
