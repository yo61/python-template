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
