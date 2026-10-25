#!/usr/bin/env python3
"""rust's lock update (dev/lock_core.py's): rust/flake.lock moved to its inputs' newest -- in a
generated project, as the template's flake.nix holds Liquid, and copied back -- then what follows
it: the `msrv` prompt's regex and range, to the stable releases the new rust-overlay knows
(render-check's own, msrv.py); and dist-workspace.toml's `cargo-dist-version`, to the dev shell's
dist (a project's `pins` check holds the two equal).
"""

from __future__ import annotations

import pathlib
import re
import shutil
import sys

# dev/ and dev/rust/ named, not left to the script's own folder: `python -I` leaves that out
sys.path += [str(pathlib.Path(__file__).resolve().parents[1]), str(pathlib.Path(__file__).resolve().parent)]
from lock_core import ROOT, Summary, lock_in_project, main  # noqa: E402 - dev/, put on the path above
from msrv import msrv_regex, msrv_span, rust_releases  # noqa: E402 - dev/rust/, put on the path above

TEMPLATE = ROOT / "rust"
# the msrv prompt's table, to the next table: its regex and its prompt's range are rewritten there
# alone
MSRV = re.compile(r"(?ms)^\[placeholders\.msrv\]\n.*?(?=^\[|\Z)")
# dist-workspace.toml's pin, its one line
DIST = re.compile(r'(?m)^cargo-dist-version = "([^"]*)"$')


def update(summary: Summary) -> None:
    nix_cli = shutil.which("nix")
    if nix_cli is None:
        raise ValueError("no nix on PATH")
    # a kind with dist: its dev shell has the version cargo-dist-version names
    project, tools = lock_in_project(summary, "rust", "bin")
    msrv(summary, nix_cli, project)
    dist(summary, tools)


def dist(summary: Summary, tools: dict[str, str]) -> None:
    """dist-workspace.toml's cargo-dist-version, the dev shell's dist."""
    config = TEMPLATE / "dist-workspace.toml"
    text = config.read_text()
    pins = DIST.findall(text)
    if len(pins) != 1 or "cargo-dist" not in tools:
        raise ValueError("dist-workspace.toml: not one `cargo-dist-version` line, or no dist in the dev shell")
    old, new = pins[0], tools["cargo-dist"]
    if old != new:
        config.write_text(DIST.sub(f'cargo-dist-version = "{new}"', text))
        summary.follow("rust/dist-workspace.toml's cargo-dist-version", old, new)


def msrv(summary: Summary, nix_cli: str, project: pathlib.Path) -> None:
    """The msrv prompt's regex and range, the stable releases the locked rust-overlay knows."""
    releases = rust_releases(nix_cli, (project / "flake.nix").read_text(), TEMPLATE / "flake.lock")
    config = TEMPLATE / "cargo-generate.toml"
    text = config.read_text()
    table = MSRV.search(text)
    if table is None:
        raise ValueError("cargo-generate.toml: no [placeholders.msrv]")
    old_regex = re.search(r"(?m)^regex = '([^']*)'$", table[0])
    old_span = re.search(r"1\.\d+ to (\d+\.\d+\.\d+)", table[0])
    if old_regex is None or old_span is None:
        raise ValueError("cargo-generate.toml: [placeholders.msrv] has no `regex = '...'` or no range in its prompt")
    new_regex, new_span = msrv_regex(releases), msrv_span(releases)
    rewritten = table[0].replace(old_regex[0], f"regex = '{new_regex}'").replace(old_span[0], new_span)
    if rewritten == table[0]:
        return
    config.write_text(text[: table.start()] + rewritten + text[table.end() :])
    old_newest, new_newest = old_span[1], new_span.rsplit(" ", 1)[1]
    if old_newest != new_newest:
        summary.follow("the newest Rust the msrv prompt takes", old_newest, new_newest)
    if old_regex[1] != new_regex:
        summary.followed.append("the msrv regex: the releases the new rust-overlay knows")


if __name__ == "__main__":
    sys.exit(main("rust", update))
