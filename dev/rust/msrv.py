"""rust's `msrv` prompt and its lock: the stable releases the shipped flake.lock's rust-overlay
knows, and the regex and range the prompt asks for from them. render-check holds the prompt to
them; `just lock-update rust` writes them after moving the lock.
"""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import tempfile

from lock_core import NIX_FLAGS, get_flake, path_ref  # dev/, which its importer puts on the path

# The oldest MSRV the template takes: a release's `cargo publish --workspace` (publish-crates.yml)
# is cargo 1.90's.
MSRV_FLOOR = 90
Release = tuple[int, int, int]


def rust_releases(nix: str, flake_nix: str, lock: pathlib.Path) -> list[Release]:
    """The stable releases `lock`'s rust-overlay knows, for a rendered flake.nix.

    The lock must be this flake.nix's as it stands (`--no-update-lock-file`: nothing to relock);
    then the locked rust-overlay alone is fetched -- nixpkgs is not, the smoke test's Nix job
    builds with it -- and its stable manifests' names read by Nix.
    """

    def nix_run(*args: str) -> str:
        done = subprocess.run([nix, *NIX_FLAGS, *args], capture_output=True, text=True, check=False)  # noqa: S603
        if done.returncode != 0:
            tail = "\n      ".join(done.stderr.strip().splitlines()[-6:])
            raise ValueError(f"nix {args[0]} {args[1]}: {tail}")
        return done.stdout

    with tempfile.TemporaryDirectory() as tmp:
        flake = pathlib.Path(tmp)
        (flake / "flake.nix").write_text(flake_nix)
        shutil.copyfile(lock, flake / "flake.lock")
        try:
            nix_run("flake", "metadata", "--no-update-lock-file", "--json", path_ref(flake))
        except ValueError as exc:
            msg = f"flake.lock is not this flake.nix's, or a fetch failed: {exc}"
            raise ValueError(msg) from None
        overlay = f"{get_flake(flake)}.inputs.rust-overlay"
        expr = f'let m = import ({overlay} + "/manifests/stable");'
        expr += " in { names = builtins.attrNames m; inherit (m) latest; }"
        stable = json.loads(nix_run("eval", "--impure", "--json", "--expr", expr))
    versions = (re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", v) for v in stable["names"])
    releases = sorted((int(m[1]), int(m[2]), int(m[3])) for m in versions if m)
    if not releases or ".".join(map(str, releases[-1])) != stable["latest"]:
        raise ValueError("rust-overlay's stable manifests: none read, or the newest not `latest`")
    return releases


def msrv_regex(releases: list[Release]) -> str:
    """The `msrv` regex these releases ask for: each minor from the floor, bare or a patch of it."""
    patches: dict[int, list[int]] = {}
    for major, minor, patch in releases:
        if major == 1 and minor >= MSRV_FLOOR:
            patches.setdefault(minor, []).append(patch)
    parts = []
    for minor, ps in sorted(patches.items()):
        if len(ps) == 1:
            p = str(ps[0])
        elif all(x < 10 for x in ps):
            p = "[" + "".join(map(str, ps)) + "]"
        else:
            p = "(" + "|".join(map(str, ps)) + ")"
        parts.append(f"^1\\.{minor}(\\.{p})?$")
    return "|".join(parts)


def msrv_span(releases: list[Release]) -> str:
    """The range the prompt names: the floor to the newest release."""
    return f"1.{MSRV_FLOOR} to {'.'.join(map(str, releases[-1]))}"
