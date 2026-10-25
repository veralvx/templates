#!/usr/bin/env python3
"""python's render-check: dev/render_core.py's checks, every answer combination, then python's own:

  * the copies agree -- the workspace members' code, manifests and licence texts against the
    single package's -- and python_min's choices are the Pythons this harness knows;
  * each manifest describes its layout: the Pythons, the licence files, the kind, the image.

Usage:  python3 dev/python/render-check.py   (python-liquid and PyYAML; nix-instantiate if on PATH)
Exit:   0 = all good, 1 = at least one check failed.
"""

from __future__ import annotations

import pathlib
import re
import sys
import tomllib
from collections.abc import Mapping

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from render_core import IMAGE_LABELS, Case, Check, image_answer, image_wanted, run  # noqa: E402 - dev/, put on the path above

SINGLE = "src/{{crate_name}}"
CLI = "packages/{{project-name}}"
CORE = "packages/{{project-name}}-core"

# the template's names, one sample answer per prompt (render_core's SAMPLE_BUILTINS the rest of
# cargo-generate's own); `CASES` varies them
BASE_VARS = {
    "project-name": "sample-app",
    "crate_name": "sample_app",
    "description": "A sample package.",
    "author_name": "Jane Doe",
    "author_email": "jane@example.com",
    "github_username": "jane",
    "keywords": "cli, sample",
}
PYTHONS = ("3.12", "3.13", "3.14", "3.15")

# each kind's container_image answers (render_core's IMAGE_LABELS)
IMAGES = {"bin": (True, False), "lib": (None, True), "workspace": (True, False)}
CASES = [
    {"project_kind": kind, "license": lic, "python_min": py, **extra}
    | image_answer(image)
    for kind in ("bin", "lib", "workspace")
    for image in IMAGES[kind]
    for lic in ("MIT OR Apache-2.0", "MIT", "Apache-2.0")
    for py in PYTHONS
    for extra in ({}, {"author_email": "", "keywords": ""})
]


def label(case: Mapping[str, object]) -> str:
    return (
        f"{case['project_kind']}/{case['license']}/{case['python_min']}"
        + ("/bare" if case.get("author_email") == "" else "")
        + IMAGE_LABELS[case.get("container_image")]
    )


def pythons(check: Check) -> None:
    """python_min's choices are this harness's Pythons."""
    print("== python_min's choices")
    if "python_min" not in check.names():
        check.fail("no python_min prompt: this harness's cases answer one")
    for expr, name, spec in check.prompts:
        if name == "python_min" and tuple(spec.get("choices", ())) != PYTHONS:
            where = "" if expr is None else f" ({expr})"
            check.fail(f"python_min{where}'s choices are not {PYTHONS}: update this harness and .python-versions")


def duplicated_code(check: Check) -> None:
    """The single package and the workspace hold the same code twice: the library (__init__), the
    command line, `python -m`, and their tests. Only the import of the library differs."""
    print("== duplicated code")
    pairs = [
        (f"{SINGLE}/cli.py", f"{CLI}/src/{{{{crate_name}}}}/cli.py"),
        (f"{SINGLE}/__main__.py", f"{CLI}/src/{{{{crate_name}}}}/__main__.py"),
        ("tests/test_cli.py", f"{CLI}/tests/test_cli.py"),
        ("tests/test_{{crate_name}}.py", f"{CORE}/tests/test_core.py"),
    ]
    for single, member in pairs:
        a, b = check.texts[single], check.texts[member]
        if a.replace("{{crate_name}} import", "{{crate_name}}_core import") != b and a != b:
            check.fail(f"{member} has drifted from {single}")

    def body(rel: str) -> str:  # the code, its module docstring aside
        return check.texts[rel].split('"""', 2)[2]

    if body(f"{SINGLE}/__init__.py") != body(f"{CORE}/src/{{{{crate_name}}}}_core/__init__.py"):
        check.fail("the core's __init__.py has drifted from the single package's")
    print(f"  compared {len(pairs) + 1} pairs")


def member_licences(check: Check) -> None:
    """Each member carries copies of the root's licence texts: its sdist holds its own folder."""
    print("== member licence copies")
    check.licence_copies((CLI, CORE))


def floors(check: Check, case: Case) -> None:
    """The Pythons from the floor: .python-versions, ruff's and basedpyright's targets."""
    fail, floor = check.fail, case.vars["python_min"]
    wanted = [v for v in PYTHONS if v >= floor]
    if case.outputs[".python-versions"].split() != wanted:
        fail(f"{case.label}: .python-versions is not {wanted}")
    tools = tomllib.loads(case.outputs["pyproject.toml"])["tool"]
    if tools["ruff"]["target-version"] != "py" + floor.replace(".", ""):
        fail(f"{case.label}: ruff's target-version is not the floor")
    if tools["basedpyright"]["pythonVersion"] != floor:
        fail(f"{case.label}: basedpyright's pythonVersion is not the floor")


def manifests(check: Check, case: Case) -> None:
    """Each [project] describes the case: the kind, the licence files, the Pythons, the authors."""
    fail, vars_, kind = check.fail, case.vars, case.vars["project_kind"]
    floor = vars_["python_min"]
    wanted = [v for v in PYTHONS if v >= floor]
    root = tomllib.loads(case.outputs["pyproject.toml"])
    tools = root["tool"]
    licences = [f"LICENSE-{n}" for n in ("MIT", "APACHE") if n.lower()[:3] in vars_["license"].lower()]
    members = (
        [tomllib.loads(case.outputs[f"{member}/pyproject.toml"]) for member in (CLI, CORE)]
        if kind == "workspace"
        else [root]
    )
    if (kind == "workspace") == ("project" in root):
        fail(f"{case.label}: the root's [project] table does not match project_kind")
    if (kind == "workspace") != ("workspace" in tools.get("uv", {})):
        fail(f"{case.label}: [tool.uv.workspace] does not match project_kind")
    for manifest in members:
        project = manifest["project"]
        name = project["name"]
        if project["license"] != vars_["license"] or project["license-files"] != licences:
            fail(f"{case.label}: {name}: licence {project['license']!r}, files {project['license-files']}")
        if project["requires-python"] != f">={floor}":
            fail(f"{case.label}: {name}: requires-python is not the floor")
        listed = [
            c.rsplit(" :: ", 1)[1]
            for c in project["classifiers"]
            if re.fullmatch(r"Programming Language :: Python :: 3\.\d+", c)
        ]
        if listed != wanted:
            fail(f"{case.label}: {name}: its Python classifiers are {listed}, not {wanted}")
        author = {"name": "Jane Doe"} | ({"email": vars_["author_email"]} if vars_["author_email"] else {})
        if project["authors"] != [author]:
            fail(f"{case.label}: {name}: authors is {project['authors']!r}")
        if ("keywords" in project) != bool(vars_["keywords"]):
            fail(f"{case.label}: {name}: keywords present for an empty answer, or missing")
        scripts = "scripts" in project
        if scripts != (kind == "bin" or (name == vars_["project-name"] and kind == "workspace")):
            fail(f"{case.label}: {name}: [project.scripts] present={scripts}")
    if kind == "workspace":
        # the members' [project] tables are the single package's, but for what tells them apart
        single = tomllib.loads(check.render("pyproject.toml", {**vars_, "project_kind": "bin"}))["project"]
        own = {"name", "description", "dependencies", "urls", "scripts", "classifiers"}
        for manifest in members:
            shared = {k: v for k, v in manifest["project"].items() if k not in own}
            if shared != {k: v for k, v in single.items() if k not in own}:
                name = manifest["project"]["name"]
                fail(f"{case.label}: {name}'s [project] has drifted from the single package's")


def layout(check: Check, case: Case) -> None:
    """packages/ for a workspace, src/ otherwise; the image's Nix file, workflow, script and flake
    output, all or none."""
    kind = case.vars["project_kind"]
    image = image_wanted(case.vars)
    if any(f.startswith("packages/") for f in case.kept) != (kind == "workspace"):
        check.fail(f"{case.label}: packages/ kept for {kind}")
    if any(f.startswith("src/") for f in case.kept) == (kind == "workspace"):
        check.fail(f"{case.label}: src/ dropped for {kind}")
    for name in ("nix/image.nix", ".github/workflows/image.yml", ".github/image-registries.sh"):
        if (name in case.kept) != image:
            check.fail(f"{case.label}: {name} {'missing' if image else 'kept'}")
    if ("nix/image.nix" in case.outputs["flake.nix"]) != image:
        check.fail(f"{case.label}: flake.nix's image output does not match container_image")


if __name__ == "__main__":
    sys.exit(
        run(
            "python",
            base_vars=BASE_VARS,
            cases=CASES,
            label=label,
            rules=(pythons, duplicated_code, member_licences),
            case_rules=(floors, manifests, layout),
        )
    )
