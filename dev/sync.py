#!/usr/bin/env python3
"""The shared files' copies: `just sync` writes them, `just sync --check` checks them (as
`just checks` does). shared/manifest.toml names each original and the templates it goes into.

Checked, each a failure that names the file:
  * the manifest: each original listed exists, a regular file, under shared/root/ or
    shared/template/ as its section says, and each file there is listed; each template it names is
    a template root (a top-level folder, not hidden, holding a cargo-generate.toml); each path is a
    plain relative one that lands nowhere else's (not in a template root, shared/, dev/ or .git, nor
    a cargo-generate.toml or justfile; a [root] one holds no Liquid, as cargo-generate renders names);
  * each copy -- the root's of a [root] original, each listed template's -- exists as a regular file
    reached through no symlink (cargo-generate leaves a symlink out of a project), holds the
    original's bytes, and is executable exactly when the original is;
  * a [root] original holds no Liquid where a template renders it -- not excluded by that
    template's cargo-generate.toml as cargo-generate reads it (gitignore patterns; a template with an
    `include` list is refused, as it makes the exclude list moot): the root's copy would not be what
    a project gets;
  * each recipe in shared/recipes.just -- its comments, attributes, line and body -- stands the same
    in the root justfile and every template's (every comment and attribute line right above a
    recipe is its own: a justfile's own comment keeps a blank line between);
  * the template roots are those the root cargo-generate.toml offers (sub_templates), the root
    dprint.json leaves to their own checks (excludes); every dprint.json names the same plugins,
    and formats TOML alike (its `toml` settings and the global ones, which reach every plugin), as
    the TOML they share must pass each one's check;
  * dev/dprint.files, as dev/unlisted.sh reads it, lets through what `just dprint-update` writes --
    every dprint.json, each copy of a Markdown or TOML [root] original -- and refuses a template
    root's and shared/template/'s own Markdown and TOML;
  * .github/dependabot.yml's github-actions entry names `/` and each folder of workflows below
    shared/ and in a template root, once each, and nothing else.

Writing fixes the copies and the recipes, each file replaced whole (written aside, then renamed);
a recipe is replaced where it stands, so one missing stays a failure; then everything is checked,
and the rest is a person's to fix.

Usage:  python3 dev/sync.py [--check]   (Python 3.11+, the standard library alone; bash)
Exit:   0 = in sync, 1 = not (each failure printed), 2 = a usage error.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHARED = ROOT / "shared"
KINDS = {"root": SHARED / "root", "template": SHARED / "template"}
RECIPES = SHARED / "recipes.just"
# a Liquid tag or output, as cargo-generate renders them
LIQUID = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.DOTALL)
# a dprint.json's whole-line comment, which JSON has not (one after a value is left to fail)
JSONC_COMMENT = re.compile(r"(?m)^\s*//.*$")
# files a template root and the repository root each hold their own of, never a copy
OWN = ("cargo-generate.toml", "justfile")


class Failures(list[str]):
    def __call__(self, message: str) -> None:
        self.append(message)


def template_roots() -> list[str]:
    """The top-level folders holding a cargo-generate.toml, hidden ones aside (as the justfile's
    `*/cargo-generate.toml` reads them)."""
    return sorted(p.parent.name for p in ROOT.glob("*/cargo-generate.toml") if not p.parent.name.startswith("."))


def through_symlink(path: pathlib.Path) -> bool:
    """Whether path, or a folder between ROOT and it, is a symlink."""
    rel = path.relative_to(ROOT)
    return any((ROOT / pathlib.Path(*rel.parts[: i + 1])).is_symlink() for i in range(len(rel.parts)))


def executable(path: pathlib.Path) -> bool:
    return bool(path.stat().st_mode & stat.S_IXUSR)


def write_file(path: pathlib.Path, data: bytes, mode: int) -> None:
    """path's content and mode replaced whole: written aside, then renamed over it. Aside is .git
    when it is a folder on path's file system (a leftover there ships in no project), else path's
    folder (a worktree, or no .git: a leftover `sync-*` file shows in `git status`)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    git = ROOT / ".git"
    same_device = git.is_dir() and git.stat().st_dev == path.parent.stat().st_dev
    aside_in = git if same_device else path.parent
    fd, aside = tempfile.mkstemp(dir=aside_in, prefix=f"sync-{path.name}.")
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
        os.chmod(aside, mode)
        os.replace(aside, path)
    except BaseException:
        pathlib.Path(aside).unlink(missing_ok=True)
        raise


class PatternError(ValueError):
    """A line cargo-generate's matcher refuses: with it, cargo-generate generates nothing."""


def glob_regex(glob: str) -> bytes:
    """globset 0.4's regex for a glob, with ignore 0.4's options (literal separators, backslash
    escapes, unclosed classes allowed): its Parser and Tokens::to_regex_with, step by step."""
    chars, pos = list(glob), 0
    prev = cur = None
    stack: list[int] = []  # where each open alternation's branches start
    branches: list[list[tuple]] = [[]]
    unclosed_class = False

    def bump() -> str | None:
        nonlocal pos, prev, cur
        prev = cur
        cur = chars[pos] if pos < len(chars) else None
        pos += cur is not None
        return cur

    def peek() -> str | None:
        return chars[pos] if pos < len(chars) else None

    def push(token: tuple) -> None:
        branches[-1].append(token)

    while (c := bump()) is not None:
        if c == "?":
            push(("any",))
        elif c == "*":
            before = prev
            if peek() != "*":
                push(("zero_or_more",))
                continue
            bump()
            if not branches[-1]:
                if peek() not in (None, "/"):
                    push(("zero_or_more",)), push(("zero_or_more",))
                else:
                    push(("recursive_prefix",))
                    bump()
                continue
            if before != "/" and (len(branches) <= 1 or before not in (",", "{")):
                push(("zero_or_more",)), push(("zero_or_more",))
                continue
            nxt = peek()
            if nxt is None:
                bump()
                suffix = True
            elif nxt in (",", "}") and len(branches) >= 2:
                suffix = True
            elif nxt == "/":
                bump()
                suffix = False
            else:
                push(("zero_or_more",)), push(("zero_or_more",))
                continue
            last = branches[-1].pop()
            if last[0] in ("recursive_prefix", "recursive_suffix"):
                push(last)
            else:
                push(("recursive_suffix",) if suffix else ("recursive_zero_or_more",))
        elif c == "[" and not unclosed_class:
            saved = (pos, prev, cur)
            negated = peek() in ("!", "^")
            if negated:
                bump()
            ranges: list[list[str]] = []
            first, in_range = True, False
            while True:
                k = bump()
                if k is None:  # unclosed: a literal `[`, and no class after it
                    pos, prev, cur = saved
                    unclosed_class = True
                    push(("literal", "["))
                    break
                if k == "]" and not first:
                    if in_range:
                        ranges.append(["-", "-"])
                    push(("class", negated, ranges))
                    break
                if k == "-" and not first:
                    if in_range:
                        ranges[-1][1], in_range = "-", False
                        if ranges[-1][1] < ranges[-1][0]:
                            raise PatternError(f"invalid range {ranges[-1][0]}-{ranges[-1][1]}")
                    else:
                        in_range = True
                elif in_range:
                    ranges[-1][1], in_range = k, False
                    if ranges[-1][1] < ranges[-1][0]:
                        raise PatternError(f"invalid range {ranges[-1][0]}-{ranges[-1][1]}")
                else:
                    ranges.append([k, k])
                first = False
        elif c == "{":
            stack.append(len(branches))
            branches.append([])
        elif c == "}":
            if not stack:
                raise PatternError("unopened alternation")
            start = stack.pop()
            alternates = branches[start:]
            del branches[start:]
            push(("alternates", alternates))
        elif c == "," and stack:
            branches.append([])
        elif c == "\\":
            escaped = bump()
            if escaped is None:
                raise PatternError("dangling escape")
            push(("literal", escaped))
        else:
            push(("literal", c))
    if len(branches) > 1:
        raise PatternError("unclosed alternation")

    def literal(ch: str) -> bytes:
        return b"".join(re.escape(bytes([b])) if b < 0x80 else b"\\x%02x" % b for b in ch.encode())

    def to_regex(tokens: list[tuple]) -> bytes:
        out = b""
        for token in tokens:
            kind = token[0]
            if kind == "literal":
                out += literal(token[1])
            elif kind == "any":
                out += b"[^/]"
            elif kind == "zero_or_more":
                out += b"[^/]*"
            elif kind == "recursive_prefix":
                out += b"(?:/?|.*/)"
            elif kind == "recursive_suffix":
                out += b"/.*"
            elif kind == "recursive_zero_or_more":
                out += b"(?:/|/.*/)"
            elif kind == "class":
                out += b"[" + (b"^" if token[1] else b"")
                for low, high in token[2]:
                    out += literal(low) if low == high else literal(low) + b"-" + literal(high)
                out += b"]"
            else:
                parts = [part for part in map(to_regex, token[1]) if part]  # empty ones dropped
                if parts:
                    out += b"(?:" + b"|".join(parts) + b")"
        return out

    tokens = branches[0]
    # \Z, not $: Python's $ also matches before a final newline
    return b"^" + (b".*" if tokens == [("recursive_prefix",)] else to_regex(tokens)) + b"\\Z"


def gitignore_rule(pattern: str) -> tuple[re.Pattern[bytes], bool, bool] | None:
    """A gitignore line as cargo-generate's matcher reads it (ignore 0.4's
    GitignoreBuilder::add_line, step by step): (its regex, whether it lets a path through, whether
    it matches folders only); None for a blank line or a comment; PatternError if refused."""
    line = pattern
    if line.startswith("#"):
        return None
    if not line.endswith("\\ "):
        line = line.rstrip()
    if not line:
        return None
    negate = absolute = only_dir = False
    if line.startswith(("\\!", "\\#")):
        line = line[1:]
        absolute = line.startswith("/")
    else:
        if line.startswith("!"):
            negate, line = True, line[1:]
        if line.startswith("/"):
            absolute, line = True, line[1:]
    if line.endswith("/"):
        only_dir, line = True, line[:-1]
        if line.endswith("\\"):
            line = line[:-1]
    if not absolute and "/" not in line and not (line.startswith("**/") or line == "**"):
        line = "**/" + line  # no slash: it matches at any depth
    if line.endswith("/**"):  # everything inside, not the folder itself
        line += "/*"
    try:
        # DOTALL: globset's regexes let `.` match a newline
        return re.compile(glob_regex(line), re.DOTALL), negate, only_dir
    except re.error as error:  # a regex globset would have built: a bug here, said plainly
        raise PatternError(f"no regex for it here ({error})") from error


def excluded_by(rel: str, patterns: list[str]) -> bool:
    """cargo-generate's `matched_path_or_any_parents(rel, false)`: the path, then each folder above
    it, until one is matched; within one, the last matching line decides (`!` lets it through).
    PatternError if a line is refused."""
    rules = [r for r in map(gitignore_rule, patterns) if r is not None]
    parts = rel.split("/")
    for depth in range(len(parts), -1, -1):  # down to "", a top-level path's parent
        path, is_dir = "/".join(parts[:depth]).encode(), depth < len(parts)
        for regex, negate, only_dir in reversed(rules):
            if (is_dir or not only_dir) and regex.match(path):
                return not negate
    return False


def exclusions(template: str) -> list[list[str]] | str:
    """Every exclude list a project of the template can be generated with: the base list with each
    subset of the conditional lists appended (cargo-generate appends those of the conditions that
    hold, in no set order -- a HashMap's -- and a subset in file order gives the verdict any order
    of it would: the last list to match at the deepest level a rule matches decides); or why they
    cannot be read."""
    try:
        config = tomllib.loads((ROOT / template / "cargo-generate.toml").read_text())
    except (OSError, tomllib.TOMLDecodeError) as error:
        return f"unreadable ({error})"
    base, conditional = config.get("template", {}), config.get("conditional", {})
    if not isinstance(base, dict) or not isinstance(conditional, dict):
        return "a [template] or [conditional] that is no table"
    conditionals = [c for c in conditional.values() if isinstance(c, dict)]
    if any("include" in s for s in (base, *conditionals)):
        return "an include list, which makes cargo-generate set the exclude list aside"
    lists = [base.get("exclude", []), *(c["exclude"] for c in conditionals if "exclude" in c)]
    if not all(isinstance(x, list) and all(isinstance(p, str) for p in x) for x in lists):
        return "an exclude list that is no list of strings"
    extra = lists[1:]
    if len(extra) > 10:
        return "more than ten conditional exclude lists, too many combinations to check"
    return [lists[0] + [p for i, x in enumerate(extra) if mask >> i & 1 for p in x] for mask in range(2 ** len(extra))]


def placement_error(kind: str, rel: str, templates: list[str]) -> str | None:
    parts = rel.split("/")
    if not rel or rel.startswith("/") or any(p in ("", ".", "..") for p in parts):
        return "no plain relative path"
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in rel):
        return "a path holding a control character"
    folded = [p.casefold() for p in parts]  # a case-insensitive file system takes `Justfile` for it
    if ".git" in folded or folded[-1] in OWN:
        return "a path no copy may take (.git, or a cargo-generate.toml or justfile: each folder's own)"
    if kind == "root" and folded[0] in {t.casefold() for t in templates} | {"shared", "dev"}:
        return "a path inside a template root, shared/ or dev/, which a root copy may not take"
    if kind == "root" and LIQUID.search(rel):
        return "a path holding Liquid, which cargo-generate renders in a template"
    return None


Copy = tuple[str, str, pathlib.Path, pathlib.Path, "str | None"]


def copies(fail: Failures, templates: list[str]) -> list[Copy]:
    """(kind, its path, original, copy, the copy's template or None for the root's) for every copy
    the manifest makes; the manifest's own errors failed."""
    try:
        manifest = tomllib.loads((SHARED / "manifest.toml").read_text())
    except (OSError, tomllib.TOMLDecodeError) as error:
        fail(f"shared/manifest.toml: unreadable ({error})")
        return []
    for key in manifest.keys() - KINDS.keys():
        fail(f"shared/manifest.toml: [{key}] is no section ([root], [template])")
    out: list[Copy] = []
    listed = set()
    for kind, folder in KINDS.items():
        section = manifest.get(kind, {})
        if not isinstance(section, dict):
            fail(f"shared/manifest.toml: {kind} is not a section")
            continue
        for rel, into in section.items():
            label = f"shared/{kind}/{rel}"
            listed.add(folder / rel)
            if problem := placement_error(kind, rel, templates):
                fail(f"shared/manifest.toml: {rel!r}: {problem}")
                continue
            original = folder / rel
            if through_symlink(original) or not original.is_file():
                fail(f"{label}: listed in shared/manifest.toml, but no regular file (a symlink is none)")
                continue
            if into == "all":
                names = templates
            elif isinstance(into, list) and into and all(isinstance(n, str) for n in into):
                for name in sorted(set(into) - set(templates)):
                    fail(f"shared/manifest.toml: {rel} names {name!r}, which is no template root")
                names = sorted({n for n in into if n in templates})
            else:
                fail(f'shared/manifest.toml: {rel} = {into!r}: "all" or a list of template roots')
                continue
            if kind == "root":
                out.append((kind, rel, original, ROOT / rel, None))
            out.extend((kind, rel, original, ROOT / name / rel, name) for name in names)
    for folder in KINDS.values():
        for path in sorted(p for p in folder.rglob("*") if p.is_file() or p.is_symlink()):
            if path not in listed:
                fail(f"{path.relative_to(ROOT)}: not in shared/manifest.toml")
    seen: dict[pathlib.Path, str] = {}
    for kind, rel, _, copy, _ in out:
        source = f"shared/{kind}/{rel}"
        if seen.setdefault(copy, source) != source:
            fail(f"{copy.relative_to(ROOT)}: a copy of both {seen[copy]} and {source}")
    return out


def check_copies(fail: Failures, made: list[Copy], write: bool) -> None:
    rules: dict[str, list[list[str]] | str] = {}
    for kind, rel, original, copy, template in made:
        label = copy.relative_to(ROOT)
        try:
            data = original.read_bytes()
        except OSError as error:
            fail(f"shared/{kind}/{rel}: unreadable ({error})")
            continue
        if kind == "root" and template is not None and LIQUID.search(data.decode(errors="replace")):
            variants = rules.setdefault(template, exclusions(template))
            try:
                if isinstance(variants, str):
                    raise PatternError(variants)
                rendered = any(not excluded_by(rel, patterns) for patterns in variants)
            except PatternError as error:
                fail(f"{template}/cargo-generate.toml: {error} -- so whether it renders {rel} is unknown")
            else:
                if rendered:
                    fail(f"shared/root/{rel}: holds Liquid, which {template}/ renders -- the root's copy would "
                         "not be what a project gets (move it to shared/template/, or exclude it there)")
        if through_symlink(copy.parent):
            fail(f"{label}: inside a symlinked folder, which cargo-generate leaves out of a project")
            continue
        blocking = next((a for a in copy.parents if a.is_relative_to(ROOT) and a.exists() and not a.is_dir()), None)
        if blocking is not None:
            fail(f"{label}: {blocking.relative_to(ROOT)} is a file, where its folder goes")
            continue
        if copy.exists() and not copy.is_symlink() and not copy.is_file():
            fail(f"{label}: not a file, where shared/{kind}/{rel}'s copy goes")
            continue
        wanted = (copy.stat().st_mode if copy.is_file() and not copy.is_symlink() else 0o644) & 0o7777
        wanted = wanted | 0o111 if executable(original) else wanted & ~0o111
        if write and (copy.is_symlink() or not copy.is_file() or copy.read_bytes() != data
                      or executable(copy) != executable(original)):
            write_file(copy, data, wanted)
            print(f"wrote {label}")
        if copy.is_symlink() or not copy.is_file():
            fail(f"{label}: missing (a copy of shared/{kind}/{rel}; a symlink is none)")
            continue
        if copy.read_bytes() != data:
            fail(f"{label}: differs from shared/{kind}/{rel} -- change the original, then `just sync`")
        if executable(copy) != executable(original):
            fail(f"{label}: executable in one of it and shared/{kind}/{rel}, not both")


RECIPE_LINE = r"@?{name}(?:\s[^:]*)?:(?!=)"  # `:=`: an assignment


def recipe_names(lines: list[str]) -> list[str]:
    """The recipes a justfile defines: the lines at the margin that open one."""
    pattern = re.compile(RECIPE_LINE.format(name=r"([A-Za-z_][A-Za-z0-9_-]*)"))
    return [m.group(1) for line in lines if (m := pattern.match(line))]


def recipe_span(lines: list[str], name: str) -> tuple[int, int, int] | None:
    """(its first comment or attribute line, its line, past its body): the comment and attribute
    lines right above it, its line, its body to the next line at the margin, trailing blank lines
    left out."""
    pattern = re.compile(RECIPE_LINE.format(name=re.escape(name)))
    for i, line in enumerate(lines):
        if pattern.match(line):
            start = i
            while start > 0 and lines[start - 1].startswith(("#", "[")):
                start -= 1
            end = i + 1
            while end < len(lines) and (not lines[end] or lines[end][0].isspace()):
                end += 1
            while end > i + 1 and not lines[end - 1].strip():
                end -= 1
            return start, i, end
    return None


def check_recipes(fail: Failures, templates: list[str], write: bool) -> int:
    """The shared recipes in every justfile; the number of them."""
    try:
        shared = RECIPES.read_text(encoding="utf-8").split("\n")
    except (OSError, UnicodeDecodeError) as error:
        fail(f"shared/recipes.just: unreadable ({error})")
        return 0
    names = recipe_names(shared)
    if not names:
        fail("shared/recipes.just: no recipe in it")
    for justfile in [ROOT / "justfile", *(ROOT / t / "justfile" for t in templates)]:
        label = justfile.relative_to(ROOT)
        if through_symlink(justfile):
            fail(f"{label}: a symlink, or inside a symlinked folder, which cargo-generate leaves out of a project")
            continue
        try:
            raw = justfile.read_bytes()
            lines = raw.decode("utf-8").split("\n")
        except (OSError, UnicodeDecodeError) as error:
            fail(f"{label}: unreadable ({error})")
            continue
        if b"\r" in raw:
            fail(f"{label}: holds a carriage return (CRLF): its recipes cannot be compared line by line")
            continue
        changed = False
        for name in names:
            mine = recipe_span(shared, name)
            theirs = recipe_span(lines, name)
            assert mine is not None
            if theirs is None:
                fail(f"{label}: no recipe {name} (shared/recipes.just's) -- add it, then `just sync`")
                continue
            if lines[theirs[0] : theirs[2]] != shared[mine[0] : mine[2]]:
                if write:
                    lines[theirs[0] : theirs[2]] = shared[mine[0] : mine[2]]
                    changed = True
                    print(f"wrote {label}'s recipe {name}")
                else:
                    fail(f"{label}: recipe {name} differs from shared/recipes.just's -- change the original, "
                         "then `just sync`")
        if changed:
            write_file(justfile, "\n".join(lines).encode("utf-8"), justfile.stat().st_mode & 0o7777)
    return len(names)


def jsonc(path: pathlib.Path) -> dict:
    """A dprint.json: JSONC, its whole-line comments dropped."""
    data = json.loads(JSONC_COMMENT.sub("", path.read_text()))
    if not isinstance(data, dict):
        raise ValueError("not an object")
    return data


def toml_settings(config: dict) -> dict:
    """What of a dprint.json formats TOML: every key but the file selection, the plugins and the
    Markdown plugin's settings -- the `toml` plugin's and the global ones (lineWidth, useTabs...)."""
    return {k: v for k, v in config.items() if k not in {"$schema", "excludes", "includes", "plugins", "markdown"}}


def check_roots(fail: Failures, templates: list[str]) -> None:
    try:
        offered = tomllib.loads((ROOT / "cargo-generate.toml").read_text())["template"]["sub_templates"]
        if not isinstance(offered, list) or not all(isinstance(n, str) for n in offered):
            raise TypeError("not a list of names")
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as error:
        fail(f"cargo-generate.toml: no [template] sub_templates read ({error!r})")
        offered = []
    for name in sorted(set(templates) - set(offered)):
        fail(f"cargo-generate.toml: sub_templates leaves out {name}, a template root")
    for name in sorted(set(offered) - set(templates)):
        fail(f"cargo-generate.toml: sub_templates offers {name!r}, which is no template root")
    if len(offered) != len(set(offered)):
        fail("cargo-generate.toml: sub_templates names a template twice")
    try:
        root = jsonc(ROOT / "dprint.json")
        excludes, root_plugins = root.get("excludes", []), root["plugins"]
        root_toml = toml_settings(root)
        if not isinstance(excludes, list):
            raise ValueError("excludes is not a list")
    except (OSError, KeyError, ValueError) as error:
        fail(f"dprint.json: unreadable ({error!r})")
        excludes, root_plugins, root_toml = [], None, None
    for name in templates:
        if f"./{name}/" not in excludes:
            fail(f"dprint.json: excludes leaves out ./{name}/, a template root (its own dprint.json checks it)")
        try:
            config = jsonc(ROOT / name / "dprint.json")
            theirs = config["plugins"]
        except (OSError, KeyError, ValueError) as error:
            fail(f"{name}/dprint.json: no plugins read ({error!r})")
            continue
        if root_plugins is not None and theirs != root_plugins:
            fail(f"{name}/dprint.json: its plugins are not dprint.json's -- `just dprint-update` sets all")
        if root_toml is not None and toml_settings(config) != root_toml:
            fail(f"{name}/dprint.json: its TOML settings (`toml`, the global ones) are not dprint.json's "
                 "-- set them as there: the TOML they share (shared/) must pass each one's check")
    try:
        listed = dependabot_actions_directories(ROOT / ".github/dependabot.yml")
    except (OSError, ValueError) as error:
        fail(f".github/dependabot.yml: no github-actions directories read ({error!r})")
        listed = None
    if listed is not None:
        expected = workflow_directories(templates)
        for directory in sorted({d for d in listed if listed.count(d) > 1}):
            fail(f".github/dependabot.yml: the github-actions directories name {directory} twice")
        for directory in sorted(expected - set(listed)):
            fail(f".github/dependabot.yml: the github-actions directories leave out {directory} "
                 "(Dependabot reads only the directories named)")
        for directory in sorted(set(listed) - expected):
            fail(f".github/dependabot.yml: the github-actions directories name {directory}, no folder of "
                 "workflows here")


def check_update_list(fail: Failures, templates: list[str], made: list[Copy]) -> None:
    """dev/dprint.files, as dev/unlisted.sh reads it (the last pattern that matches deciding): what
    `just dprint-update` writes let through -- every dprint.json, and each copy of a Markdown or TOML
    [root] original, which the root formats and `just sync` copies -- and no template root's or
    shared/template/'s own Markdown and TOML, which hold Liquid."""
    allowed = ["dprint.json", *(f"{name}/dprint.json" for name in templates)]
    allowed += sorted(
        {str(path.relative_to(ROOT)) for kind, rel, original, copy, _ in made if kind == "root"
         and rel.endswith((".md", ".toml")) for path in (original, copy)}
    )
    refused = [f"{folder}/{path}" for folder in [*templates, "shared/template"]
               for path in ("README.md", "docs/a/b.md", "pyproject.toml")]
    try:
        unlisted = set(subprocess.run(  # noqa: S603 - this repository's own script
            [ROOT / "dev" / "unlisted.sh", ROOT / "dev" / "dprint.files"],
            input="".join(f"{path}\n" for path in allowed + refused), capture_output=True, text=True, check=True,
        ).stdout.splitlines())
    except (OSError, subprocess.CalledProcessError) as error:
        fail(f"dev/dprint.files: not read by dev/unlisted.sh ({error!r})")
        return
    for path in allowed:
        if path in unlisted:
            fail(f"dev/dprint.files: refuses {path}, which `just dprint-update` writes -- let it through")
    for path in refused:
        if path not in unlisted:
            fail(f"dev/dprint.files: lets {path} through -- its folder's `!<folder>/*`, after every pattern "
                 "it must override: a template root's and shared/template/'s Liquid is a generated project's")


def workflow_directories(templates: list[str]) -> set[str]:
    """What dependabot.yml's github-actions entry must name: `/` (Dependabot reads it as .github/workflows
    and a root action.yml), and the .github/workflows of shared/root, shared/template and each template
    root that holds a workflow (any other directory is read as the YAML files directly in it)."""
    found = {"/"}
    for folder in [*KINDS.values(), *(ROOT / name for name in templates)]:
        workflows = folder / ".github/workflows"
        if any(p.suffix in (".yml", ".yaml") and p.is_file() for p in workflows.glob("*")):
            found.add("/" + workflows.relative_to(ROOT).as_posix())
    return found


def dependabot_actions_directories(path: pathlib.Path) -> list[str]:
    """The `directories` list of a dependabot.yml's github-actions entry, as the file is written here
    (the standard library reads no YAML; a form this does not read fails, unread or read short):
    the entry, its `- package-ecosystem: github-actions` line (quoted or not) and the lines below
    indented past its dash; `directories:`, a key of it, at its keys' indentation; the list, the
    `- "<path>"` lines (quoted either way, or not) right after it, blank and comment lines passed over."""
    lines = path.read_text().splitlines()
    blank = re.compile(r" *(#.*)?")
    head = re.compile(r"""( *)- +(package-ecosystem: +)(["']?)([A-Za-z0-9_-]+)\3 *(#.*)?""")
    heads = [(i, m) for i, line in enumerate(lines) if (m := head.fullmatch(line)) and m[4] == "github-actions"]
    if len(heads) != 1:
        raise ValueError(f"{len(heads)} github-actions entries")
    first, match = heads[0]
    dash, keys = len(match[1]), match.start(2)
    end = next((j for j in range(first + 1, len(lines))
                if not blank.fullmatch(lines[j]) and len(lines[j]) - len(lines[j].lstrip(" ")) <= dash), len(lines))
    starts = [j for j in range(first + 1, end) if re.fullmatch(rf" {{{keys}}}directories: *(#.*)?", lines[j])]
    if len(starts) != 1:
        raise ValueError(f"{len(starts)} directories lists in the github-actions entry")
    item = re.compile(r"""( *)- +(["']?)(/[^"'\s#]*)\2 *(#.*)?""")
    listed = []
    for line in lines[starts[0] + 1 : end]:
        if blank.fullmatch(line):
            continue
        got = item.fullmatch(line)
        if not got or len(got[1]) < keys:
            break
        listed.append(got[3])
    return listed


def sync(write: bool) -> Failures:
    fail = Failures()
    templates = template_roots()
    made = copies(fail, templates)
    check_copies(fail, made, write)
    recipes = check_recipes(fail, templates, write)
    check_roots(fail, templates)
    check_update_list(fail, templates, made)
    print(f"{len(made)} copies, {recipes} recipes in {1 + len(templates)} justfiles, "
          f"{len(templates)} template roots: " + ("in sync" if not fail else f"{len(fail)} failure(s)"))
    return fail


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="check only: write nothing")
    args = parser.parse_args()
    failures = sync(write=not args.check)
    for message in failures:
        print(f"error: {message}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
