#!/usr/bin/env python3
"""python's lock update (dev/lock_core.py's): python/flake.lock moved to its inputs' newest -- in a
generated project, as the template's flake.nix holds Liquid, and copied back -- then what follows
it: pyproject.toml's dependency-group pins and uv's `required-version`, to the versions each
kind's `pins` check reports (a workspace pins packaging too), which must then report none.
"""

from __future__ import annotations

import pathlib
import re
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from lock_core import ROOT, Summary, evaluate, generate, kinds, lock_in_project, main  # noqa: E402 - dev/, put on the path above

TEMPLATE = ROOT / "python"
# the `pins` check's report: one line a pin, as python/nix/checks.nix writes it
STALE = re.compile(r"(?P<name>[A-Za-z0-9._-]+): pinned (?P<old>\S+), nixpkgs (?P<new>\S+)")


def reports() -> dict[tuple[str, str], str]:
    """Each pin a kind's `pins` check reports, on the template as it stands (a workspace pins
    packaging too): its name and version pinned -- one name may be pinned at two -- to nixpkgs'."""
    stale: dict[tuple[str, str], str] = {}
    for kind in kinds("python"):
        for line in evaluate(generate("python", kind), "checks.x86_64-linux.pins.stale").splitlines():
            if (match := STALE.fullmatch(line)) is None:
                raise ValueError(f"the pins check reports {line!r}: no pin to move")
            stale[match["name"], match["old"]] = match["new"]
    return stale


def update(summary: Summary) -> None:
    lock_in_project(summary, "python", "bin")
    stale = reports()
    manifest = TEMPLATE / "pyproject.toml"
    text = manifest.read_text()
    for (name, old), new in sorted(stale.items()):
        if name == "uv":
            pin, moved = f'required-version = "=={old}"', f'required-version = "=={new}"'
        else:
            pin, moved = f'"{name}=={old}"', f'"{name}=={new}"'
        # every group's (pip-audit's, git-cliff's...), the literal text: nothing read as a pattern
        count = text.count(pin)
        text = text.replace(pin, moved)
        if count == 0:
            raise ValueError(f"pyproject.toml: no {name} {old} pin")
        summary.follow(f"pyproject.toml's {name}", old, new)
    if stale:
        manifest.write_text(text)
        if left := reports():
            raise ValueError(f"the pins check still reports, the pins moved: {left!r}")


if __name__ == "__main__":
    sys.exit(main("python", update))
