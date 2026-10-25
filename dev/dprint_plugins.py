#!/usr/bin/env python3
"""The dprint plugins moved to their newest releases, and what follows them formatted anew.

Every dprint.json -- the root's and each template root's, whose plugins `just sync --check` holds
equal -- has `dprint config update` run on it: each plugin to its latest release, as dprint looks
it up, a release younger than three days held back (`--minimum-dependency-age`, Dependabot's
cooldown here; its reach, below). dprint may move a plugins.dprint.dev
URL to its npm package (`npm:@dprint/<name>@<version>`) as it does. Then the root's Markdown and
TOML are formatted by the new plugins (`dprint fmt`), shared/root/'s originals among them, and the
shared files' copies written anew from those (`just sync`); `just sync --check` and `dprint check`
must then pass. A template root's Markdown and TOML hold Liquid, formatted by a generated project:
the pull request's smoke tests run each one's dprint, and the summary says so.

dprint reports a plugin it could not update as a warning, and exits 0: a `Failed ...` or `Had
diagnostics ...` line it prints fails the update here, so a fetch lost is no "nothing moved" --
but `Failed resolving the npm package ... Keeping its url.`, after which dprint moves the URL as
before. That one, and each plugin it skipped or held back (`Skipping ...`, `Not moving ...`), is
noted in the summary, and as a warning of the run's when GitHub Actions runs it: the next run tries
again, and one noted every month is seen. The three days' hold reaches the plugins dprint takes from
npm alone: a plugins.dprint.dev URL moves to its newest release, as does one dprint holds back from
npm (`Not moving ... to npm yet`).

Usage:  python3 dev/dprint_plugins.py [--summary FILE]   (`just dprint-update`)
It may change only what dev/dprint.files lets through: anything else it changed is an error (a
path the tree had changed already is not held: dprint-plugins.yml's runs begin clean), as
dprint-plugins.yml's `propose` refuses it too.
Exit:   0 once updated; 1 if the update failed or changed what it may not, what it moved left in
        the working tree.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass

sys.path.append(str(pathlib.Path(__file__).resolve().parent))
from lock_core import ROOT, changed, code, unlisted  # noqa: E402 - dev/, put on the path above
from sync import jsonc, template_roots  # noqa: E402

LISTING = ROOT / "dev" / "dprint.files"
# dprint's own messages for a plugin it could not update, and for one it skipped, held back or kept
# on its URL (crates/dprint/src/commands/config.rs, 0.61.1)
FAILED = re.compile(r"\bFailed\b|\bHad diagnostics\b")
KEPT = "Failed resolving the npm package for "  # then "Keeping its url.": a failure but this one
NOTED = re.compile(r"\bSkipping\b|\bNot moving\b|\bKeeping its url\b")

# a plugin, by its name and version: plugins.dprint.dev's wasm, or npm's package (a checksum after
# either, `@<sha256>`)
URL = re.compile(r"https://plugins\.dprint\.dev/(?:(?P<owner>[\w.-]+)/)?(?P<name>[\w.-]+?)-v?(?P<version>\d[\w.+-]*)\.wasm")
NPM = re.compile(r"npm:(?:@(?P<owner>[\w.-]+)/)?(?P<name>[\w.-]+)@(?P<version>\d[\w.+-]*)")


def failure(line: str) -> bool:
    """Whether dprint's line says it could not update a plugin: its first failure not the npm
    lookup it falls back from (the line beginning so, a later "Failed" in it is no exception)."""
    found = FAILED.search(line)
    return found is not None and not line[found.start() :].startswith(KEPT)


@dataclass(frozen=True)
class Plugin:
    """A dprint.json's plugin entry: its name and version where they can be read, its source."""

    entry: str
    name: str
    version: str
    official: bool  # dprint's own: dprint/dprint-plugin-<name>, its releases there

    @classmethod
    def read(cls, entry: str) -> Plugin:
        found = URL.match(entry) or NPM.match(entry)
        if found is None:
            return cls(entry, entry, "?", official=False)
        owner = found["owner"]
        official = owner is None if found.re is URL else owner == "dprint"
        return cls(entry, found["name"], found["version"], official)

    def source(self) -> str:
        return "npm" if self.entry.startswith("npm:") else "its URL"


def configs() -> list[pathlib.Path]:
    """Each dprint.json: the root's, then each template root's."""
    return [ROOT / "dprint.json", *(ROOT / name / "dprint.json" for name in template_roots())]


def plugins(config: pathlib.Path) -> list[Plugin]:
    return [Plugin.read(entry) for entry in jsonc(config)["plugins"]]


def config_update(config: pathlib.Path, noted: dict[str, None]) -> None:
    """`dprint config update` on `config`, its messages echoed; a failure among them, an error, and
    each note kept (once: every config's are alike)."""
    done = subprocess.run(  # noqa: S603
        ["dprint", "config", "update", "--minimum-dependency-age", "P3D"],  # noqa: S607
        cwd=config.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    print(done.stdout, end="", file=sys.stderr)
    label = config.relative_to(ROOT)
    failed = [line.strip() for line in done.stdout.splitlines() if failure(line)]
    if done.returncode != 0:
        raise ValueError(f"{label}: `dprint config update` exited {done.returncode}: {'; '.join(failed) or 'see above'}")
    if failed:
        raise ValueError(f"{label}: `dprint config update` warned it could not update a plugin: {'; '.join(failed)}")
    noted.update(dict.fromkeys(line.strip() for line in done.stdout.splitlines() if NOTED.search(line)))


def moves(before: list[Plugin], after: list[Plugin]) -> list[str]:
    """Each plugin that moved, as Markdown: old to new, where its releases are."""
    old = {plugin.name: plugin for plugin in before}
    lines = []
    for plugin in after:
        was = old.get(plugin.name)
        if was is not None and was.entry == plugin.entry:
            continue
        # an entry read as no name and version is shown as code: nothing in it rendered
        name = plugin.name if plugin.version != "?" else code(plugin.entry)
        line = f"{name}: {was.version if was else 'new'} -> {plugin.version}"
        if was is not None and was.source() != plugin.source():
            line += f", now from {plugin.source()} ({code(plugin.entry)})"
        if plugin.official:
            line += f" ([releases](https://github.com/dprint/dprint-plugin-{plugin.name}/releases))"
        lines.append(line)
    kept = {plugin.name for plugin in after}
    lines += [
        f"{plugin.name if plugin.version != '?' else code(plugin.entry)}: removed"
        for plugin in before
        if plugin.name not in kept
    ]
    return lines


def update(noted: dict[str, None]) -> list[str]:
    """Every dprint.json updated, then, if a plugin moved, the root formatted and the copies synced;
    the moves (the root's: `just sync --check`, last, holds every other's to it)."""
    root, *_ = paths = configs()
    before = plugins(root)
    for config in paths:
        config_update(config, noted)
    moved = moves(before, plugins(root))
    if moved:
        shown("dprint", "fmt")
        shown("just", "sync")
        shown("dprint", "check")
    shown("just", "sync", "--check")
    return moved


def shown(*cmd: str) -> None:
    """A command run from the root, all it prints shown on standard error -- `dprint check` names a
    file it refuses on its standard output -- its failure an error."""
    print(f"+ {' '.join(cmd)}", file=sys.stderr)
    subprocess.run(cmd, cwd=ROOT, stdout=sys.stderr, check=True)  # noqa: S603


def markdown(moved: list[str], formatted: list[str], noted: list[str]) -> str:
    """The summary, for the commit and the pull request."""
    parts = ["Made by `just dprint-update`.", "", "Plugins moved, in every dprint.json:"]
    parts += [f"- {line}" for line in moved] or ["- none"]
    if formatted:
        parts += ["", "Formatted anew by them:", *(f"- {code(path)}" for path in formatted)]
    if noted:
        parts += ["", "dprint noted (the next run tries again):", *(f"- {code(line)}" for line in noted)]
    if moved:
        parts += [
            "",
            "Left to a person (look, fix, push to this branch):",
            "- The templates' Markdown and TOML hold Liquid, so the root formats none of it: the smoke "
            "tests run each generated project's `dprint check`. A file one fails, formatted in the "
            "template (in a generated project, `dprint fmt`, the change carried back).",
        ]
    return "\n".join(parts) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Update the dprint plugins, and format what follows them.")
    parser.add_argument("--summary", type=pathlib.Path, help="write the summary (Markdown) here")
    args = parser.parse_args()
    dirty = changed()
    noted: dict[str, None] = {}
    try:
        moved = update(noted)
        made = changed() - dirty
        if outside := unlisted(made, LISTING):
            raise ValueError(f"it changed what dev/dprint.files does not list: {', '.join(outside)}")
    except (subprocess.CalledProcessError, OSError, KeyError, ValueError) as exc:
        print(f"error: the dprint plugins' update: {exc!r}", file=sys.stderr)
        print("  what it moved before failing is left in the working tree (`git status`)", file=sys.stderr)
        return 1
    text = markdown(moved, sorted(path for path in made if not path.endswith("dprint.json")), list(noted))
    print(text)
    # an annotation on the run: with nothing moved there is no pull request to say it in
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for line in noted:
            # a workflow command's data, escaped as GitHub reads it
            escaped = line.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            print(f"::warning::dprint noted: {escaped}")
    if args.summary:
        args.summary.write_text(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
