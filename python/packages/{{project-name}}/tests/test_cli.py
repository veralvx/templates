import re
import runpy
import sys
from importlib.metadata import version

import pytest

from {{crate_name}}.cli import NAME, main


def test_it_greets_the_name_given(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["Ada"]) == 0
    assert capsys.readouterr().out == "Hello, Ada!\n"


def test_nobody_named_it_greets_the_world(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert capsys.readouterr().out == "Hello, world!\n"


def test_version_is_the_installed_distributions(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as stop:
        _ = main(["--version"])
    assert stop.value.code == 0
    assert capsys.readouterr().out == f"{NAME} {version(NAME)}\n"


def test_help_says_what_it_does_and_takes(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as stop:
        _ = main(["--help"])
    assert stop.value.code == 0
    lines = [line.strip() for line in capsys.readouterr().out.splitlines()]
    assert "Print a greeting." in lines
    assert any(re.fullmatch(r"name\s+who to greet \(default: the world\)", line) for line in lines)


def test_python_m_runs_the_command_line(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "argv", ["{{crate_name}}", "Ada"])
    with pytest.raises(SystemExit) as stop:
        _ = runpy.run_module("{{crate_name}}", run_name="__main__")
    assert stop.value.code == 0
    assert capsys.readouterr().out == "Hello, Ada!\n"
