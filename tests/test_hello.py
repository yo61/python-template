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
