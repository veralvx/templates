#!/usr/bin/env python3
"""typst's lock update (dev/lock_core.py's): typst/flake.lock -- the root's too, one original in
shared/ (`just flake-sync`) -- moved to its inputs' newest. Every tool follows it: a typst
project's CI builds the flake's `tools` (.github/install-tools.sh), so nothing is pinned apart;
each that moved is in the summary (lock_core's `update_flake`).

Left to a person, and said in the summary: a new Typst's rendering, which the tests' references
are; the `compiler` prompt, which render-check names; typst-package-check, an input at a tag
`nix flake update` keeps.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from lock_core import ROOT, Summary, lock_inputs, main, run, update_flake  # noqa: E402 - dev/, put on the path above

TEMPLATE = ROOT / "typst"


def update(summary: Summary) -> None:
    before, after = update_flake(summary, TEMPLATE)
    run("just", "flake-sync")
    old, new = before.get("typst"), after.get("typst")
    if old is not None and new is not None and old != new:
        summary.left.append(
            f"Typst {old} -> {new}: the tests' references are its rendering -- those the smoke test "
            "fails, `just update` in a generated project, the difference looked at, and its "
            "tests/*/ref/ copied back to typst/tests/"
        )
    tag = lock_inputs(TEMPLATE / "flake.lock")["package-check"]["original"].get("ref", "?")
    summary.left.append(
        f"typst-package-check stays at {tag}, its flake input's tag: a newer one is moved by hand -- "
        "the tag in typst/flake.nix and the root's, then `nix flake update package-check`"
    )


if __name__ == "__main__":
    sys.exit(main("typst", update))
