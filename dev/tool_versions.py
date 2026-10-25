#!/usr/bin/env python3
"""No tool version written by hand in a workflow, script, hook or justfile: what CI or a recipe
installs is a lock's -- a flake's nixpkgs, through `nix develop`, a flake's `tools` or
dev/nix-tools.sh -- or an action's own, moved by Dependabot (dprint/check's dprint,
cocogitto-action's cog, rustsec/audit-check's cargo-audit); cargo-generate's floor aside, which the
templates declare and no lock decides.

Read: every workflow and composite action, shell script, git hook and justfile git tracks, this
repository's and each template's, a command continued over lines (`\\`) as one. Refused, a line
each, naming it:
  * a tool given a version: `<name>@<version>` or `<name>@${{ <expression> }}` (`uses:
    <action>@<commit>` aside: Dependabot's), an install's `==`, `~=`, `--version` or `--vers`, an
    apt package's `=<version>`, `rustup install <version>`, an installer script given a version
    (`| sh -s <version>`, or its URL's `/<version>/`), an image at a version
    (`ghcr.io/...:<version>`, `docker run <image>:<version>`, `container:`, `image:`, `docker://`)
    -- a project's own image too: its name is its flake's (`nix eval .#image.imageName`). An IP's
    four parts are no tag (`--add-host db:10.0.0.1`);
  * a version input or variable set to a literal (`version: 0.9.5`, `toolchain: 1.85.0`,
    `typst-version: 0.15.1`, `ACTIONLINT: 1.7.12`, `export DPRINT_VERSION=0.61.1`) -- an
    interpreter's too (`python-version`): a project's own files name those;
  * a release download's URL with its version written in;
  * nixpkgs no lock holds: the flake registry's (`nix run nixpkgs#...`, `flake:nixpkgs#`,
    `nixpkgs/<branch>#`), a branch's head (`github:NixOS/nixpkgs#`, `.../nixos-25.05#`, `?ref=`,
    a tarball's, git's or a channel's URL, `--override-input`, `nix registry add`) or a revision
    typed in (`.../<commit>#`, `?rev=`: no lock update moves it; one interpolated, `.../$rev`, is
    read from a lock at run time, and let through), the channels' (`nix-shell -p`, `nix-env -i`,
    `=channel:`, `nix-channel`, `<nixpkgs>`, `NIX_PATH=`, `-I`/`--include nixpkgs=`): a lock's is
    the version, those whatever their branch holds that day. `--inputs-from <path>` resolves the
    registry's `nixpkgs` from that flake's lock (a local one: `--inputs-from github:...` is a
    branch's head again); a reference typed in stays one.
And an action not at a commit: every `uses:` but a local one (`./`) names its action at a full
commit SHA, its version in a comment (`@<40 hex> # v4.2.2`), as Dependabot keeps it -- a tag or a
branch moves under the workflow; and none names an image (`docker://`, at a tag, a digest or none:
no lock moves it).
A regex reads each command: a false positive is written another way, never allowed. Not read: a
version a step reads from a file at run time (`typst-version: ${{ steps.manifest.outputs.compiler
}}`) or a shell variable holds (`cargo install "just@$JUST"`) -- the file's, the variable's, so a
declared floor (`compiler`, the MSRV, `python-version`) passes, and a tool list kept in a file (the
old typst/tools.toml) would too: keep none; nor a toolchain named by date or chosen another way
(`nightly-2024-01-01`, `rustup default 1.85.0`, `cargo +1.85.0`), an installer downloaded, then
run, an image on another registry outside `docker`, `podman` and a workflow's keys (`crane copy`),
or one with a port.
Allowed: dev/install-cargo-generate.sh, the floor's installer, whose version must be each
template's `cargo_generate_version` floor (`>=<version>`), all three alike.

Usage:  python3 dev/tool_versions.py   (`just tool-versions-check`)
Exit:   0 = none by hand, 1 = one at least, each named.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FLOOR = "dev/install-cargo-generate.sh"
VERSION = r"v?\d+(?:\.\d+)+"
RULES = (
    # a tool at a version: `just@1.58.0`, `cargo install cocogitto@7.0.0`, install-action's
    # `just@${{ steps.pins.outputs.just }}` (an action's commit aside)
    ("a tool given a version", re.compile(rf"(?<![\w.-])[\w.+-]+@(?:{VERSION}|\$\{{\{{)")),
    # an install's version: `pip install x==1.2` or `x~=1.2`, `cargo binstall --version=1.2 x`,
    # `cargo install x --vers 1.2`, `apt-get install x=1.2-1`, `rustup toolchain install 1.85.0`
    (
        "an install given a version",
        re.compile(
            rf"install\b[^#\n]*(?:[=~]=\s*{VERSION}|--vers(?:ion)?[ =]{VERSION})"
            r"|\bapt(?:-get)?\s+install\b[^#\n]*\s[\w.+-]+=\d"
            rf"|\brustup\s+(?:toolchain\s+)?install\s+(?:[^#\n]*\s)?{VERSION}\b"
        ),
    ),
    # an installer script given its version: `curl ... | sh -s 0.61.1` (`| sudo sh -s -- -v
    # 0.61.1` too), or in its URL: `curl https://astral.sh/uv/0.4.0/install.sh | sh`
    (
        "an installer given a version",
        re.compile(
            rf"\|\s*(?:sudo\s+)?(?:ba)?sh\s+-s\s+(?:--\s+)?(?:-[\w-]+[ =])?{VERSION}"
            rf"|https?://\S*/{VERSION}/\S*[^#\n]*\|\s*(?:sudo\s+)?(?:ba)?sh\b"
        ),
    ),
    # an image at a version: `ghcr.io/typst/package-check:0.7.0` anywhere, `docker run
    # alpine:3.20`, `node:20`, a workflow's `container:`/`image:`/`docker://`; a tag of three parts
    # at most, so an IP (`--add-host db:172.17.0.1`) is none
    (
        "an image at a version",
        re.compile(
            r"(?:(?:ghcr|quay|docker)\.io/[\w./-]+|(?:mcr\.microsoft\.com|public\.ecr\.aws)/[\w./-]+"
            r"|\b(?:docker|podman)\s+(?:(?:container|image)\s+)?(?:run|pull|create)\b"
            r".*?(?<![\w.:/=-])[a-z][\w.-]*(?:/[\w./-]+)?"
            r"|^\s*-?\s*(?:container|image):\s*[\"']?[\w.-]+(?:/[\w./-]+)?|docker://[\w.-]+(?:/[\w./-]+)?)"
            r":v?\d+(?:\.\d+){0,2}(?![\d.])"
        ),
    ),
    # a version input or variable: `version: 0.9.5`, `typst-version: 0.15.1`, `toolchain: 1.85.0`,
    # `export DPRINT_VERSION=0.61.1` (a bare shell `version=` is a project's own: `just release`'s)
    (
        "a version set by hand",
        re.compile(
            rf"^\s*-?\s*(?:export\s+)?(?:[\w-]+[-_](?:version|VERSION)|VERSION|version(?=\s*:)|toolchain(?=\s*:))"
            rf"\s*[:=]\s*[\"']?{VERSION}"
        ),
    ),
    # an environment variable holding a version: `ACTIONLINT: 1.7.12`
    ("a version in a variable", re.compile(r"^\s+[A-Z][A-Z0-9_]*:\s*[\"']?v?\d+\.\d+\.\d+")),
    # a release download, its version in its URL
    ("a download's version written in", re.compile(rf"/releases/download/{VERSION}")),
    # nixpkgs no lock holds: the registry's, a branch's head, a revision typed in, the channels'
    (
        "nixpkgs no lock holds",
        re.compile(
            # the registry's: unless `--inputs-from` a local flake resolves the name from its lock
            r"^(?!.*--inputs-from[\s=]+[\"']?(?:\.|/|path:|\$)).*(?<![\w$}/.-])(?:flake:)?nixpkgs(?:/[\w.-]+)?#"
            # a reference typed in, whatever `--inputs-from` says: by `github:` (an installable, an
            # `--override-input`, a `nix registry add`), a tarball, git, a channel's tarball; but a
            # revision interpolated (`github:NixOS/nixpkgs/$rev`): a lock's, read at run time
            r"|(?i:github:nixos/nixpkgs)\b(?!/\$)"
            r"|(?i:github\.com/nixos/nixpkgs)(?:/archive/|/tarball/|\.git\b|\?|#)|(?i:channels\.nixos\.org/)"
            r"|\bnix-shell\b[^#\n]*\s(?:-p\b|--packages\b)|\bnix-env\b[^#\n]*\s(?:-i|--install\b)"
            r"|=channel:|\bnix-channel\b|<nixpkgs>|\bNIX_PATH=|(?:-I\s*|--include\s+)nixpkgs="
        ),
    ),
)
# a step's or a job's action: at its commit, the version in a comment
USES = re.compile(r"^\s*-?\s*uses:\s*[\"']?(?P<ref>[^\s\"'#]+)")
ACTION = re.compile(r"^\s*-?\s*uses:\s*[\"']?[^\s\"'#@]+@[0-9a-f]{40}[\"']?\s+#\s*\S")
WANTED = re.compile(
    r"(^|/)\.github/workflows/[^/]+\.ya?ml$|(^|/)action\.ya?ml$|\.sh$|(^|/)justfile$|(^|/)\.githooks/[^/]+$"
)


def files() -> list[str]:
    """What git tracks that installs a tool or runs one: workflows, actions, scripts, hooks,
    justfiles."""
    listed = subprocess.run(  # noqa: S603 - git, on this repository
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True  # noqa: S607
    ).stdout.split("\0")
    return sorted(path for path in listed if path and WANTED.search(path))


def floor_check() -> list[str]:
    """The floor's installer installs each template's declared floor."""
    errors = []
    installed = re.findall(r"(?m)^version=(\S+)$", (ROOT / FLOOR).read_text())
    if len(installed) != 1:
        return [f"{FLOOR}: not one `version=<version>` line"]
    for config in sorted(ROOT.glob("*/cargo-generate.toml")):
        requirement = tomllib.loads(config.read_text()).get("template", {}).get("cargo_generate_version", "")
        floor = requirement.removeprefix(">=")
        if floor != installed[0]:
            errors.append(
                f"{FLOOR} installs cargo-generate {installed[0]}, {config.parent.name}/cargo-generate.toml's floor"
                f" is {floor or 'none'} (`cargo_generate_version = \">=<version>\"`)"
            )
    return errors


def commands(text: str) -> list[tuple[int, str]]:
    """Each line, numbered, a command continued with `\\` joined to its first."""
    joined: list[tuple[int, str]] = []
    going = False
    # "\n" alone: splitlines() would also split at \f, \x1c... and number lines unlike git
    for n, line in enumerate(text.split("\n"), 1):
        # an odd run of backslashes continues (`\\\\` is one, literal); a comment ends at its line
        continued = (len(line) - len(line.rstrip("\\"))) % 2 == 1 and not line.lstrip().startswith("#")
        part = line[:-1] if continued else line
        if going:
            joined[-1] = (joined[-1][0], f"{joined[-1][1]} {part}")
        else:
            joined.append((n, part))
        going = continued
    return joined


def by_hand(paths: list[str]) -> list[str]:
    """Each line of `paths` giving a tool a version, named."""
    found = []
    for path in paths:
        for n, line in commands((ROOT / path).read_text(errors="replace")):
            if ACTION.match(line) or line.lstrip().startswith("#"):
                continue
            if (uses := USES.match(line)) and not uses["ref"].startswith("./"):
                ref = uses["ref"]
                if ref.startswith("docker://"):
                    # at a tag, a digest or none, chosen here: no lock moves it
                    found.append(f"{path}:{n}: an image a step runs ({ref!r}): take it from the lock")
                elif re.search(r"@[0-9a-f]{40}$", ref):
                    found.append(
                        f"{path}:{n}: an action at a commit, its version in no comment ({ref!r}): `@<sha> # v1.2.3`"
                    )
                else:
                    found.append(
                        f"{path}:{n}: an action not at a commit ({ref!r}): name its full commit SHA,"
                        " its version in a comment (`@<sha> # v1.2.3`), as Dependabot keeps it"
                    )
                continue
            for what, rule in RULES:
                if match := rule.search(line):
                    found.append(f"{path}:{n}: {what} ({match[0].strip()!r}): take it from the lock")
                    break
    return found


def main() -> int:
    paths = [path for path in files() if path != FLOOR]
    floor, versions = floor_check(), by_hand(paths)
    for error in floor + versions:
        print(f"error: {error}", file=sys.stderr)
    print(
        f"{len(paths)} files read: "
        + (f"{len(versions)} refused" if versions else "no tool version by hand, every action at its commit")
        + f"; the floor {'apart from the templates' if floor else 'as declared'}"
    )
    return 1 if floor or versions else 0


if __name__ == "__main__":
    sys.exit(main())
