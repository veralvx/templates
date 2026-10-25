#!/usr/bin/env python3
"""typst's render-check: dev/render_core.py's checks, every answer combination, then typst's own:

  * the regexes accept Universe's categories and disciplines, and refuse what Universe would --
    and a `compiler` below 0.12, which the checks are not verified on;
  * when `nix` is on PATH, the `compiler` regex takes the flake's Typst (nixpkgs', at flake.lock)
    and nothing newer: a floor CI can test;
  * the `.gitattributes` export-ignore paths exist, the package's files kept;
  * the licence texts agree: LICENSE's branch with the file each also is;
  * each typst.toml describes its kind and licence, and each case keeps exactly the licence files
    its README and its `license` name.

Usage:  python3 dev/typst/render-check.py   (python-liquid and PyYAML; nix-instantiate, nix if on PATH)
Exit:   0 = all good, 1 = at least one check failed.
"""

from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Mapping

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from lock_core import NIX_FLAGS, get_flake  # noqa: E402 - dev/, put on the path above
from render_core import Case, Check, case_vars, run  # noqa: E402 - dev/, put on the path above

# typst/packages' lists (docs/CATEGORIES.md, docs/DISCIPLINES.md; bundler/src/*.rs)
CATEGORIES = (
    "components visualization model layout text languages scripting integration utility fun "
    "book report paper thesis poster flyer presentation cv office"
).split()
DISCIPLINES = (
    "accounting agriculture anthropology archaeology architecture biology business chemistry "
    "communication computer-science design drawing economics education engineering environment "
    "fashion film finance geography geology history journalism law linguistics literature "
    "mathematics medicine music painting philosophy photography physics politics psychology "
    "sociology theater theology transportation"
).split()
# what the package is, which .gitattributes must never export-ignore
PACKAGE = ("typst.toml", "src", "template", "README.md", "LICENSE", "CHANGELOG.md")

# the template's names, one sample answer per prompt (render_core's SAMPLE_BUILTINS the rest of
# cargo-generate's own); `CASES` varies them
BASE_VARS = {
    "project-name": "sample-package",
    "crate_name": "sample_package",
    "author_name": "Jane Doe",
    "author_email": "jane@example.com",
    "github_username": "jane",
    "compiler": "0.14.0",
}
LICENCES = ("MIT OR Apache-2.0", "MIT", "Apache-2.0", "MIT-0")
FULL = {
    "keywords": "greeting, Institute of Something",
    "disciplines": "computer-science, mathematics",
}
EMPTY = {"author_email": "", "keywords": "", "disciplines": ""}
CASES = [
    {
        "project_kind": kind,
        "license": lic,
        "description": "Does a thing well enough to say so.",
        "categories": cats,
        **extra,
    }
    for kind, cat_choices in (
        ("package", ("", "utility, scripting")),
        ("template", ("report", "paper, thesis, cv")),
    )
    for cats in cat_choices
    for lic in LICENCES
    for extra in (FULL, EMPTY)
]


def label(case: Mapping[str, object]) -> str:
    return f"{case['project_kind']}/{case['license']}/[{case['categories']}]" + (
        "/empty" if case["keywords"] == "" else ""
    )


def universe_regexes(check: Check) -> None:
    """The regexes accept and refuse what Universe does."""
    print("== Universe's regexes")
    fail = check.fail
    for regex in check.regexes("categories"):
        for category in CATEGORIES:
            if not re.search(regex, category):
                fail(f"categories regex refuses Universe's {category!r}")
        if not re.search(regex, "book, report, paper"):
            fail("categories regex refuses three of Universe's categories listed together")
        for bad in ("slides", "report, paper, thesis, cv", "Report"):
            if re.search(regex, bad):
                fail(f"categories regex accepts {bad!r}")
    for regex in check.regexes("categories", 'project_kind == "template"'):
        if re.search(regex, ""):
            fail("a template package's categories regex accepts none (Universe requires one)")
    for regex in check.regexes("disciplines"):
        for discipline in DISCIPLINES:
            if not re.search(regex, discipline):
                fail(f"disciplines regex refuses Universe's {discipline!r}")
        if not re.search(regex, ", ".join(DISCIPLINES)):
            fail("disciplines regex refuses Universe's disciplines listed together")
        if re.search(regex, "astrology"):
            fail("disciplines regex accepts 'astrology'")
    for regex in check.regexes("compiler"):
        if re.search(regex, "0.11.0"):
            fail("compiler regex accepts 0.11.0, below what the checks are verified on")
    for regex in check.regexes("github_username"):
        for bad in ("a--b", "-a", "a-", "a" * 40):
            if re.search(regex, bad):
                fail(f"github_username regex accepts {bad!r}, which Universe's `<@handle>` refuses")
    for regex in check.regexes("author_name"):
        if re.search(regex, "Jane <Doe>"):
            fail("author_name regex accepts angle brackets, which break typst.toml's `<@handle>`")


def export_ignore(check: Check) -> None:
    """.gitattributes' export-ignore paths exist (a stale one is dead weight), none the package."""
    print("== export-ignore paths")
    for line in check.texts[".gitattributes"].splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        path, *attributes = line.split()
        if attributes != ["export-ignore"] or not path.startswith("/"):
            check.fail(f".gitattributes: {line!r} is not `/<path> export-ignore`")
            continue
        if not (check.template / path.lstrip("/")).exists():
            check.fail(f".gitattributes: {path} does not exist in the template")
        if path.lstrip("/") in PACKAGE:
            check.fail(f".gitattributes: {path} is the package's, which typst/packages must get")


def licence_copies(check: Check) -> None:
    """LICENSE's branch for a licence is the file it also is (the dual licence's, the MIT-0)."""
    print("== licence copies")
    for licence, copy in (("MIT", "LICENSE-MIT"), ("Apache-2.0", "LICENSE-APACHE"), ("MIT-0", "LICENSE-MIT-0")):
        vars_ = case_vars(BASE_VARS, {**CASES[0], "license": licence})
        if check.render("LICENSE", vars_) != check.render(copy, vars_):
            check.fail(f"LICENSE's {licence} text differs from {copy}")


def compiler_cap(check: Check) -> None:
    """The `compiler` regex: up to the flake's Typst -- nixpkgs', at flake.lock, CI's -- and no
    newer, which CI could not test as a floor."""
    print("== the compiler floor and the flake's Typst")
    nix = shutil.which("nix")
    if nix is None:
        print("  SKIP: no nix on PATH (CI's checks.yml has it)")
        return
    # the flake's own nixpkgs input, as flake.lock locks it (no registry read)
    flake = f"{get_flake(check.template)}.inputs.nixpkgs"
    expr = f"{flake}.legacyPackages.${{builtins.currentSystem}}.typst.version"
    done = subprocess.run(  # noqa: S603 - nix, on the template's own flake
        [nix, *NIX_FLAGS, "eval", "--raw", "--impure", "--expr", expr],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0 or not re.fullmatch(r"\d+\.\d+\.\d+", done.stdout):
        tail = "\n    ".join(done.stderr.strip().splitlines()[-6:])
        check.fail(f"the flake's Typst, read from flake.lock's nixpkgs: {done.stdout!r}\n    {tail}")
        return
    typst = done.stdout
    major, minor, patch = map(int, typst.split("."))
    # every release past it, as far as a regex reaches in practice: its minor's later patches, the
    # next hundred minors', and the next two majors' -- ascending, so the first accepted is named
    later = [f"{major}.{m}.{p}" for m in range(minor, minor + 100) for p in range(50) if (m, p) > (minor, patch)]
    majors = [f"{x}.{m}.{p}" for x in (major + 1, major + 2) for m in range(10) for p in range(10)]
    newer = later + majors
    for regex in check.regexes("compiler"):
        if not re.search(regex, typst):
            check.fail(f"compiler regex refuses the flake's Typst, {typst}")
        if accepted := next((v for v in newer if re.search(regex, v)), None):
            check.fail(f"compiler regex accepts {accepted}, above the flake's Typst ({typst}): CI could not test it")
    print(f"  the flake's Typst: {typst}")


def manifest(check: Check, case: Case) -> None:
    """typst.toml describes the case as Universe reads it."""
    fail, kind, licence = check.fail, case.vars["project_kind"], case.vars["license"]
    parsed = tomllib.loads(case.outputs["typst.toml"])
    package = parsed["package"]
    expected = {
        ("template", "MIT OR Apache-2.0"): "(MIT OR Apache-2.0) AND MIT-0",
        ("template", "MIT"): "MIT AND MIT-0",
        ("template", "Apache-2.0"): "Apache-2.0 AND MIT-0",
    }.get((kind, licence), licence)
    if package["license"] != expected:
        fail(f"{case.label}: license is {package['license']!r}, expected {expected!r}")
    if package["authors"] != ["Jane Doe <@jane>"]:
        fail(f"{case.label}: authors is {package['authors']!r}")
    if ("template" in parsed) != (kind == "template"):
        fail(f"{case.label}: [template] present={('template' in parsed)} for {kind}")
    if kind == "template" and not package.get("categories"):
        fail(f"{case.label}: a template package needs a category")
    for key in ("keywords", "categories", "disciplines"):
        want = [item.strip() for item in case.vars[key].split(",") if item.strip()]
        if package.get(key, []) != want:
            fail(f"{case.label}: {key} is {package.get(key)!r}, expected {want!r}")
    if len(package.get("categories", [])) > 3:
        fail(f"{case.label}: more than three categories")
    entry = parsed.get("template", {}).get("path")
    if entry and f"{entry}/main.typ" not in case.outputs:
        fail(f"{case.label}: [template] path {entry} has no main.typ")


def entrypoint(check: Check, case: Case) -> None:
    """src/lib.typ imports the kind's module, which the case keeps."""
    kind = case.vars["project_kind"]
    module = "report" if kind == "template" else "greet"
    lib = case.outputs["src/lib.typ"]
    if f'#import "{module}.typ": {module}' not in lib or f"src/{module}.typ" not in case.outputs:
        check.fail(f"{case.label}: src/lib.typ does not import the {kind}'s module, or it is missing")


def licence_files(check: Check, case: Case) -> None:
    """LICENSE always; the dual licence's two texts; a template's MIT-0 text unless MIT-0 is the
    whole package's -- and each one the README links kept."""
    kind, licence = case.vars["project_kind"], case.vars["license"]
    want = {"LICENSE"}
    if licence == "MIT OR Apache-2.0":
        want |= {"LICENSE-MIT", "LICENSE-APACHE"}
    if kind == "template" and licence != "MIT-0":
        want.add("LICENSE-MIT-0")
    have = {rel for rel in case.kept if rel.startswith("LICENSE")}
    if have != want:
        check.fail(f"{case.label}: licence files {sorted(have)}, expected {sorted(want)}")
    for link in re.findall(r"\]\((LICENSE[^)]*)\)", case.outputs["README.md"]):
        if link not in case.kept:
            check.fail(f"{case.label}: README.md links {link}, which this case does not keep")


if __name__ == "__main__":
    sys.exit(
        run(
            "typst",
            base_vars=BASE_VARS,
            cases=CASES,
            label=label,
            rules=(universe_regexes, export_ignore, licence_copies, compiler_cap),
            case_rules=(manifest, entrypoint, licence_files),
        )
    )
