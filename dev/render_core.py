"""What every template's render-check shares: dev/<template>/render-check.py runs it with its own
answers and rules.

Renders a template root with Liquid, without cargo-generate, for every answer combination its
render-check gives, and checks what otherwise surfaces only after generation:

  * every prompt's name is none cargo-generate reserves, and its default is one of its choices
    and passes its own regex (cargo-generate matches with `is_match`: the anchors are the regex's
    own);
  * the generation answers, `just generate`'s and the smoke tests' (dev/<template>/answers.toml):
    each a prompt's, which its type, choices and regexes take -- cargo-generate takes any other
    name too, unasked and unchecked -- and every prompt with no default answered where it is asked;
  * every `ignore` entry is a literal path that exists: cargo-generate joins each onto its copy of
    the template and removes it, so a glob names nothing and the file ships silently;
  * every hook script exists (cargo-generate copies none, nor its config);
  * every templated file is UTF-8 (cargo-generate aborts on one that is not: a binary file must be
    excluded), and every variable it names is declared or built in -- cargo-generate renders an
    unknown one as an empty string, and a file it cannot render as it stands, both silently;
  * no excluded file (copied verbatim, a binary one too) holds one of the template's
    placeholders, and one of a kind parsed below is UTF-8 -- each exclude list read as
    cargo-generate reads it (sync.py's), the conditionals' joining the template's where they hold;
  * in every case, every templated file renders and leaves no template syntax behind, and every
    file parses as its kind -- the ones the case drops too, stricter than cargo-generate: TOML
    (Cargo.lock too), YAML, JSON (flake.lock too; dprint.json's whole-line comments allowed) and,
    with `nix-instantiate` on PATH, Nix.

Then the template's own checks, each on its own: one failing, or unable to run because a file
before it did not render, is reported and the rest still run; the exit status is 1.

An approximation: cargo-generate uses the Rust `liquid` crate, this python-liquid. They agree on
the subset the templates use (assign, if/elsif/else, unless, for, split, strip, replace, remove,
date, downcase), which is why the templates stay inside it. One known divergence: after a `-%}`
trim tag, python-liquid also drops a file's final newline where liquid-rust keeps it -- so
whitespace is the smoke tests' to check, not this.
"""

from __future__ import annotations

import contextlib
import fnmatch
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

try:
    from liquid import Environment
except ImportError:  # pragma: no cover - dependency hint
    sys.exit("python-liquid is required:  pip install -r dev/requirements.txt")

try:
    import yaml
except ImportError:  # pragma: no cover - dependency hint
    sys.exit("PyYAML is required:  pip install -r dev/requirements.txt")

# cargo-generate's reading of an exclude list, and Liquid's tags: sync.py's, which holds the shared
# files to them too
from sync import JSONC_COMMENT, PatternError, excluded_by, exclusions  # dev/, its importer's path
from sync import LIQUID as TAG

ROOT = pathlib.Path(__file__).resolve().parents[1]

# `{{project-name}}` is valid for the Rust liquid crate but the dash parses as subtraction in
# python-liquid, so the identifier is rewritten inside tags (TAG) only -- never in prose naming it.
# cargo-generate's own variables (crate_type declared, but no template reads it)
BUILTINS = frozenset(
    {
        "project-name", "crate_name", "crate_type", "authors", "username", "os-arch",
        "within_cargo_project", "is_init",
    }
)
# the names cargo-generate refuses a placeholder (project_variables.rs's RESERVED_NAMES, 0.25.0)
RESERVED = BUILTINS - {"username"}
# the values every case gives those a template's sample answers do not
SAMPLE_BUILTINS: dict[str, object] = {
    "authors": "Jane Doe <jane@example.com>",
    "username": "jane",
    "os-arch": "linux-x86_64",
    "within_cargo_project": False,
    "is_init": False,
}
# container_image, a layout with a binary's prompt: unasked (None), or answered; a lib may still be
# given it (`-d`), which cargo-generate passes through unasked
IMAGE_LABELS: dict[object, str] = {None: "", True: "/image", False: "/no-image"}

# Liquid's operators and literals, and `forloop`: no variables anywhere in a tag. A tag's name is
# its first word, a filter's the word after a `|`; a parameter word is one only where its tag
# takes it (`for x in list limit: 2 reversed`, `render "x" with y as z`). A name another
# position holds -- `{{ echo }}`, `{{ size }}` -- is a variable, as Liquid reads it.
WORDS = frozenset("and or contains true false nil null empty blank forloop".split())
PARAMETERS = {
    "for": frozenset({"in", "limit", "offset", "reversed"}),
    "tablerow": frozenset({"in", "limit", "offset", "cols"}),
    "include": frozenset({"with", "for", "as"}),
    "render": frozenset({"with", "for", "as"}),
}
# a name; not an attribute after a single `.` (`forloop.last`), but a range's end (`1..stop`)
NAME = re.compile(r"(?<!\w)(?<!(?<!\.)\.)[A-Za-z_][A-Za-z0-9_-]*")
LITERAL = re.compile(r"\"[^\"]*\"|'[^']*'")
# a `{% %}` tag's name: its first word, to the first character no name holds (`if(x)`)
TAG_NAME = re.compile(r"#?[A-Za-z_]*")
FILTER_NAME = re.compile(r"^\s*[A-Za-z_][\w-]*")


def image_answer(image: bool | None) -> dict[str, object]:
    """A case's container_image answer: none for one unasked."""
    return {} if image is None else {"container_image": image}


def image_wanted(vars_: Mapping[str, object]) -> bool:
    """Whether the case builds the image: answered yes, by a layout with a binary."""
    return vars_.get("container_image") is True and vars_["project_kind"] != "lib"


def case_vars(base_vars: Mapping[str, object], answers: Mapping[str, object]) -> dict[str, Any]:
    """What a case renders with: the sample built-ins, the template's sample answers, the case's,
    and `project-name` as `project_name` too (python-liquid reads no dash: `normalise`)."""
    vars_: dict[str, Any] = {**SAMPLE_BUILTINS, **base_vars, **answers}
    vars_["project_name"] = vars_["project-name"]
    return vars_


def references(tag: str) -> list[str]:
    """The variables a tag (`{{ ... }}` or `{% ... %}`) reads: its names but its tag's, each
    filter's, the operators and literals, and string literals; a filter's arguments are read."""
    body = LITERAL.sub('""', tag.strip("{}%- "))
    skip = WORDS
    if tag.startswith("{%"):
        body = body.strip()
        head = match.group(0) if (match := TAG_NAME.match(body)) else ""
        body = body[len(head) :]
        if head.startswith("#") or head in ("comment", "raw"):  # an inline comment, a raw block's tag
            return []
        if head == "liquid":  # a tag on each line
            return [name for line in body.splitlines() if line.strip() for name in references(f"{{% {line} %}}")]
        skip = WORDS | PARAMETERS.get(head, frozenset())
    names = []
    for i, segment in enumerate(body.split("|")):
        read = FILTER_NAME.sub("", segment, count=1) if i else segment
        names += [m.group(0) for m in NAME.finditer(read) if m.group(0) not in skip]
    return names


def normalise(text: str) -> str:
    return TAG.sub(lambda m: m.group(0).replace("project-name", "project_name"), text)


def matches_any(rel: str, globs: Iterable[str]) -> bool:
    """Whether `rel` is one of the `ignore` entries, or inside one (an exclude list is
    `Check.excluded_from`'s)."""
    return any(fnmatch.fnmatch(rel, g) or rel == g or rel.startswith(g.rstrip("/") + "/") for g in globs)


def holds(expr: str, vars_: Mapping[str, object]) -> bool:
    """A conditional's Rhai expression -- comparisons, `&&`, `||`, `!` -- over the answers."""
    python = expr.replace("&&", " and ").replace("||", " or ")
    python = re.sub(r"!(?!=)", " not ", python)
    # a dashed name (`project-name`) is no Rhai identifier: no condition reads it
    names = {k: v for k, v in vars_.items() if "-" not in k}
    return bool(eval(python, {"__builtins__": {}}, names))  # noqa: S307 - our own config's


@dataclass
class Case:
    """One answer combination, rendered: the files it keeps, the text of each (a binary one aside)."""

    label: str
    vars: dict[str, Any]  # what Liquid renders with: case_vars
    ignored: list[str]  # the conditionals' `ignore` entries that hold
    excluded: list[str]  # its exclude list: the template's, then the conditionals' that hold
    kept: set[str] = field(default_factory=set)
    outputs: dict[str, str] = field(default_factory=dict)


class Check:
    """One template's run: its config, its files, the failures so far."""

    def __init__(self, name: str) -> None:
        self.template = ROOT / name
        self.cfg = tomllib.loads((self.template / "cargo-generate.toml").read_text())
        self.excluded: list[str] = self.cfg["template"].get("exclude", [])
        # every exclude list a project can be generated with, each line read as cargo-generate
        # reads it (a refused one raises PatternError)
        variants = exclusions(name)
        if isinstance(variants, str):
            raise PatternError(f"its exclude lists: {variants}")
        for patterns in variants:
            try:
                excluded_by("", patterns)
            except PatternError as error:
                raise PatternError(f"an exclude line cargo-generate refuses: {error}") from error
        self.variants = [tuple(patterns) for patterns in variants]
        self.verdicts: dict[tuple[str, tuple[str, ...]], bool] = {}
        self.conditionals: dict[str, dict[str, Any]] = self.cfg.get("conditional", {})
        # every prompt with the condition it is asked under (None: always): a name may be asked
        # under several, each with its own default, choices and regex
        self.prompts: list[tuple[str | None, str, dict[str, Any]]] = [
            (None, n, spec) for n, spec in self.cfg["placeholders"].items()
        ] + [
            (expr, n, spec)
            for expr, section in self.conditionals.items()
            for n, spec in section.get("placeholders", {}).items()
        ]
        # each hook list's scripts (a lone string is one script)
        hooks = self.cfg.get("hooks", {}).values()
        self.hooks = sorted({n for names in hooks for n in ([names] if isinstance(names, str) else names)})
        skipped = {"cargo-generate.toml", *self.hooks}
        self.files = sorted(
            str(p.relative_to(self.template))
            for p in self.template.rglob("*")
            if p.is_file() and str(p.relative_to(self.template)) not in skipped
        )
        # each file's text; one not UTF-8 read with its bad bytes replaced, and named
        self.texts: dict[str, str] = {}
        self.not_utf8: set[str] = set()
        for rel in self.files:
            data = (self.template / rel).read_bytes()
            try:
                self.texts[rel] = data.decode("utf-8")
            except UnicodeDecodeError:
                self.texts[rel] = data.decode("utf-8", errors="replace")
                self.not_utf8.add(rel)
        self.env = Environment()
        self.nix = shutil.which("nix-instantiate")
        self.nix_errors: dict[str, str] = {}  # each Nix text parsed: its error, "" if none
        self.failures: list[str] = []

    def fail(self, msg: str) -> None:
        self.failures.append(msg)
        print(f"  FAIL {msg}")

    def names(self) -> set[str]:
        return {n for _, n, _ in self.prompts}

    def regexes(self, name: str, condition: str | None = None) -> list[str]:
        """Each regex the prompt `name` has -- under `condition` alone, if given."""
        return [
            spec["regex"]
            for expr, n, spec in self.prompts
            if n == name and "regex" in spec and (condition is None or expr == condition)
        ]

    def excluded_from(self, rel: str, patterns: Sequence[str]) -> bool:
        """Whether `patterns`, an exclude list, excludes `rel`, as cargo-generate decides."""
        key = (rel, tuple(patterns))
        if key not in self.verdicts:
            self.verdicts[key] = excluded_by(rel, list(key[1]))
        return self.verdicts[key]

    def templated(self, rel: str) -> bool:
        """Rendered in some project: by one exclude list at least."""
        return any(not self.excluded_from(rel, patterns) for patterns in self.variants)

    def verbatim(self, rel: str) -> bool:
        """Copied as it stands in some project: excluded by one exclude list at least."""
        return any(self.excluded_from(rel, patterns) for patterns in self.variants)

    def render(self, rel: str, vars_: Mapping[str, object]) -> str:
        """A templated file rendered with `vars_`, a case_vars."""
        return self.env.from_string(normalise(self.texts[rel])).render(**vars_)

    def licence_copies(self, members: Iterable[str]) -> None:
        """Each member folder holds the root's licence texts, byte for byte (a workspace member's
        package holds its own folder alone)."""
        for member in members:
            for name in ("LICENSE-MIT", "LICENSE-APACHE"):
                copy = self.template / member / name
                if not copy.is_file():
                    self.fail(f"{member}/{name} is missing")
                elif copy.read_bytes() != (self.template / name).read_bytes():
                    self.fail(f"{member}/{name} differs from the root's {name}")

    def guarded(self, label: str, rule: Callable[..., object], *args: object) -> None:
        """Run a rule; one that cannot run (a file before it did not render) is a failure too."""
        try:
            rule(*args)
        except Exception as exc:  # noqa: BLE001 - report and continue
            self.fail(f"{label}: could not check: {type(exc).__name__}: {exc}")


Rule = Callable[[Check], object]
CaseRule = Callable[[Check, Case], object]
FinalRule = Callable[[Check, list[Case]], object]


def kind(rel: str) -> str | None:
    """What a file parses as: toml, yaml, json, jsonc (dprint.json: whole-line comments), nix."""
    path = pathlib.PurePath(rel)
    if path.suffix == ".toml" or path.name == "Cargo.lock":
        return "toml"
    if path.suffix in (".yml", ".yaml"):
        return "yaml"
    if path.name == "dprint.json":
        return "jsonc"
    if path.suffix == ".json" or path.name == "flake.lock":
        return "json"
    if path.suffix == ".nix":
        return "nix"
    return None


def parse(check: Check, case: Case, rel: str, out: str) -> None:
    """A file, as the case renders it, parsed as its kind."""
    what = kind(rel)
    try:
        if what == "toml":
            tomllib.loads(out)
        elif what == "yaml":
            yaml.safe_load(out)
        elif what == "json":
            json.loads(out)
        elif what == "jsonc":
            json.loads(JSONC_COMMENT.sub("", out))
        elif what == "nix" and check.nix:
            # many cases render a file alike: each text parsed once
            if out not in check.nix_errors:
                parsed = subprocess.run(  # noqa: S603 - nix-instantiate, from PATH
                    [check.nix, "--parse", "-"], input=out, capture_output=True, text=True, check=False
                )
                check.nix_errors[out] = parsed.stderr.strip() if parsed.returncode != 0 else ""
            if check.nix_errors[out]:
                raise ValueError(check.nix_errors[out])  # noqa: TRY301
    except Exception as exc:  # noqa: BLE001 - report and continue
        # named as the file is: by its suffix, a lock file by its kind
        suffix = pathlib.PurePath(rel).suffix.lstrip(".")
        named = what if suffix == "lock" else suffix
        check.fail(f"{case.label}: {rel}: invalid {named} after render: {exc}")


def refusals(spec: Mapping[str, Any], value: str) -> list[str]:
    """Why a prompt refuses `value`: not one of its choices, or its regex not matching it (as
    cargo-generate's `is_match`, the anchors the regex's own); a regex that does not compile is the
    prompts' check's failure."""
    found = []
    if "choices" in spec and value not in spec["choices"]:
        found.append("is not one of its choices")
    with contextlib.suppress(re.error):
        if "regex" in spec and not re.search(spec["regex"], value):
            found.append("rejected by its regex")
    return found


def as_bool(value: object) -> bool | None:
    """A bool prompt's answer as cargo-generate reads it: a bool, or `true` or `false` in any case;
    None for any other."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true"
    return None


def unresolved(check: Check, answers: Mapping[str, object], kind: str) -> list[str]:
    """What fails a generation of `kind` under `--silent` -- a conditional prompt it asks with no
    default, unanswered -- or leaves it to chance: a name sections holding together declare apart.
    The conditional prompts resolved as cargo-generate does: every prompt answered or defaulted once
    its condition holds (the unconditional ones first), the first value a name gets kept, until
    none more holds; a condition naming a variable not yet set, or failing, holds not (its Rhai
    error). The built-ins are `just generate`'s (`--name demo`), the rest SAMPLE_BUILTINS; a bool
    answer cargo-generate refuses (generation_answers refuses it) sets nothing."""
    bools = {n for _, n, spec in check.prompts if spec.get("type") == "bool"}
    given = {n: as_bool(v) if n in bools else v for n, v in answers.items()}
    given = {n: v for n, v in given.items() if v is not None}
    unset = object()

    def value(n: str, spec: Mapping[str, object]) -> object:
        return given[n] if n in given else spec.get("default", unset)

    def asks(expr: str, known: Mapping[str, object]) -> bool:
        try:
            return holds(expr, known)
        except Exception:  # noqa: BLE001 - cargo-generate's: a failing condition holds not
            return False

    known: dict[str, object] = {
        **SAMPLE_BUILTINS, "project-name": "demo", "crate_name": "demo", "crate_type": "bin",
    }
    for expr, n, spec in check.prompts:
        if expr is None and (v := value(n, spec)) is not unset:
            known.setdefault(n, v)
    known["project_kind"] = kind
    pending = [(expr, n, spec) for expr, n, spec in check.prompts if expr is not None]
    found: dict[str, str] = {}
    while held := [item for item in pending if asks(item[0], known)]:
        # one name unanswered that sections holding together declare apart (a default, or none):
        # cargo-generate keeps one of them, in its HashMap's order, so what follows is chance
        fresh = [(expr, n, spec) for expr, n, spec in held if n not in known and n not in given]
        for name in dict.fromkeys(n for _, n, _ in fresh):
            same = [(expr, spec) for expr, n, spec in fresh if n == name]
            if len({repr(spec.get("default", unset)) for _, spec in same}) > 1:
                found.setdefault(name, f"{name} for {kind} ({' or '.join(expr for expr, _ in same)}): "
                                 "declared apart by sections holding together, one kept at random")
        for item in held:
            pending.remove(item)
            expr, n, spec = item
            # cargo-generate asks no name it already holds
            if n in known:
                continue
            if (v := value(n, spec)) is unset:
                found.setdefault(n, f"{n} unanswered for {kind} ({expr}), where it has no default: "
                                 "`--silent` would fail")
            else:
                known[n] = v
    return sorted(found.values())


def generation_answers(check: Check, path: pathlib.Path) -> int:
    """The generation answers, `just generate`'s and the smoke tests' (cargo-generate's
    `--values-file`), held to the template's prompts -- cargo-generate takes a name no prompt asks
    for too, unchecked, into its Liquid, over a built-in of that name. A `text`, `editor` or
    `array` prompt's value (none here) is not read. Returns how many answers it read."""
    rel = path.relative_to(ROOT)
    try:
        values = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        check.fail(f"{rel}: unreadable ({type(exc).__name__}: {exc})")
        return 0
    if set(values) != {"values"} or not isinstance(values["values"], dict):
        check.fail(f"{rel}: not a [values] table alone: cargo-generate reads it, and drops the rest silently")
        return 0
    answers: dict[str, object] = values["values"]
    for key, value in answers.items():
        asked = [(expr or "always", spec) for expr, n, spec in check.prompts if n == key]
        if key == "project_kind":
            check.fail(f"{rel}: project_kind is each generation's kind (`-d`), not an answer here")
            continue
        if not asked:
            check.fail(f"{rel}: {key!r} is no prompt of the template: nothing would ask or check it")
        for where, spec in asked:
            typed = spec.get("type", "string")  # cargo-generate's default
            if typed == "bool":
                # not `in (True, False)`: 1 == True, and cargo-generate refuses a number
                if as_bool(value) is None:
                    check.fail(f"{rel}: {key} = {value!r} ({where}) is not true or false")
            elif typed != "string":
                continue
            # a string, as a `-d` gives: cargo-generate writes a number as it reads it (1.90 as 1.9)
            elif not isinstance(value, str):
                check.fail(f"{rel}: {key} = {value!r} ({where}) is no string")
            # one line: a `-d` cannot give more, a regex may let one through into the TOML or YAML
            # it is written in, and Python's `$` matches before a last newline where Rust's does not
            elif "\n" in value:
                check.fail(f"{rel}: {key} ({where}) holds a newline")
            else:
                for reason in refusals(spec, value):
                    check.fail(f"{rel}: {key} = {value!r} ({where}) {reason}")
    for expr, n, spec in check.prompts:
        # a built-in is no question: cargo-generate holds it before any prompt
        if expr is None and "default" not in spec and n not in answers and n not in BUILTINS:
            check.fail(f"{rel}: {n} unanswered, and it has no default: `--silent` would fail")
    kinds = [kind for expr, n, spec in check.prompts if expr is None and n == "project_kind"
             for kind in spec.get("choices", [])]
    for kind in kinds:
        for failure in unresolved(check, answers, kind):
            check.fail(f"{rel}: {failure}")
    return len(answers)


def run(
    name: str,
    *,
    base_vars: Mapping[str, object],
    cases: Sequence[Mapping[str, object]],
    label: Callable[[Mapping[str, object]], str],
    rules: Iterable[Rule] = (),
    case_rules: Iterable[CaseRule] = (),
    final_rules: Iterable[FinalRule] = (),
) -> int:
    """The shared checks, then `rules` (each printing its own heading), each case rendered and
    `case_rules` run on it, then `final_rules` on every case. The exit status: 1 on any failure."""
    try:
        check = Check(name)
    except (OSError, KeyError, tomllib.TOMLDecodeError, PatternError) as exc:
        # nothing to check without the config and the files: the template, as far as read
        print(f"  FAIL {name}: its cargo-generate.toml, its exclude lists or a file unreadable "
              f"({type(exc).__name__}: {exc})\n\n1 FAILURE(S)")
        return 1
    fail = check.fail
    rules, case_rules, final_rules = tuple(rules), tuple(case_rules), tuple(final_rules)

    print("== prompts: names, defaults, choices, regexes")
    for expr, n, spec in check.prompts:
        where = f"{n} ({expr or 'always'})"
        if n in RESERVED:
            fail(f"{where}: a name cargo-generate reserves: it refuses the template wherever it is asked")
        if "regex" in spec:
            try:
                re.compile(spec["regex"])
            except re.error as exc:
                fail(f"{where}: its regex does not compile: {exc}")
                continue
        # the default of its prompt's type, which cargo-generate refuses the template without
        typed, default = spec.get("type", "string"), spec.get("default")
        if typed == "bool" and "default" in spec and not isinstance(default, bool):
            fail(f"{where}: default {default!r} is no bool")
        elif typed in ("string", "text", "editor") and "default" in spec and not isinstance(default, str):
            fail(f"{where}: default {default!r} is no string")
        elif typed != "bool" and isinstance(default, str):
            for reason in refusals(spec, default):
                fail(f"{where}: default {default!r} {reason}")
    print(f"  checked {len(check.prompts)} prompts")

    answers_file = ROOT / "dev" / name / "answers.toml"
    print(f"== generation answers ({answers_file.relative_to(ROOT)})")
    print(f"  checked {generation_answers(check, answers_file)} answers")

    print("== conditional ignore paths, hooks")
    for expr, section in check.conditionals.items():
        for entry in section.get("ignore", []):
            if any(ch in entry for ch in "*?["):
                fail(f"{expr}: ignore entry {entry!r} looks like a glob; ignore takes literal paths")
            elif not (check.template / entry).exists():
                fail(f"{expr}: ignore entry {entry!r} does not exist in the template")
    for hook in check.hooks:
        if not (check.template / hook).is_file():
            fail(f"hook {hook} does not exist")
    print(f"  checked {sum(len(s.get('ignore', [])) for s in check.conditionals.values())} paths, "
          f"{len(check.hooks)} hooks")

    print("== variable references, binary files")
    known = BUILTINS | check.names()
    refs = 0
    for rel in check.files:
        text = check.texts[rel]
        if rel in check.not_utf8:
            if check.templated(rel):
                fail(f"{rel} is not UTF-8 but not excluded: cargo-generate would abort on it")
            elif what := kind(rel):
                fail(f"{rel} is not UTF-8, which a {what} file must be")
            continue
        if not check.templated(rel):
            continue
        local = set(re.findall(r"assign\s+([A-Za-z_][A-Za-z0-9_]*)\s*=", text))
        local |= set(re.findall(r"for\s+([A-Za-z_][A-Za-z0-9_]*)\s+in", text))
        local |= set(re.findall(r"capture\s+([A-Za-z_][A-Za-z0-9_]*)", text))
        for match in TAG.finditer(text):
            for token in references(match.group(0)):
                refs += 1
                if token not in known and token not in local:
                    fail(f"{rel}: unknown variable {token!r} -- it would render as an empty string")
    print(f"  checked {refs} identifier references")

    print("== exclude list integrity")
    ours = check.names() | {"project-name", "crate_name", "authors"}
    verbatim = [rel for rel in check.files if check.verbatim(rel)]
    for rel in verbatim:
        text = check.texts[rel]  # a binary file's too, its bad bytes replaced
        for var in sorted(ours):
            if re.search(r"\{\{\s*" + re.escape(var) + r"\s*\}\}", text):
                fail(f"{rel} is on the exclude list but contains {{{{{var}}}}}")
    print(f"  checked {len(verbatim)} excluded files")

    for rule in rules:
        check.guarded(rule.__name__, rule, check)

    rendered_cases: list[Case] = []
    for answers in cases:
        vars_ = case_vars(base_vars, answers)
        case = Case(label(answers), vars_, [], list(check.excluded))
        print(f"== render {case.label}")
        # case_vars' `project_name` is python-liquid's alone: no cargo-generate condition sees it
        seen = {k: v for k, v in vars_.items() if k != "project_name"}
        for expr, section in check.conditionals.items():
            try:
                if holds(expr, seen):
                    case.ignored.extend(section.get("ignore", []))
                    case.excluded.extend(section.get("exclude", []))
            except Exception as exc:  # noqa: BLE001 - report and continue
                fail(f"harness cannot evaluate conditional {expr!r}: {exc}")
        rendered = 0
        for rel in check.files:
            kept = not matches_any(rel, case.ignored)
            if kept:
                case.kept.add(rel)
            if rel in check.not_utf8:  # binary: excluded, or refused above
                continue
            # the ones this case drops too (the module's docstring)
            if not check.excluded_from(rel, case.excluded):
                try:
                    out = check.render(rel, vars_)
                except Exception as exc:  # noqa: BLE001 - report and continue
                    fail(f"{case.label}: {rel}: liquid error: {exc}")
                    continue
                if leftovers := TAG.findall(out):
                    fail(f"{case.label}: {rel}: unexpanded template syntax: {leftovers[:3]}")
                rendered += 1
            else:
                out = check.texts[rel]
            if kept:
                case.outputs[rel] = out
            parse(check, case, rel, out)
        for case_rule in case_rules:
            check.guarded(f"{case.label}: {case_rule.__name__}", case_rule, check, case)
        print(f"  rendered {rendered} files, {len(case.kept)} kept, checked")
        rendered_cases.append(case)

    for final in final_rules:
        check.guarded(final.__name__, final, check, rendered_cases)

    print()
    if check.failures:
        print(f"{len(check.failures)} FAILURE(S)")
        return 1
    print("all checks passed")
    return 0

