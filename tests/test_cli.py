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
