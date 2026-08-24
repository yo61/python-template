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
        # Commands return their value; the CLI layer prints it (see `hello`
        # below). Cyclopts' default result_action would auto-print any non-None
        # return itself (double-printing) and sys.exit() even on a None result,
        # which breaks main()'s "returns normally on success" contract and its
        # single deliberate sys.exit(1) for ValueError.
        result_action="return_value",
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
