# python-template Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the upstream `BrianPugh/python-template` clone with a yo61 house template — a runnable Python project carrying the toolchain that `jobhound`, `unifictl` and `gh-release-stats` converged on, plus a Fumadocs site and a self-testing bootstrap script.

**Architecture:** The repo *is* a working project, not a set of `.jinja` stencils, so CI can lint, type-check and test it directly. Placeholders are therefore **real valid values** (`pythontemplate`, `python-template`) that `./bootstrap` rewrites by exact string substitution, never `{{MARKER}}` tokens. A CI job generates two projects from the template and runs the full gate on both, which is what stops the template rotting.

**Tech Stack:** uv · hatchling · ruff · ty · pytest · cyclopts · Taskfile · mise · prek · release-please · commitlint · Fumadocs (Next static export, pnpm) · GitHub Pages

**Spec:** `docs/superpowers/specs/2026-08-24-python-template-rewrite-design.md`

## Global Constraints

- `requires-python = ">=3.11"`; CI matrix `["3.11", "3.12", "3.13", "3.14"]`.
- ruff: `line-length = 100`, `target-version = "py311"`,
  `select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]`, `quote-style = "double"`.
- Licence Apache-2.0 with `license-files = ["LICENSE"]`.
- All GitHub Actions SHA-pinned with a `# vX.Y.Z` comment; every `checkout` sets
  `persist-credentials: false` unless it must push.
- Bash: `set -euo pipefail`; must pass `shellcheck` and
  `shfmt -i 2 -bn -ci -sr -d`. Use `command -v`, never `which`.
- Conventional commits. Types allowed: `build chore ci deps docs feat fix perf
  refactor revert style test`. `subject-case` disabled.
- **Never commit to `main`.** All work on branch `rewrite-template`.
- Google-style docstrings on public APIs; functions ≤100 lines, complexity ≤8.

### Placeholder tokens

`bootstrap` rewrites these exact strings. They are valid values, so the template
runs as-is. Any new file added to the template MUST use these spellings or the
bootstrap smoke test (Task 13) will catch the omission.

| token | meaning | example replacement |
|---|---|---|
| `pythontemplate` | Python package name (importable identifier) | `my_tool` |
| `python-template` | repo / project / distribution name (kebab) | `my-tool` |
| `A template for yo61 Python projects.` | description | user-supplied |
| `Robin Bowes` | author | user-supplied |

### Verified action pins

Verified against the GitHub API on 2026-08-24; each SHA resolves to the tag in
its comment. Re-verify if implementation slips by more than a week.

```
actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1              # v7.0.1
astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d            # v10.0.1
go-task/setup-task@a00fbb05ce67b35648be3c78cbc9fd85354c757e            # v2.2.0
j178/prek-action@4e14d07f9231acabce116ccfca13b13dd9755ece              # v3.0.0
zizmorcore/zizmor-action@3dc1ecc9bcb9e94e9b2c709687979e1298497054      # v0.6.2
actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1  # v3.2.0
googleapis/release-please-action@45996ed1f6d02564a971a2fa1b5860e934307cf7  # v5.0.0
pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33   # v1.14.2
pnpm/action-setup@0977fd99725f1db4007ccb2928dbb4e90d06cc86             # v6.0.10
actions/setup-node@820762786026740c76f36085b0efc47a31fe5020            # v7.0.0
actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d       # v6.0.0
actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9 # v5.0.0
actions/deploy-pages@cd2ce8fcbc39b97be8ca5fce6e763baed58fa128          # v5.0.0
yo61/commitlint-github-action@501ff7bb31eb7133c871318c877d0e43cd1ff500 # v6.3.1
```

`setup-uv` v10 is a major bump from the v9 used across the fleet. Its only
breaking change disables caching on `pull_request_target`, `workflow_run` and
`release` events; our workflows use `pull_request` and `push`, so it is safe.

**Resolved 2026-08-24.** `yo61/commitlint-github-action` was pinned two
different ways across the fleet: jobhound at `31e5e045` (the commit the
annotated `v6.3.0` tag targets) and unifictl/gh-release-stats at `501ff7bb`,
commented `v6.3.0` but actually two hours later and untagged.

`501ff7bb` is the better content — it pins the runtime image by digest instead
of the mutable `:6.3.0` tag, so a downstream SHA pin cannot be worked around by
repointing the image. It has now been tagged **`v6.3.1`** (annotated, target
`501ff7bb`), so the template pins a real tag with an accurate comment and
Dependabot has something to track from.

Upstream `wagoid/commitlint-github-action` is confirmed dead: last commit
2025-01-14, no releases ever.

Note the trade-off the digest pin buys: the image freezes the npm resolution.
The fork declares `@commitlint/cli ^21.2.1`, but that resolved when the image
was built (2026-08-11), so it runs 21.2.1 rather than the current 21.2.2.
Bumping commitlint in CI now means rebuilding the image and moving the digest —
it will not drift in on its own. The prek hook is unaffected: it installs
`@commitlint/config-conventional@^21.2.0` at hook-install time and so already
runs 21.2.2.

---

## Phase 1 — Foundation

### Task 1: Orphan reset and repo skeleton

**Files:**
- Delete: everything currently tracked except the two docs added on this branch
- Create: `LICENSE`, `.gitignore`, `README.md`
- Preserve: `docs/superpowers/specs/2026-08-24-python-template-rewrite-design.md`, `docs/superpowers/plans/2026-08-24-python-template-rewrite.md`

**Interfaces:**
- Produces: a clean tree on an orphan branch that every later task builds on.

The spec and this plan currently live on a branch off the *old* `main`.
`git checkout --orphan` starts from the current index and the next step is
`git rm -rf .`, which would delete them. Copy them out first.

- [ ] **Step 1: Copy the two design docs out of the tree**

```bash
mkdir -p /tmp/tmpl-carry
cp docs/superpowers/specs/2026-08-24-python-template-rewrite-design.md /tmp/tmpl-carry/
cp docs/superpowers/plans/2026-08-24-python-template-rewrite.md /tmp/tmpl-carry/
ls -1 /tmp/tmpl-carry/   # expect exactly 2 files
```

- [ ] **Step 2: Create the orphan branch and empty the tree**

```bash
git checkout --orphan template-v2
git rm -rf --quiet .
git status --short   # expect no staged entries
ls -A | grep -v '^\.git$' || echo "tree is empty"
```

- [ ] **Step 3: Restore the design docs**

```bash
mkdir -p docs/superpowers/specs docs/superpowers/plans
cp /tmp/tmpl-carry/2026-08-24-python-template-rewrite-design.md docs/superpowers/specs/
cp /tmp/tmpl-carry/2026-08-24-python-template-rewrite.md docs/superpowers/plans/
```

- [ ] **Step 4: Write `.gitignore`**

```gitignore
.venv/
__pycache__/
*.egg-info/
.pytest_cache/
.ruff_cache/
.ty_cache/
.DS_Store
dist/
build/
```

- [ ] **Step 5: Write `LICENSE`**

Apache-2.0 full text, copyright line `Copyright 2026 Robin Bowes`.

```bash
curl -fsSL https://www.apache.org/licenses/LICENSE-2.0.txt -o LICENSE
grep -c "Apache License" LICENSE   # expect >= 1
```

- [ ] **Step 6: Write a minimal `README.md`**

Full README lands in Task 15; this is enough to make the tree coherent.

```markdown
# python-template

A template for yo61 Python projects.

Click **Use this template**, clone the result, then run `./bootstrap`.
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: reset template to empty tree

Discards the upstream BrianPugh/python-template history. Nothing in it
matched yo61 practice; see docs/superpowers/specs/ for the design."
```

---

### Task 2: Python package and pyproject

**Files:**
- Create: `pyproject.toml`, `src/pythontemplate/__init__.py`, `src/pythontemplate/py.typed`, `src/pythontemplate/commands/__init__.py`, `src/pythontemplate/commands/hello.py`
- Test: `tests/test_hello.py`

**Interfaces:**
- Produces: `pythontemplate.__version__: str`; `pythontemplate.commands.hello.run(name: str = "world", *, shout: bool = False) -> str`.
  Task 3's `cli.py` registers `run` as the `hello` command.
  `run` **returns** its string rather than printing, so it is testable without
  capsys; the CLI layer prints it.

- [ ] **Step 1: Write the failing test**

`tests/test_hello.py`:

```python
"""Tests for the example `hello` command."""

from pythontemplate.commands.hello import run


def test_hello_defaults_to_world():
    assert run() == "Hello, world!"


def test_hello_accepts_a_name():
    assert run("Robin") == "Hello, Robin!"


def test_hello_shout_uppercases():
    assert run("Robin", shout=True) == "HELLO, ROBIN!"


def test_hello_rejects_empty_name():
    import pytest

    with pytest.raises(ValueError, match="name must not be empty"):
        run("   ")
```

- [ ] **Step 2: Run the test and watch it fail**

Run: `uv run pytest tests/test_hello.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'pythontemplate'`.

- [ ] **Step 3: Write `pyproject.toml`**

```toml
[project]
name = "python-template"
version = "0.0.0"
description = "A template for yo61 Python projects."
readme = "README.md"
license = "Apache-2.0"
license-files = ["LICENSE"]
requires-python = ">=3.11"
authors = [{ name = "Robin Bowes" }]
dependencies = [
    "cyclopts>=4.11",
]

[project.scripts]
python-template = "pythontemplate.cli:main"

[dependency-groups]
dev = [
    "hypothesis>=6",
    "pytest>=8",
    "pytest-cov>=5",
    "ruff>=0.6",
    "ty>=0.0.1a8",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pythontemplate"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]

[tool.ruff.format]
quote-style = "double"

[tool.ty.rules]
# strict-by-default; tighten as needed

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers --strict-config"
# tests/test_cli.py monkeypatches sys.argv and calls main(), which invokes
# app() with no tokens so cyclopts reads the replaced argv. That exercises the
# production argv-reading branch; cyclopts' stack inspection cannot tell it
# from a forgotten `app([])` and warns. False positive.
filterwarnings = [
    "ignore:Cyclopts application invoked without tokens.*:UserWarning",
]

# Uncomment together with the layer packages when adopting DDD layering.
# See docs/site/content/docs/how-to/add-ddd-layers.mdx
# [tool.importlinter]
# root_package = "pythontemplate"
#
# [[tool.importlinter.contracts]]
# name = "DDD layers"
# type = "layers"
# layers = [
#     "pythontemplate.commands",
#     "pythontemplate.application",
#     "pythontemplate.domain",
# ]
```

- [ ] **Step 4: Write the package**

`src/pythontemplate/__init__.py`:

```python
"""A template for yo61 Python projects."""

__version__ = "0.0.0"
```

`src/pythontemplate/commands/__init__.py`:

```python
"""Command implementations, one module per CLI verb."""
```

`src/pythontemplate/py.typed`: empty file.

`src/pythontemplate/commands/hello.py`:

```python
"""The example `hello` command."""

from __future__ import annotations


def run(name: str = "world", *, shout: bool = False) -> str:
    """Build a greeting.

    Returns the string rather than printing it so the behaviour is testable
    without capturing stdout. The CLI layer does the printing.

    Args:
        name: Who to greet. Must contain at least one non-space character.
        shout: Uppercase the whole greeting.

    Returns:
        The greeting.

    Raises:
        ValueError: If `name` is empty or only whitespace.
    """
    if not name.strip():
        raise ValueError("name must not be empty")
    greeting = f"Hello, {name}!"
    return greeting.upper() if shout else greeting
```

- [ ] **Step 5: Run the tests and watch them pass**

```bash
uv sync
uv run pytest tests/test_hello.py -q
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock src tests
git commit -m "feat: add package skeleton with example hello command"
```

---

### Task 3: CLI with lazy app build and `__complete` fast path

**Files:**
- Create: `src/pythontemplate/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `pythontemplate.commands.hello.run` (Task 2), `pythontemplate.__version__`.
- Produces: `cli.get_app() -> cyclopts.App` (memoised), `cli.app(*args, **kwargs)`
  proxy, `cli.main() -> None`. `main` is the `[project.scripts]` entry point.

This is the house pattern from `jobhound` and `unifictl`: every command module is
imported *inside* `_build_app()`, so `__complete` can answer without paying for
them. In jobhound that saves ~38 ms per tab-press.

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:

```python
"""Tests for the CLI entry point."""

import sys

import pytest

from pythontemplate import cli


@pytest.fixture(autouse=True)
def _reset_app_cache():
    """Clear the memoised App so each test builds a fresh one."""
    cli._app_cache = None
    yield
    cli._app_cache = None


def test_hello_command_prints_greeting(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["python-template", "hello", "Robin"])
    cli.main()
    assert capsys.readouterr().out.strip() == "Hello, Robin!"


def test_shout_flag_is_wired(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["python-template", "hello", "Robin", "--shout"])
    cli.main()
    assert capsys.readouterr().out.strip() == "HELLO, ROBIN!"


def test_empty_name_exits_cleanly_without_traceback(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["python-template", "hello", "  "])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "name must not be empty" in err
    assert "Traceback" not in err


def test_complete_fast_path_does_not_build_the_app(capsys, monkeypatch):
    """The whole point of the fast path: no App, no command imports."""
    monkeypatch.setattr(sys, "argv", ["python-template", "__complete", "hel"])

    def _explode():
        raise AssertionError("__complete must not build the cyclopts App")

    monkeypatch.setattr(cli, "_build_app", _explode)
    cli.main()
    assert "hello" in capsys.readouterr().out


def test_get_app_is_memoised():
    assert cli.get_app() is cli.get_app()
```

- [ ] **Step 2: Run the test and watch it fail**

Run: `uv run pytest tests/test_cli.py -q`
Expected: `ImportError: cannot import name 'cli' from 'pythontemplate'`.

- [ ] **Step 3: Write `src/pythontemplate/cli.py`**

```python
"""CLI entry point. Commands are imported lazily — see `_build_app`."""

from __future__ import annotations

import sys
from typing import Any

_TOP_LEVEL_COMMANDS = ("hello",)


def _build_app() -> Any:
    """Build the fully-wired cyclopts App.

    Command modules are imported here rather than at module scope so that
    `import pythontemplate.cli` stays cheap and the `__complete` fast path in
    `main` never pays for them.
    """
    from cyclopts import App

    from pythontemplate import __version__
    from pythontemplate.commands import hello as cmd_hello

    app = App(
        name="python-template",
        help="A template for yo61 Python projects.",
        version=__version__,
    )

    def hello(name: str = "world", *, shout: bool = False) -> None:
        """Greet someone.

        Args:
            name: Who to greet.
            shout: Uppercase the greeting.
        """
        print(cmd_hello.run(name, shout=shout))

    app.command(hello, name="hello")
    app.command(_complete, name="__complete", show=False)
    return app


def _complete(*tokens: str) -> None:
    """Emit completion candidates, one per line. Quoting is the shell's job."""
    prefix = tokens[-1] if tokens else ""
    for candidate in _TOP_LEVEL_COMMANDS:
        if candidate.startswith(prefix):
            print(candidate)


_app_cache: Any = None


def get_app() -> Any:
    """Return the cyclopts App, building it on first call."""
    global _app_cache
    if _app_cache is None:
        _app_cache = _build_app()
    return _app_cache


def app(*args: Any, **kwargs: Any) -> Any:
    """Proxy so the lazy build stays transparent to callers and tests."""
    return get_app()(*args, **kwargs)


def main() -> None:
    """Entry point. Turns known exceptions into clean stderr lines, exit 1."""
    if len(sys.argv) >= 2 and sys.argv[1] == "__complete":
        _complete(*sys.argv[2:])
        return

    try:
        app()
    except ValueError as exc:
        print(f"python-template: {exc}", file=sys.stderr)
        sys.exit(1)
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `uv run pytest -q`
Expected: 9 passed.

- [ ] **Step 5: Verify the fast path really is faster**

```bash
uv run python -X importtime -c "import pythontemplate.cli" 2>&1 | tail -3
```
Expected: no `cyclopts` in the import list — `cli` imports it only inside
`_build_app`. If cyclopts appears, an import escaped to module scope.

- [ ] **Step 6: Commit**

```bash
git add src/pythontemplate/cli.py tests/test_cli.py
git commit -m "feat: add CLI entry point with lazy app build and __complete fast path"
```

---

## Phase 2 — Quality gates

### Task 4: Toolchain pins and Taskfile

**Files:**
- Create: `mise.toml`, `.python-version`, `Taskfile.yml`

**Interfaces:**
- Produces: `task dev:check` — the single gate name every later task and the
  bootstrap smoke test invokes.

- [ ] **Step 1: Write `.python-version`**

```
3.13
```

- [ ] **Step 2: Write `mise.toml`**

```toml
[tools]
uv = "0.11"
task = "3"
node = "22"
pnpm = "11"

[env]
# Stop ad-hoc `uv run` from rewriting uv.lock. The lockfile changes
# deliberately, via `uv lock` or the release-please sync-lockfile job.
UV_FROZEN = "1"
_.python.venv = ".venv"
```

- [ ] **Step 3: Write `Taskfile.yml`**

```yaml
version: "3"
silent: true

env:
  UV_FROZEN: "1"

tasks:
  default:
    desc: List available tasks
    cmds:
      - task --list

  dev:lint:
    desc: Run ruff check
    cmds:
      - uv run ruff check src tests

  dev:fmt:
    desc: Apply ruff format
    cmds:
      - uv run ruff format src tests

  dev:fmt-check:
    desc: Check formatting without rewriting
    cmds:
      - uv run ruff format --check src tests

  dev:typecheck:
    desc: Run ty type checker
    cmds:
      - uv run ty check src

  dev:test:
    desc: Run the pytest suite
    cmds:
      - uv run pytest

  dev:check:
    desc: Full quality gate — lint, format-check, typecheck, tests
    cmds:
      - task: dev:lint
      - task: dev:fmt-check
      - task: dev:typecheck
      - task: dev:test

  dev:hooks:
    desc: Run all prek hooks against every file
    cmds:
      - prek run --all-files

  dev:hooks-install:
    desc: Install git hooks (pre-commit, commit-msg, pre-push)
    cmds:
      - prek install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push

  docs:dev:
    desc: Run the Fumadocs site locally with hot reload at http://localhost:3000.
      Strips the GitHub Pages basePath so assets resolve under root.
    dir: docs/site
    cmds:
      - BASE_PATH= pnpm dev

  docs:serve:
    desc: Production-build the site without basePath and serve it locally.
    dir: docs/site
    cmds:
      - BASE_PATH= SITE_URL=http://localhost:3000 pnpm build
      - pnpm start

  docs:build:
    desc: Production build with the /python-template basePath, matching CI.
    dir: docs/site
    cmds:
      - pnpm build
```

- [ ] **Step 4: Verify the gate is green**

Run: `task dev:check`
Expected: ruff clean, ty clean, 9 tests pass.

- [ ] **Step 5: Commit**

```bash
git add mise.toml .python-version Taskfile.yml
git commit -m "build: add mise toolchain pins and Taskfile quality gate"
```

---

### Task 5: prek hooks and commitlint

**Files:**
- Create: `.pre-commit-config.yaml`, `commitlint.config.mjs`

**Interfaces:**
- Consumes: `task dev:check` (Task 4) is the CI equivalent; hooks must not diverge.
- Produces: the hook set that `j178/prek-action` runs in CI (Task 6).

ruff, ty and pytest run as `local` hooks through `uv run --no-sync`, so their
versions come from `uv.lock` and there is no second `rev:` to keep aligned.
This is the pattern all three current repos use; gh-release-stats' comment
records why (a prek pin once lagged the project ruff by nine minor versions).

- [ ] **Step 1: Write `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      # Whitespace / line endings
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: mixed-line-ending
        args: [--fix=lf]
      # File integrity
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: check-case-conflict
      - id: check-symlinks
      # Executables / shebangs
      - id: check-executables-have-shebangs
      - id: check-shebang-scripts-are-executable
      # Parseable config
      - id: check-yaml
      - id: check-toml
      - id: check-json

  # ruff, ty and pytest run via `uv run` so their versions are single-sourced
  # from uv.lock — the same binaries CI runs. No second `rev:` to keep aligned.
  - repo: local
    hooks:
      - id: ruff-check
        name: ruff check
        entry: uv run --no-sync ruff check --fix
        language: system
        types: [python]
        pass_filenames: false
      - id: ruff-format
        name: ruff format
        entry: uv run --no-sync ruff format
        language: system
        types: [python]
        pass_filenames: false
      - id: ty
        name: ty type check
        entry: uv run --no-sync ty check src
        language: system
        types: [python]
        pass_filenames: false
      # pytest is a pre-push gate rather than per-commit, so a docs-only
      # commit is not held up. CI is the authoritative gate.
      - id: pytest
        name: pytest
        entry: uv run --no-sync pytest -q
        language: system
        stages: [pre-push]
        types: [python]
        pass_filenames: false

  # The template ships bootstrap, so shell is linted and formatted. Flags match
  # CI and ~/.vimrc's ALE config: -i 2 -bn -ci -sr. Note `-i2` is invalid --
  # Go's flag parser reads it as a flag named `i2` and shfmt exits non-zero.
  - repo: https://github.com/koalaman/shellcheck-precommit
    rev: v0.11.0
    hooks:
      - id: shellcheck
  - repo: https://github.com/scop/pre-commit-shfmt
    rev: v3.12.0-2
    hooks:
      - id: shfmt
        args: [-i, "2", -bn, -ci, -sr, -d]

  - repo: https://github.com/alessandrojcm/commitlint-pre-commit-hook
    rev: v9.26.0
    hooks:
      - id: commitlint
        stages: [commit-msg]
        additional_dependencies:
          - "@commitlint/config-conventional@^21.2.0"

  - repo: https://github.com/rhysd/actionlint
    rev: v1.7.12
    hooks:
      - id: actionlint

  - repo: https://github.com/woodruffw/zizmor-pre-commit
    rev: v1.29.0
    hooks:
      - id: zizmor
```

- [ ] **Step 2: Write `commitlint.config.mjs`**

```javascript
export default {
  extends: ['@commitlint/config-conventional'],
  // Dependabot generates bodies with long markdown URLs that exceed
  // body-max-line-length and will not wrap them. Skip its commits; the full
  // ruleset still applies to human authors.
  ignores: [(message) => message.includes('Signed-off-by: dependabot[bot]')],
  rules: {
    // `deps` is not a config-conventional type. Dependabot uses it so
    // release-please can route those commits to a visible Dependencies
    // changelog section -- the default `chore(deps)` lands under `chore`,
    // which the preset hides.
    'type-enum': [
      2,
      'always',
      [
        'build',
        'chore',
        'ci',
        'deps',
        'docs',
        'feat',
        'fix',
        'perf',
        'refactor',
        'revert',
        'style',
        'test',
      ],
    ],
    // Allow class names and acronyms in subjects. The default ruleset rejects
    // pascal-case/start-case subjects, too restrictive for domain-rich code.
    'subject-case': [0],
  },
};
```

- [ ] **Step 3: Install and run the hooks**

```bash
task dev:hooks-install
task dev:hooks
```
Expected: all hooks pass. `check-executables-have-shebangs` and the shell hooks
have nothing to chew on until Task 14 adds `bootstrap`.

- [ ] **Step 4: Verify the shfmt flag spelling is the valid one**

```bash
shfmt -i 2 -bn -ci -sr --version   # expect a version, not "flag provided but not defined"
```

- [ ] **Step 5: Commit**

```bash
git add .pre-commit-config.yaml commitlint.config.mjs
git commit -m "build: add prek hooks and commitlint config"
```

---

### Task 6: CI workflow

**Files:**
- Create: `.github/workflows/ci.yaml`

**Interfaces:**
- Consumes: `.pre-commit-config.yaml` (Task 5), `task dev:check` (Task 4).
- Produces: a required check named `test`. The `bootstrap` job is added in
  Task 15 once the script exists; the aggregator's `needs` is updated then.

Shape follows `gh-release-stats`, not `jobhound`: CI runs the prek hooks rather
than restating them, so local and CI cannot drift; and ruff/ty run once instead
of once per matrix entry.

- [ ] **Step 1: Write `.github/workflows/ci.yaml`**

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  lint:
    name: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d  # v10.0.1
        with:
          python-version: "3.13"
          enable-cache: true
          # Distinguishes this job's cache key from pytest (py3.13)'s. Without
          # it both race on the same key and one fails to save.
          cache-suffix: lint
      # The ruff and ty hooks are `uv run --no-sync`, so the venv must exist
      # before prek runs.
      - run: uv sync --frozen
      # Runs the hooks from .pre-commit-config.yaml rather than repeating them
      # here, so local and CI cannot drift. zizmor is skipped: it has its own
      # job below, which the ruleset requires by name.
      - uses: j178/prek-action@4e14d07f9231acabce116ccfca13b13dd9755ece  # v3.0.0
        env:
          SKIP: zizmor

  pytest:
    name: pytest (py${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.11", "3.12", "3.13", "3.14"]
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d  # v10.0.1
        with:
          python-version: ${{ matrix.python-version }}
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run pytest -q

  # Aggregator. The branch ruleset requires this exact check name, so the
  # matrix can grow without touching branch protection.
  test:
    name: test
    runs-on: ubuntu-latest
    needs: [lint, pytest]
    if: always()
    steps:
      - name: aggregate
        env:
          LINT: ${{ needs.lint.result }}
          PYTEST: ${{ needs.pytest.result }}
        run: |
          set -euo pipefail
          if [[ "$LINT" != "success" || "$PYTEST" != "success" ]]; then
            echo "lint=$LINT pytest=$PYTEST"
            exit 1
          fi
          echo "lint and pytest matrix all green"

  commitlint:
    name: commitlint
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false
      # Fork of wagoid/commitlint-github-action. Upstream is dead: last commit
      # 2025-01-14, no releases, and it pins @commitlint/ensure ^19 -- which
      # predates the exemption for long lines containing a URL added in v20, so
      # Dependabot's markdown-link bodies fail body-max-line-length on it.
      # This fork runs commitlint v21 on node 24 and pins its runtime image by
      # digest, so pinning by SHA here cannot be worked around.
      - uses: yo61/commitlint-github-action@501ff7bb31eb7133c871318c877d0e43cd1ff500  # v6.3.1
        with:
          configFile: commitlint.config.mjs

  zizmor:
    name: zizmor
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          persist-credentials: false
      - uses: zizmorcore/zizmor-action@3dc1ecc9bcb9e94e9b2c709687979e1298497054  # v0.6.2
        with:
          advanced-security: false
          persona: regular
          version: v1.29.0
```

- [ ] **Step 2: Verify the commitlint pin resolves to its comment**

```bash
gh api repos/yo61/commitlint-github-action/git/refs/tags/v6.3.1 -q '.object.sha' \
  | xargs -I{} gh api repos/yo61/commitlint-github-action/git/tags/{} -q '.object.sha'
```
Expected: `501ff7bb31eb7133c871318c877d0e43cd1ff500`, matching the workflow pin.

- [ ] **Step 3: Lint the workflow locally**

```bash
actionlint .github/workflows/ci.yaml
zizmor .github/workflows/ci.yaml
```
Expected: no findings.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yaml
git commit -m "ci: add lint, pytest matrix, commitlint and zizmor jobs"
```

---

## Phase 3 — Release

### Task 7: release-please configuration

**Files:**
- Create: `release-please-config.json`, `.release-please-manifest.json`, `CHANGELOG.md`

**Interfaces:**
- Produces: the config the release workflow (Task 8) passes as `--config-file`.

- [ ] **Step 1: Write `release-please-config.json`**

```json
{
  "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
  "release-type": "python",
  "include-v-in-tag": true,
  "include-component-in-tag": false,
  "bump-minor-pre-major": true,
  "bump-patch-for-minor-pre-major": false,
  "changelog-sections": [
    { "type": "feat", "section": "Features" },
    { "type": "feature", "section": "Features" },
    { "type": "fix", "section": "Bug Fixes" },
    { "type": "perf", "section": "Performance Improvements" },
    { "type": "deps", "section": "Dependencies" },
    { "type": "revert", "section": "Reverts" },
    { "type": "docs", "section": "Documentation", "hidden": true },
    { "type": "style", "section": "Styles", "hidden": true },
    { "type": "chore", "section": "Miscellaneous Chores", "hidden": true },
    { "type": "refactor", "section": "Code Refactoring", "hidden": true },
    { "type": "test", "section": "Tests", "hidden": true },
    { "type": "build", "section": "Build System", "hidden": true },
    { "type": "ci", "section": "Continuous Integration", "hidden": true }
  ],
  "packages": {
    ".": {
      "package-name": "python-template",
      "changelog-path": "CHANGELOG.md"
    }
  }
}
```

- [ ] **Step 2: Write `.release-please-manifest.json`**

```json
{".":"0.0.0"}
```

- [ ] **Step 3: Write `CHANGELOG.md`**

```markdown
# Changelog
```

- [ ] **Step 4: Verify the JSON parses**

```bash
jq -e . release-please-config.json > /dev/null && echo "config ok"
jq -e . .release-please-manifest.json > /dev/null && echo "manifest ok"
```

- [ ] **Step 5: Commit**

```bash
git add release-please-config.json .release-please-manifest.json CHANGELOG.md
git commit -m "build: add release-please configuration"
```

---

### Task 8: Release workflow with lockfile sync

**Files:**
- Create: `.github/workflows/release.yaml`

**Interfaces:**
- Consumes: `release-please-config.json` (Task 7).
- Requires repo secrets `SEMANTIC_RELEASE_APP_CLIENT_ID` and
  `SEMANTIC_RELEASE_APP_PRIVATE_KEY`, and a `pypi` environment.

The `sync-lockfile` job is mandatory, not garnish. release-please rewrites the
version in `pyproject.toml` but knows nothing about `uv.lock`, so the
self-referencing pin goes stale and the next `uv run` on `main` silently
rewrites it (jobhound #66). `extra-files` cannot fix it because `uv lock`
strips comments, and `git commit` from the runner cannot because a
`required_signatures` ruleset rejects unsigned commits.

- [ ] **Step 1: Write `.github/workflows/release.yaml`**

```yaml
name: Release

on:
  push:
    branches: [main]

permissions: {}

jobs:
  release-please:
    runs-on: ubuntu-latest
    if: github.repository_owner == 'yo61'
    permissions:
      contents: read
    outputs:
      release_created: ${{ steps.rp.outputs.release_created }}
      tag_name: ${{ steps.rp.outputs.tag_name }}
      prs: ${{ steps.rp.outputs.prs }}
    steps:
      # Mint a short-lived App token so the Release PR is authored by the App
      # rather than github-actions[bot]. PRs opened with the default
      # GITHUB_TOKEN do not fire `pull_request` workflows (GitHub's
      # loop-prevention policy), so the PR would have no checks and branch
      # protection would block the merge.
      - id: create_token
        uses: actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1  # v3.2.0
        with:
          client-id: ${{ secrets.SEMANTIC_RELEASE_APP_CLIENT_ID }}
          private-key: ${{ secrets.SEMANTIC_RELEASE_APP_PRIVATE_KEY }}
          owner: ${{ github.repository_owner }}
          repositories: ${{ github.event.repository.name }}
          permission-contents: write
          permission-pull-requests: write
      - uses: googleapis/release-please-action@45996ed1f6d02564a971a2fa1b5860e934307cf7  # v5.0.0
        id: rp
        with:
          config-file: release-please-config.json
          manifest-file: .release-please-manifest.json
          token: ${{ steps.create_token.outputs.token }}

  sync-lockfile:
    needs: release-please
    if: needs.release-please.outputs.prs && needs.release-please.outputs.prs != '[]'
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - id: create_token
        uses: actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1  # v3.2.0
        with:
          client-id: ${{ secrets.SEMANTIC_RELEASE_APP_CLIENT_ID }}
          private-key: ${{ secrets.SEMANTIC_RELEASE_APP_PRIVATE_KEY }}
          owner: ${{ github.repository_owner }}
          repositories: ${{ github.event.repository.name }}
          permission-contents: write
      - id: pr_branch
        env:
          PRS_JSON: ${{ needs.release-please.outputs.prs }}
        run: |
          set -euo pipefail
          branch=$(printf '%s' "$PRS_JSON" | jq -r '.[0].headBranchName')
          if [[ -z "$branch" || "$branch" == "null" ]]; then
            echo "release-please did not report a head branch; skipping" >&2
            echo "skip=true" >> "$GITHUB_OUTPUT"
          else
            echo "branch=$branch" >> "$GITHUB_OUTPUT"
          fi
      - if: steps.pr_branch.outputs.skip != 'true'
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          ref: ${{ steps.pr_branch.outputs.branch }}
          token: ${{ steps.create_token.outputs.token }}
          persist-credentials: true
      - if: steps.pr_branch.outputs.skip != 'true'
        uses: astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d  # v10.0.1
        with:
          python-version: "3.13"
          enable-cache: false
      - if: steps.pr_branch.outputs.skip != 'true'
        name: Sync uv.lock and commit (signed) if changed
        env:
          UV_FROZEN: "0"
          GH_TOKEN: ${{ steps.create_token.outputs.token }}
          GITHUB_REPOSITORY: ${{ github.repository }}
          BRANCH: ${{ steps.pr_branch.outputs.branch }}
        # Uses the GraphQL createCommitOnBranch mutation, not git commit/push.
        # Commits made via the API on an App's behalf are signed by GitHub's
        # app-flow key, which the required_signatures ruleset on main demands;
        # a plain git commit from the runner is unsigned and blocks the PR.
        run: |
          set -euo pipefail
          uv lock
          if [[ -z "$(git status --porcelain uv.lock)" ]]; then
            echo "uv.lock already in sync"
            exit 0
          fi
          head_sha=$(git rev-parse HEAD)
          base64 -w0 < uv.lock > /tmp/uv.lock.b64
          # Request built with jq --rawfile and submitted via --input. Two
          # failure modes this avoids:
          #   1. Inline `-f content=$b64` exceeds MAX_ARG_STRLEN (128KB per
          #      arg) once uv.lock passes ~95KB (E2BIG / exit 126).
          #   2. `-f content=@/tmp/file` does NOT work -- gh's @filename
          #      expansion does not apply to graphql variables; it sends the
          #      literal path and the server rejects "Invalid Base64".
          # shellcheck disable=SC2016 # jq references, not shell expansions.
          query='mutation($repo: String!, $branch: String!, $sha: GitObjectID!, $content: Base64String!) {
            createCommitOnBranch(input: {
              branch: { repositoryNameWithOwner: $repo, branchName: $branch },
              message: { headline: "chore: sync uv.lock with version bump" },
              expectedHeadOid: $sha,
              fileChanges: { additions: [{ path: "uv.lock", contents: $content }] }
            }) {
              commit { url }
            }
          }'
          jq -n \
            --arg query "$query" \
            --arg repo "$GITHUB_REPOSITORY" \
            --arg branch "$BRANCH" \
            --arg sha "$head_sha" \
            --rawfile content /tmp/uv.lock.b64 \
            '{
              query: $query,
              variables: {
                repo: $repo,
                branch: $branch,
                sha: $sha,
                content: ($content | rtrimstr("\n"))
              }
            }' > /tmp/graphql.json
          gh api graphql --input /tmp/graphql.json

  publish:
    needs: release-please
    if: needs.release-please.outputs.release_created == 'true'
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/python-template
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          ref: ${{ needs.release-please.outputs.tag_name }}
          persist-credentials: false
      - uses: astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d  # v10.0.1
        with:
          python-version: "3.13"
          enable-cache: false
      - run: uv build
      - uses: pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33  # v1.14.2
```

- [ ] **Step 2: Lint the workflow**

```bash
actionlint .github/workflows/release.yaml
zizmor .github/workflows/release.yaml
shellcheck -s bash <(sed -n '/set -euo pipefail/,/gh api graphql/p' .github/workflows/release.yaml) || true
```
Expected: actionlint and zizmor clean.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/release.yaml
git commit -m "ci: add release workflow with release-please and lockfile sync"
```

---

### Task 9: Dependabot

**Files:**
- Create: `.github/dependabot.yml`

The `deps` vs `chore(deps)` split is deliberate: release-please treats every
visible changelog section as releasable, so `deps` both lists an update and
cuts a patch release, while `chore` does neither. The line is what reaches
users. Production and development are separate groups because a grouped PR
mixing both has no unambiguous prefix.

- [ ] **Step 1: Write `.github/dependabot.yml`**

```yaml
version: 2

updates:
  # Developer tooling; never reaches the published package.
  - package-ecosystem: "pre-commit"
    directory: "/"
    schedule:
      interval: "weekly"
    cooldown:
      default-days: 7
    commit-message:
      prefix: "chore(deps)"
    groups:
      hooks:
        patterns: ["*"]

  # Python. The `uv` ecosystem updates uv.lock as well as the pyproject
  # constraints; `pip` would leave the lock stale.
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "weekly"
    cooldown:
      default-days: 7
    commit-message:
      prefix: "deps"
      prefix-development: "chore(deps)"
    groups:
      uv-production:
        dependency-type: "production"
        update-types: ["minor", "patch"]
      uv-development:
        dependency-type: "development"
        update-types: ["minor", "patch"]

  # Actions. Pins are SHAs with version comments; Dependabot rewrites both.
  # Majors stay outside the group so they arrive as individual PRs.
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    cooldown:
      default-days: 7
    commit-message:
      prefix: "chore(deps)"
    groups:
      actions-minor-patch:
        update-types: ["minor", "patch"]

  # docs/site is pnpm-managed; Dependabot auto-detects pnpm-lock.yaml.
  - package-ecosystem: "npm"
    directory: "/docs/site"
    schedule:
      interval: "weekly"
    cooldown:
      default-days: 7
    commit-message:
      prefix: "chore(deps)"
    ignore:
      # TypeScript 7.x is the native (Go) compiler; it drops the JS compiler
      # API that `next build` loads for type-checking. Hold on 6.x until the
      # Next/fumadocs toolchain supports it.
      - dependency-name: "typescript"
        update-types: ["version-update:semver-major"]
    groups:
      npm-minor-patch:
        update-types: ["minor", "patch"]
```

- [ ] **Step 2: Verify it parses**

```bash
uv run --with pyyaml python -c "import yaml,sys; yaml.safe_load(open('.github/dependabot.yml')); print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add .github/dependabot.yml
git commit -m "build: add dependabot config for uv, actions, hooks and npm"
```

---

### Task 10: Agent scaffolding

**Files:**
- Create: `CLAUDE.md`, `decisions/README.md`, `quality/criteria.md`, `docs/superpowers/README.md`

- [ ] **Step 1: Write `decisions/README.md`**

```markdown
# Decisions

One file per decision that affects more than a single task:
`YYYY-MM-DD-topic.md`.

Format:

## Decision: what was decided
## Context: why it came up
## Alternatives considered
## Reasoning: why this option won
## Trade-offs accepted
## Supersedes: link to the prior decision, if replacing

Grep here before making a decision in an area. Follow what you find unless new
information invalidates the reasoning.
```

- [ ] **Step 2: Write `quality/criteria.md`**

Seeded with the format and no criteria. Criteria are earned from real review
findings; pre-populating guesses produces a checklist nobody trusts.

```markdown
# Quality Criteria

Empty by design. Add a criterion when a review catches a *real* failure, not
preemptively. Each entry records the failure that produced it.

Format:

## Category: area — e.g. API design, error handling, tests

### Criteria
- specific, testable check

### Severity: blocking | warning
### Source: where this came from
### Last triggered: date, or "never"

Promote a criterion triggered 3+ times to "always check". Suggest pruning one
never triggered after 10+ evaluations.
```

- [ ] **Step 3: Write `docs/superpowers/README.md`**

```markdown
# Design records

- `specs/YYYY-MM-DD-<topic>-design.md` — validated designs from brainstorming
- `plans/YYYY-MM-DD-<topic>.md` — implementation plans

Written before code, committed alongside it.
```

- [ ] **Step 4: Write `CLAUDE.md`**

```markdown
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

## Placeholders

Before `./bootstrap` runs, `pythontemplate` and `python-template` are live
values, not markers. Any new file must use those exact spellings or the
bootstrap smoke test will fail.
```

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md decisions quality docs/superpowers/README.md
git commit -m "docs: add agent scaffolding and project CLAUDE.md"
```

---

## Phase 4 — Docs site

### Task 11: Fumadocs scaffold

**Files:**
- Create: `docs/site/` — copied from `../go-udap/docs/site/` then adapted
- Modify: `docs/site/next.config.mjs`, `docs/site/package.json`, `docs/site/lib/layout.shared.tsx`

**Interfaces:**
- Produces: `pnpm build` in `docs/site` emitting `docs/site/out/`, consumed by
  the Pages workflow (Task 13).

go-udap's site is the only Fumadocs precedent in the fleet and is current
(Next 16, fumadocs 16.14.2). Copy the boilerplate rather than regenerating it,
so the security `overrides` and the basePath plumbing come along.

- [ ] **Step 1: Copy the boilerplate**

```bash
SRC=../go-udap/docs/site
mkdir -p docs/site
cp -R "$SRC"/app "$SRC"/components "$SRC"/lib docs/site/
cp "$SRC"/{next.config.mjs,package.json,postcss.config.mjs,source.config.ts,tsconfig.json,pnpm-workspace.yaml,.gitignore} docs/site/
find docs/site -type f | sort
```
Expected: the `app/`, `components/`, `lib/` trees plus seven config files. Do
**not** copy `content/`, `public/` or `pnpm-lock.yaml`.

- [ ] **Step 2: Rewrite the basePath in `next.config.mjs`**

Change the one line, keeping the explanatory comment intact:

```javascript
const basePath = process.env.BASE_PATH ?? '/python-template';
```

- [ ] **Step 3: Rename the package**

In `docs/site/package.json`, set `"name": "python-template-docs"`. Leave every
dependency version exactly as copied.

- [ ] **Step 4: Retitle the site**

In `docs/site/lib/layout.shared.tsx`, set the nav title to `python-template`
and the GitHub URL to `https://github.com/yo61/python-template`.

- [ ] **Step 5: Check no go-udap references survive**

```bash
grep -rn "go-udap\|udap\|Squeezebox" docs/site --include='*.ts' --include='*.tsx' \
  --include='*.mjs' --include='*.json' || echo "clean"
```
Expected: `clean`. Anything found is a leftover to rewrite.

- [ ] **Step 6: Install and build**

```bash
cd docs/site && pnpm install && pnpm build && cd ../..
ls docs/site/out/index.html
```
Expected: build succeeds; `out/index.html` exists. It will 404 on content until
Task 12 — that is fine, the build is what is being checked.

- [ ] **Step 7: Commit**

```bash
git add docs/site
git commit -m "docs: add Fumadocs site scaffold"
```

---

### Task 12: Diátaxis content

**Files:**
- Create: `docs/site/content/docs/meta.json`, `docs/site/content/docs/index.mdx`, and `index.mdx` under each of `tutorials/`, `how-to/`, `reference/`, `explanation/`, `contributing/`
- Create: `docs/site/content/docs/contributing/docs-style.mdx`, `docs/site/content/docs/how-to/add-ddd-layers.mdx`

**Interfaces:**
- Consumes: `source.config.ts` `dir: 'content/docs'` (Task 11).

- [ ] **Step 1: Write the root `meta.json`**

```json
{
  "title": "Docs",
  "pages": [
    "tutorials",
    "how-to",
    "reference",
    "explanation",
    "contributing"
  ]
}
```

- [ ] **Step 2: Write `index.mdx` and the five section landing pages**

Each section index carries frontmatter and one sentence naming what belongs
there. Example — `explanation/index.mdx`:

```mdx
---
title: Explanation
description: Background and design reasoning
---

Why the project is built the way it is. Read these when you want understanding
rather than instructions.
```

Equivalents: `tutorials` ("Learning-oriented walkthroughs. Start here."),
`how-to` ("Task-oriented recipes for a specific goal."), `reference`
("Look-up material: commands, flags, configuration."), `contributing`
("How to work on the project itself.").

- [ ] **Step 3: Write `contributing/docs-style.mdx`**

Adapt go-udap's, which is the fleet's only docs style guide:

```bash
cp ../go-udap/docs/site/content/docs/contributing/docs-style.mdx \
   docs/site/content/docs/contributing/
```

Then apply three edits:

1. Replace every `concepts/*` reference with `explanation/*` — this template
   uses the canonical Diátaxis name (spec D6).
2. Strip go-udap-specific examples (NVRAM parameters, exit codes,
   `reference/global-flags`) and replace with neutral ones.
3. Delete the closing paragraph about the removed `<HowTo>` component; that is
   go-udap's history, not this template's.

Verify:

```bash
grep -n "concepts\|NVRAM\|udap\|HowTo" docs/site/content/docs/contributing/docs-style.mdx \
  || echo "clean"
```

- [ ] **Step 4: Write `how-to/add-ddd-layers.mdx`**

```mdx
---
title: Add DDD layers
description: Split the package into layers and enforce the boundaries with import-linter
---

## Goal

Turn the flat `commands/` package into explicit DDD layers, and make the
layering a build failure rather than a convention people remember.

Skip this until you have real domain logic. Four near-empty packages buy
nothing.

## Prerequisites

- `import-linter` in the dev group: `uv add --dev 'import-linter>=2'`

## Steps

### Create the layer packages

```bash
mkdir -p src/pythontemplate/{application,domain,infrastructure}
touch src/pythontemplate/{application,domain,infrastructure}/__init__.py
```

- `commands/` — CLI verbs; parse input, call application, print output
- `application/` — use-cases; orchestrate domain objects
- `domain/` — entities, value objects, business rules. No I/O, no framework
- `infrastructure/` — persistence and external clients

### Uncomment the contract

`pyproject.toml` ships the block commented out:

```toml
[tool.importlinter]
root_package = "pythontemplate"

[[tool.importlinter.contracts]]
name = "DDD layers"
type = "layers"
layers = [
    "pythontemplate.commands",
    "pythontemplate.application",
    "pythontemplate.domain",
]
```

Higher may import lower, never the reverse.

### Wire it into the gate

Add to `Taskfile.yml`:

```yaml
  dev:imports:
    desc: Enforce import boundaries (import-linter)
    cmds:
      - uv run lint-imports
```

Add `- task: dev:imports` to `dev:check`, and a matching local prek hook next
to the ruff and ty ones:

```yaml
      - id: import-linter
        name: import-linter
        entry: uv run --no-sync lint-imports
        language: system
        types: [python]
        pass_filenames: false
```

### Verify

```bash
task dev:imports
```

## Notes

### `cli` must stay out of the layers list

`cli._build_app()` imports every command module lazily. import-linter parses
the AST for imports at **any** depth, so a function-scoped import counts
exactly like a top-level one — it will report the violation with the line
number inside the function body.

There is no way to exempt a lazy import from a contract. Leaving `cli` out of
the `layers` list is the only lever, and it is what `unifictl` does.

### Do not blanket-forbid infrastructure → domain

`unifictl` also declares that `infrastructure` may import neither `domain` nor
`application`, because there `infrastructure` is an isolated private-API client
mirroring an external contract.

That is not a general rule. If `infrastructure` holds your repositories, it
*must* import the entities it persists — that is what a repository is. Adopting
the contract blindly produces violations that are not defects.
```

- [ ] **Step 5: Build and check the sidebar**

```bash
cd docs/site && pnpm build && cd ../..
grep -o 'Explanation\|Contributing' docs/site/out/docs/index.html | sort -u
```
Expected: both appear — the sections are in the nav.

- [ ] **Step 6: Commit**

```bash
git add docs/site/content
git commit -m "docs: add Diataxis sections, docs style guide and DDD how-to"
```

---

### Task 13: Pages deploy workflow

**Files:**
- Create: `.github/workflows/docs.yaml`

- [ ] **Step 1: Write the workflow**

```yaml
name: Docs

on:
  push:
    branches: [main]
    paths:
      - 'docs/site/**'
      - '.github/workflows/docs.yaml'
  pull_request:
    paths:
      - 'docs/site/**'
      - '.github/workflows/docs.yaml'
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: pages-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: docs/site
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          persist-credentials: false
      - uses: pnpm/action-setup@0977fd99725f1db4007ccb2928dbb4e90d06cc86  # v6.0.10
        with:
          version: 11
      - uses: actions/setup-node@820762786026740c76f36085b0efc47a31fe5020  # v7.0.0
        with:
          node-version: 22
          cache: pnpm
          cache-dependency-path: docs/site/pnpm-lock.yaml
      - run: pnpm install --frozen-lockfile
      - run: pnpm build
      - uses: actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d  # v6.0.0
      - uses: actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9  # v5.0.0
        with:
          path: docs/site/out

  deploy:
    needs: build
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@cd2ce8fcbc39b97be8ca5fce6e763baed58fa128  # v5.0.0
```

- [ ] **Step 2: Commit the lockfile too**

`pnpm install` in Task 11 generated `docs/site/pnpm-lock.yaml`; the workflow's
`--frozen-lockfile` requires it to be committed.

```bash
git add docs/site/pnpm-lock.yaml .github/workflows/docs.yaml
actionlint .github/workflows/docs.yaml && zizmor .github/workflows/docs.yaml
git commit -m "ci: build and deploy the docs site to GitHub Pages"
```

---

## Phase 5 — Bootstrap

### Task 14: Bootstrap smoke test

**Files:**
- Create: `scripts/test-bootstrap.sh`

**Interfaces:**
- Produces: `scripts/test-bootstrap.sh` — exit 0 on success. Called by the
  developer and by the CI job in Task 16.

Written before `bootstrap` exists, so it fails first. This is the test that
stops the template rotting: the classic failure is a new file whose placeholder
nobody added to the rewrite list, invisible until someone generates a project.

- [ ] **Step 1: Write the failing test**

```bash
#!/usr/bin/env bash
# Generate projects from the template and prove they work.
set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

run_case() {
  local name=$1
  shift
  local dir="$WORK/$name"

  git -C "$REPO_ROOT" archive HEAD | (mkdir -p "$dir" && tar -x -C "$dir")
  git -C "$dir" init -q
  git -C "$dir" add -A
  git -C "$dir" -c user.email=t@example.com -c user.name=t commit -qm "init"

  (cd "$dir" && ./bootstrap --defaults "$@") || fail "$name: bootstrap exited non-zero"

  # No placeholder may survive anywhere in the generated tree.
  local leaks
  leaks=$(grep -rIl --exclude-dir=.git --exclude-dir=node_modules \
    --exclude-dir=.venv -e 'pythontemplate' -e 'python-template' "$dir" || true)
  [ -z "$leaks" ] || fail "$name: placeholders survived in:
$leaks"

  [ -d "$dir/src/my_tool" ] || fail "$name: src/my_tool missing"
  [ ! -e "$dir/bootstrap" ] || fail "$name: bootstrap did not delete itself"
  [ ! -e "$dir/.bootstrap-defaults" ] || fail "$name: defaults file survived"
  [ ! -e "$dir/docs/superpowers/specs/2026-08-24-python-template-rewrite-design.md" ] \
    || fail "$name: template design docs leaked into the generated project"

  grep -q "basePath = process.env.BASE_PATH ?? '/my-tool'" \
    "$dir/docs/site/next.config.mjs" || fail "$name: Fumadocs basePath not rewritten"

  (cd "$dir" && uv sync --quiet && task dev:check) || fail "$name: task dev:check failed"

  echo "PASS: $name"
}

run_case flat
run_case ddd --ddd

# The DDD case must additionally have layers and a passing contract.
DDD="$WORK/ddd"
for layer in application domain infrastructure; do
  [ -d "$DDD/src/my_tool/$layer" ] || fail "ddd: src/my_tool/$layer missing"
done
grep -q '^\[tool.importlinter\]' "$DDD/pyproject.toml" \
  || fail "ddd: importlinter block still commented out"
(cd "$DDD" && task dev:imports) || fail "ddd: import contracts broken"

echo "PASS: all bootstrap cases"
```

- [ ] **Step 2: Make it executable and run it**

```bash
chmod +x scripts/test-bootstrap.sh
./scripts/test-bootstrap.sh
```
Expected: `FAIL: flat: bootstrap exited non-zero` — the script does not exist yet.

- [ ] **Step 3: Lint it**

```bash
shellcheck scripts/test-bootstrap.sh
shfmt -i 2 -bn -ci -sr -d scripts/test-bootstrap.sh
```
Expected: both clean.

- [ ] **Step 4: Commit**

```bash
git add scripts/test-bootstrap.sh
git commit -m "test: add bootstrap smoke test (fails until bootstrap exists)"
```

---

### Task 15: The bootstrap script

**Files:**
- Create: `bootstrap`, `.bootstrap-defaults`

**Interfaces:**
- Consumes: every placeholder token in Global Constraints.
- Produces: satisfies `scripts/test-bootstrap.sh` (Task 14).
- CLI: `./bootstrap [--defaults] [--ddd]`. `--defaults` reads
  `.bootstrap-defaults` instead of prompting.

- [ ] **Step 1: Write `.bootstrap-defaults`**

```bash
# Non-interactive answers, used by ./bootstrap --defaults and CI.
PROJECT_NAME=my-tool
PACKAGE_NAME=my_tool
CLI_NAME=my-tool
DESCRIPTION="A tool that does a thing."
AUTHOR="Robin Bowes"
```

- [ ] **Step 2: Write `bootstrap`**

```bash
#!/usr/bin/env bash
# Turn this template into a project. Deletes itself on success.
set -euo pipefail

USE_DEFAULTS=false
WANT_DDD=false
for arg in "$@"; do
  case "$arg" in
    --defaults) USE_DEFAULTS=true ;;
    --ddd) WANT_DDD=true ;;
    *)
      echo "usage: $0 [--defaults] [--ddd]" >&2
      exit 2
      ;;
  esac
done

command -v uv > /dev/null || {
  echo "bootstrap: uv is required (https://docs.astral.sh/uv/)" >&2
  exit 1
}

repo_name=$(basename "$(git rev-parse --show-toplevel)")

ask() { # ask VAR PROMPT DEFAULT
  local var=$1 prompt=$2 default=$3 reply
  read -r -p "  $prompt [$default]: " reply
  printf -v "$var" '%s' "${reply:-$default}"
}

if $USE_DEFAULTS; then
  # shellcheck source=.bootstrap-defaults
  . ./.bootstrap-defaults
else
  echo "Configuring this template."
  ask PROJECT_NAME "Project name" "$repo_name"
  ask PACKAGE_NAME "Package name" "${PROJECT_NAME//-/_}"
  ask CLI_NAME "CLI command" "$PROJECT_NAME"
  ask DESCRIPTION "Description" "A tool that does a thing."
  ask AUTHOR "Author" "$(git config user.name || echo 'Robin Bowes')"
  read -r -p "  DDD layering? [y/N]: " reply
  [[ "$reply" =~ ^[Yy]$ ]] && WANT_DDD=true
fi

# Files carrying placeholders. Every template file that mentions a placeholder
# must appear here or scripts/test-bootstrap.sh will fail.
# Read into an array without `mapfile` -- that is a bash 4 builtin and
# macOS still ships bash 3.2 at /bin/bash.
files=()
while IFS= read -r line; do
  files+=("$line")
done < <(
  git ls-files \
    | grep -v -e '^bootstrap$' -e '^\.bootstrap-defaults$' \
      -e '^docs/superpowers/' -e '^LICENSE$' -e '^pnpm-lock' \
      -e '^docs/site/pnpm-lock.yaml$'
)

# Order matters: rewrite the kebab form first. `pythontemplate` contains no
# hyphen so the two never overlap, but keeping the order fixed makes the
# substitution auditable.
for f in "${files[@]}"; do
  [ -f "$f" ] || continue
  sed -i.bak \
    -e "s|python-template|$PROJECT_NAME|g" \
    -e "s|pythontemplate|$PACKAGE_NAME|g" \
    -e "s|A template for yo61 Python projects\.|$DESCRIPTION|g" \
    -e "s|Robin Bowes|$AUTHOR|g" \
    "$f"
  rm -f "$f.bak"
done

# The CLI command name is independent of the project name.
sed -i.bak "s|^$PROJECT_NAME = \"$PACKAGE_NAME.cli:main\"|$CLI_NAME = \"$PACKAGE_NAME.cli:main\"|" \
  pyproject.toml && rm -f pyproject.toml.bak

git mv "src/pythontemplate" "src/$PACKAGE_NAME"

# Reset release state.
printf '{".":"0.0.0"}\n' > .release-please-manifest.json
printf '# Changelog\n' > CHANGELOG.md

# Template-specific records must not propagate into the generated project.
rm -f docs/superpowers/specs/2026-08-24-python-template-rewrite-design.md
rm -f docs/superpowers/plans/2026-08-24-python-template-rewrite.md

if $WANT_DDD; then
  for layer in application domain infrastructure; do
    mkdir -p "src/$PACKAGE_NAME/$layer"
    printf '"""%s layer."""\n' "$layer" > "src/$PACKAGE_NAME/$layer/__init__.py"
  done
  # Uncomment the importlinter block: strip the leading '# ' from every line
  # between the marker and end of file.
  sed -i.bak '/^# \[tool.importlinter\]/,$ s/^# \{0,1\}//' pyproject.toml
  rm -f pyproject.toml.bak
  # UV_FROZEN=1 comes from mise.toml and makes `uv add` refuse to touch
  # the lockfile. Override for this one call.
  UV_FROZEN=0 uv add --dev --quiet 'import-linter>=2'
  python3 - "$PACKAGE_NAME" <<'PY'
import pathlib
import sys

pkg = sys.argv[1]
tf = pathlib.Path("Taskfile.yml")
s = tf.read_text()
s = s.replace(
    "  dev:test:\n",
    "  dev:imports:\n"
    "    desc: Enforce import boundaries (import-linter)\n"
    "    cmds:\n"
    "      - uv run lint-imports\n"
    "\n"
    "  dev:test:\n",
    1,
)
s = s.replace(
    "      - task: dev:typecheck\n      - task: dev:test\n",
    "      - task: dev:typecheck\n      - task: dev:imports\n      - task: dev:test\n",
    1,
)
tf.write_text(s)

hooks = pathlib.Path(".pre-commit-config.yaml")
h = hooks.read_text()
h = h.replace(
    "      # pytest is a pre-push gate",
    "      - id: import-linter\n"
    "        name: import-linter\n"
    "        entry: uv run --no-sync lint-imports\n"
    "        language: system\n"
    "        types: [python]\n"
    "        pass_filenames: false\n"
    "      # pytest is a pre-push gate",
    1,
)
hooks.write_text(h)
PY
fi

uv sync --quiet
command -v prek > /dev/null && prek install \
  --hook-type pre-commit --hook-type commit-msg --hook-type pre-push

rm -f bootstrap .bootstrap-defaults
git add -A
git -c user.email="$(git config user.email || echo bootstrap@local)" \
  -c user.name="$AUTHOR" \
  commit -qm "chore: bootstrap $PROJECT_NAME from python-template"

cat <<MSG

Done.
  package   src/$PACKAGE_NAME
  command   $CLI_NAME
  DDD       $($WANT_DDD && echo enabled || echo "flat (see docs how-to/add-ddd-layers)")

Next: task dev:check
MSG
```

- [ ] **Step 3: Make it executable and lint it**

```bash
chmod +x bootstrap
shellcheck bootstrap
shfmt -i 2 -bn -ci -sr -d bootstrap
```
Expected: both clean. Fix any finding before proceeding — CI runs the same.

- [ ] **Step 4: Run the smoke test**

```bash
./scripts/test-bootstrap.sh
```
Expected: `PASS: flat`, `PASS: ddd`, `PASS: all bootstrap cases`.

If it reports surviving placeholders, add the missing file to the `mapfile`
exclusion review — do not weaken the grep.

- [ ] **Step 5: Commit**

```bash
git add bootstrap .bootstrap-defaults
git commit -m "feat: add bootstrap script with optional DDD layering"
```

---

## Phase 6 — Finalise

### Task 16: Bootstrap CI job, README, repo settings

**Files:**
- Modify: `.github/workflows/ci.yaml` (add `bootstrap` job, update aggregator)
- Modify: `README.md`

- [ ] **Step 1: Add the `bootstrap` job to `ci.yaml`**

Insert before the `test` aggregator:

```yaml
  bootstrap:
    name: bootstrap
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d  # v10.0.1
        with:
          python-version: "3.13"
          enable-cache: true
          cache-suffix: bootstrap
      - uses: go-task/setup-task@a00fbb05ce67b35648be3c78cbc9fd85354c757e  # v2.2.0
        with:
          version: 3.x
      # Generates two projects from the template and runs the full gate on
      # each. Without this, a new file whose placeholder nobody registered
      # stays invisible until somebody generates a real project from it.
      - run: ./scripts/test-bootstrap.sh
```

- [ ] **Step 2: Update the aggregator**

```yaml
  test:
    name: test
    runs-on: ubuntu-latest
    needs: [lint, pytest, bootstrap]
    if: always()
    steps:
      - name: aggregate
        env:
          LINT: ${{ needs.lint.result }}
          PYTEST: ${{ needs.pytest.result }}
          BOOTSTRAP: ${{ needs.bootstrap.result }}
        run: |
          set -euo pipefail
          if [[ "$LINT" != "success" || "$PYTEST" != "success" || "$BOOTSTRAP" != "success" ]]; then
            echo "lint=$LINT pytest=$PYTEST bootstrap=$BOOTSTRAP"
            exit 1
          fi
          echo "all green"
```

- [ ] **Step 3: Write the full `README.md`**

Cover: what the template gives you, the `gh repo create --template` +
`./bootstrap` flow, the toolchain table, `task --list`, the docs-site commands,
and what the DDD prompt does. Link the docs site at
`https://yo61.github.io/python-template/`.

- [ ] **Step 4: Run the whole gate**

```bash
task dev:check
task dev:hooks
./scripts/test-bootstrap.sh
actionlint .github/workflows/
zizmor .github/workflows/
```
Expected: all clean.

- [ ] **Step 5: Commit and push**

```bash
git add -A
git commit -m "ci: add bootstrap smoke-test job and write the README"
git push -u origin template-v2
```

- [ ] **Step 6: Cut over `main` and set repo settings**

Force-pushing `main` needs Robin — the global rules forbid an agent doing it.
Present these commands and let him run them:

```bash
git branch -M template-v2 main
git push --force -u origin main

gh repo edit yo61/python-template \
  --template \
  --description "Template for yo61 Python projects: uv, ruff, ty, cyclopts, release-please, Fumadocs"
gh api -X POST repos/yo61/python-template/pages -f 'build_type=workflow' || true
```

- [ ] **Step 7: Verify the deployed site**

```bash
curl -fsSI https://yo61.github.io/python-template/ | head -1
```
Expected: `HTTP/2 200`. A 404 means the basePath is wrong — the failure mode
the template exists to prevent.

---

## Self-Review

**Spec coverage.** Every spec section maps to a task: repo layout → 1;
Python core → 2, 3; quality gates → 4, 5, 6; release → 7, 8, 9; docs site →
11, 12, 13; bootstrap → 14, 15; agent scaffolding → 10; testing → 14, 16;
`isTemplate` and description → 16.

**Known gaps, deliberate.**
- `LICENSE` is fetched from apache.org rather than inlined; the copyright line
  must be appended by hand in Task 1 Step 5.
- The README body is described rather than written out (Task 16 Step 3). It is
  prose with no interface contract, and writing it blind before the rest exists
  would produce something stale.

**Bugs caught in review, fixed inline.**
- `uv add --dev import-linter` in Task 15 would fail under `UV_FROZEN=1`,
  which `mise.toml` exports shell-wide. Now overridden per-call.
- `mapfile` is a bash 4 builtin; macOS `/bin/bash` is 3.2. Replaced with a
  `while read` loop so `bootstrap` runs on a stock macOS shell.

**Type consistency.** `run(name, *, shout)` is defined in Task 2 and consumed
in Task 3. `_build_app` / `get_app` / `app` / `main` / `_app_cache` are used
consistently across `cli.py` and `tests/test_cli.py`. `task dev:check` and
`task dev:imports` are named identically in the Taskfile, the how-to, the
bootstrap patch and the smoke test.
