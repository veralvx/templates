"""What every template's lock update shares: dev/<template>/lock.py runs it with its own update.

A template's flake.lock is moved to its inputs' newest (`nix flake update`), and what the
template holds to it follows -- each template's update says what: pins, a prompt, dist's
version -- and each dev-shell tool that moved is said. Then render-check runs, and a summary is
written for the commit and the pull request: each input moved, each value that followed, and
what is left to a person -- render-check's failures, and each line of the documents and prompts
naming a version that moved.

Usage:  python3 dev/<template>/lock.py [--summary FILE]   (`just lock-update <template>`)
It may change only what dev/<template>/lock.files lists: anything else it changed is an error (a
path the tree had changed already is not held: locks.yml's runs begin clean).

Exit:   0 once updated, whatever render-check says (the summary does); 1 if the update failed or
        changed what it may not, what it moved left in the working tree.
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tomllib
import urllib.parse
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
NIX_FLAGS = ["--extra-experimental-features", "nix-command flakes"]
# where a version a person reads is written: every document but a changelog (git-cliff's, history),
# and the prompts' comments (a git pathspec's `*` crosses folders)
DOCUMENTS = ("*.md", "*/cargo-generate.toml", ":(exclude)*CHANGELOG.md")
# each package of a dev shell, by name, at its version: what Nix evaluates, nothing built
SHELL_TOOLS = (
    "ps: builtins.listToAttrs (map (p: let d = builtins.parseDrvName p.name; in"
    " { name = p.pname or d.name; value = p.version or d.version; }) ps)"
)
# what this repository's CI takes from a template's lock beyond its dev shell (dev/nix-tools.sh):
# the smoke tests' Nix jobs, and python's generate job, generate with its cargo-generate
CI_TOOLS = ("cargo-generate",)


def run(*cmd: str, cwd: pathlib.Path = ROOT) -> str:
    """A command's standard output; its standard error passes through, a failure stops the update."""
    print(f"+ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.run(cmd, cwd=cwd, check=True, stdout=subprocess.PIPE, text=True).stdout  # noqa: S603


def path_ref(path: pathlib.Path) -> str:
    """The flake at `path` as a reference read as its files are (`path:`, not git's view), the path
    percent-encoded, as a flake reference's URL must be (`é` or a space is refused as no absolute
    path) -- which also leaves nothing for a Nix string to escape."""
    return f"path:{urllib.parse.quote(str(path))}"


def get_flake(path: pathlib.Path) -> str:
    """The Nix expression of the flake at `path` (`path_ref`'s): impure."""
    return f'(builtins.getFlake "{path_ref(path)}")'


def nix(*args: str, cwd: pathlib.Path) -> str:
    return run("nix", *NIX_FLAGS, *args, cwd=cwd)


def evaluate(flake: pathlib.Path, attribute: str) -> str:
    """A flake output's string, evaluated on this lock as it stands (nothing built)."""
    return nix("eval", "--no-update-lock-file", "--raw", f".#{attribute}", cwd=flake)


def generate(template: str, kind: str) -> pathlib.Path:
    """A project of `kind` generated as `just generate` makes it, its first commit made."""
    return ROOT / run("just", "generate", template, kind).strip()


def shell_tools(flake: pathlib.Path) -> dict[str, str]:
    """The flake's dev shell's packages (x86_64-linux's), each at its version."""
    attribute = ".#devShells.x86_64-linux.default.nativeBuildInputs"
    return json.loads(nix("eval", "--no-update-lock-file", "--json", attribute, "--apply", SHELL_TOOLS, cwd=flake))


def ci_tools(flake: pathlib.Path) -> dict[str, str]:
    """CI_TOOLS, each at the version dev/nix-tools.sh installs: the flake's nixpkgs input, as its
    lock locks it (x86_64-linux's)."""
    pkgs = f"{get_flake(flake)}.inputs.nixpkgs.legacyPackages.x86_64-linux"
    expr = f"let pkgs = {pkgs}; in {{ {' '.join(f'{name} = pkgs.{name}.version;' for name in CI_TOOLS)} }}"
    return json.loads(nix("eval", "--impure", "--json", "--expr", expr, cwd=flake))


def update_flake(summary: Summary, flake: pathlib.Path) -> tuple[dict[str, str], dict[str, str]]:
    """The flake's inputs moved to their newest (`nix flake update`), and each tool of its dev
    shell that moved with them followed in the summary -- a tool is the lock's, CI's too (through
    Nix, or a pin the lock holds), so its documents' mentions are listed for a person; the shell's
    tools before and after. CI_TOOLS too, the smoke tests' -- their mentions not listed: a document
    names cargo-generate's floor, which no lock moves."""
    before, ci_before = shell_tools(flake), ci_tools(flake)
    nix("flake", "update", cwd=flake)
    after, ci_after = shell_tools(flake), ci_tools(flake)
    for name, new in sorted(after.items()):
        if (old := before.get(name)) is not None and old != new:
            summary.follow(f"the dev shell's {name}", old, new)
    for name, new in sorted(ci_after.items()):
        if (old := ci_before.get(name)) is not None and old != new:
            summary.followed.append(f"the smoke tests' {name} (the Nix jobs', python's generate job's): {old} -> {new}")
    return before, after


def lock_in_project(summary: Summary, template: str, kind: str) -> tuple[pathlib.Path, dict[str, str]]:
    """The template's lock moved in a generated project -- its flake.nix holds Liquid, which Nix
    cannot read -- and copied back (`update_flake`); the project, whose flake.nix is the rendered
    one, and its dev shell's tools now."""
    project = generate(template, kind)
    _, tools = update_flake(summary, project)
    shutil.copyfile(project / "flake.lock", ROOT / template / "flake.lock")
    return project, tools


def kinds(template: str) -> list[str]:
    config = tomllib.loads((ROOT / template / "cargo-generate.toml").read_text())
    return list(config["placeholders"]["project_kind"]["choices"])


def lock_inputs(lock: pathlib.Path) -> dict[str, dict[str, Any]]:
    """Each of the flake's own inputs' node in its lock (one that follows another's is that one's,
    and not listed)."""
    data = json.loads(lock.read_text())
    nodes = data["nodes"]
    return {name: nodes[target] for name, target in nodes[data["root"]]["inputs"].items() if isinstance(target, str)}


def inputs(lock: pathlib.Path) -> dict[str, str]:
    """Each of the flake's own inputs, as the lock holds it: its source, revision and date."""
    out = {}
    for name, node in lock_inputs(lock).items():
        original, locked = node.get("original", {}), node.get("locked", {})
        if "owner" in original:  # github:, gitlab:, sourcehut:
            source = "/".join(str(original[k]) for k in ("host", "owner", "repo", "ref") if k in original)
        else:  # git+, a tarball's URL, a path, a registry's name
            source = str(original.get("url") or original.get("path") or original.get("id", "?"))
            source += f"?ref={original['ref']}" if "ref" in original else ""
        date = datetime.datetime.fromtimestamp(locked.get("lastModified", 0), datetime.UTC).date()
        # a tarball or a path has no revision: its content's hash tells it moved
        revision = str(locked.get("rev") or locked.get("narHash", "?")).removeprefix("sha256-")
        out[name] = f"{source} {revision[:12]} ({date})"
    return out


@dataclass
class Summary:
    """What the update did, and what it leaves to a person."""

    template: str
    moved: list[str] = field(default_factory=list)
    followed: list[str] = field(default_factory=list)
    left: list[str] = field(default_factory=list)
    # each old value that moved: its documents' mentions are listed for a person
    old_values: set[str] = field(default_factory=set)

    def follow(self, what: str, old: str, new: str) -> None:
        self.followed.append(f"{what}: {old} -> {new}")
        self.old_values.add(old)

    def check(self, output: str, returncode: int) -> None:
        """render-check's failures left to a person, each in full (a message's later lines are
        indented under its `FAIL` line)."""
        failures: list[list[str]] = []
        current: list[str] | None = None
        for line in output.splitlines():
            if line.strip().startswith("FAIL "):
                current = [line.strip().removeprefix("FAIL ")]
                failures.append(current)
            elif current is not None and line.startswith("    "):
                current.append(line[4:])
            else:
                current = None
        self.left += [f"render-check:\n{fenced(lines)}" for lines in failures]
        if returncode != 0 and not failures:
            self.left.append(f"render-check exited {returncode}, naming no check: run `just render-check`")

    def markdown(self) -> str:
        parts = [f"Made by `just lock-update {self.template}`.", "", "Inputs moved:"]
        parts += [f"- {line}" for line in self.moved] or ["- none"]
        if self.followed:
            parts += ["", "What follows them, moved too:", *(f"- {line}" for line in self.followed)]
        if self.left:
            parts += ["", "Left to a person (look, fix, push to this branch):"]
            parts += ["- " + item.replace("\n", "\n  ") for item in self.left]
        return "\n".join(parts) + "\n"


def code(text: str) -> str:
    """`text` as Markdown code, whatever backticks it holds (nothing in it rendered: no mention, no
    link)."""
    ticks = "`" * (max((len(found) for found in re.findall("`+", text)), default=0) + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{ticks}{pad}{text}{pad}{ticks}"


def fenced(lines: list[str]) -> str:
    """`lines` as a Markdown code block."""
    fence = "`" * max([3, *(len(found) + 1 for line in lines for found in re.findall("`+", line))])
    return "\n".join([f"{fence}text", *lines, fence])


def mentions(old: str) -> list[str]:
    """Each line of DOCUMENTS naming the version `old` -- `v` before it or not, and no part of a
    longer version or word (0.15.0 is not in 10.15.0, 0.15.0.1 or a0.15.0) -- as Markdown. A
    version is not a tool's own: another tool's, the same, is listed too."""
    version = re.compile(rf"(?<![\w.])v?{re.escape(old)}(?!\w|\.\d)")
    found = []
    for path in filter(None, run("git", "ls-files", "-z", "--", *DOCUMENTS).split("\0")):
        for n, line in enumerate((ROOT / path).read_text(errors="replace").splitlines(), 1):
            if version.search(line):
                found.append(f"{code(f'{path}:{n}')} names {old}: {code(line.strip())}")
    return found


def unlisted(paths: Iterable[str], listing: pathlib.Path) -> list[str]:
    """Each of `paths` that `listing` does not let through, as dev/unlisted.sh reads it -- the one
    reader of such a list, dev/propose.sh's too. A path with a newline in it is never one's: it
    would read as two."""
    paths = sorted(paths)
    given = "".join(f"{path}\n" for path in paths if "\n" not in path)
    done = subprocess.run(  # noqa: S603 - this repository's own script
        [ROOT / "dev" / "unlisted.sh", listing], input=given, stdout=subprocess.PIPE, text=True, check=True
    )
    return [path for path in paths if "\n" in path] + done.stdout.splitlines()


def changed() -> set[str]:
    """Each path git sees changed, added or removed in the working tree (a rename as both)."""
    status = run("git", "status", "--porcelain=v1", "-z", "--no-renames", "--untracked-files=all")
    return {entry[3:] for entry in status.split("\0") if entry}


def main(template: str, update: Callable[[Summary], None]) -> int:
    parser = argparse.ArgumentParser(description=f"Update {template}'s flake.lock and what follows it.")
    parser.add_argument("--summary", type=pathlib.Path, help="write the summary (Markdown) here")
    args = parser.parse_args()
    lock = ROOT / template / "flake.lock"
    before, dirty = inputs(lock), changed()
    summary = Summary(template)
    try:
        update(summary)
        if outside := unlisted(changed() - dirty, ROOT / "dev" / template / "lock.files"):
            raise ValueError(f"it changed what dev/{template}/lock.files does not list: {', '.join(outside)}")
    except (subprocess.CalledProcessError, OSError, KeyError, ValueError) as exc:
        print(f"error: {template}'s lock update: {exc!r}", file=sys.stderr)
        print("  what it moved before failing is left in the working tree (`git status`)", file=sys.stderr)
        return 1
    after = inputs(lock)
    summary.moved = [
        f"{name}: {before.get(name, 'new')} -> {now}"
        for name, now in after.items() if now != before.get(name)
    ]
    summary.moved += [f"{name}: removed" for name in before if name not in after]
    checked = subprocess.run(  # noqa: S603
        ["just", "render-check", template], cwd=ROOT, capture_output=True, text=True, check=False  # noqa: S607
    )
    summary.check(checked.stdout, checked.returncode)
    for old in sorted(summary.old_values):
        summary.left += mentions(old)
    text = summary.markdown()
    print(text)
    if args.summary:
        args.summary.write_text(text)
    return 0
