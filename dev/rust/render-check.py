#!/usr/bin/env python3
"""rust's render-check: dev/render_core.py's checks, every answer combination, then rust's own:

  * the starter code's two copies agree, and each workspace member carries the root's licence
    texts;
  * each Cargo.toml describes its layout -- the metadata clippy::cargo_common_metadata asks for,
    the kind's tables, the authors and licence -- the source files and the image are the kind's;
  * crates.io: publish-crates.yml in every kind, dist's custom publish job (given the OIDC token
    Trusted Publishing needs) or, a library's alone, publish.yml calling it;
  * when `nix` is on PATH, the shipped flake.lock is every rendered flake.nix's as it stands
    (nothing to relock), and the `msrv` regex is exactly the stable releases its rust-overlay
    knows from 1.90 -- each as 1.<minor> or exactly, nothing else, the regex they ask for printed
    on a mismatch -- its prompt naming the range. That fetches rust-overlay at its locked revision
    (nixpkgs is not: the smoke test's Nix job builds with it).

Usage:  python3 dev/rust/render-check.py   (python-liquid and PyYAML; nix-instantiate, nix if on PATH)
Exit:   0 = all good, 1 = at least one check failed.
"""

from __future__ import annotations

import pathlib
import re
import shutil
import sys
import tomllib
from collections.abc import Mapping

# dev/ and dev/rust/ named, not left to the script's own folder: `python -I` leaves that out
sys.path += [str(pathlib.Path(__file__).resolve().parents[1]), str(pathlib.Path(__file__).resolve().parent)]
from msrv import MSRV_FLOOR, Release, msrv_regex, msrv_span, rust_releases  # noqa: E402 - dev/rust/, put on the path above
from render_core import IMAGE_LABELS, Case, Check, image_answer, image_wanted, run  # noqa: E402 - dev/, put on the path above

# the template's names, one sample answer per prompt (render_core's SAMPLE_BUILTINS the rest of
# cargo-generate's own); `CASES` varies them
BASE_VARS = {
    "project-name": "sample-crate",
    "crate_name": "sample_crate",
    "description": "A sample crate.",
    "author_name": "Jane Doe",
    "author_email": "jane@example.com",
    "github_username": "jane",
    "msrv": "1.92",
    "keywords": "rust, sample",
    "categories": "development-tools, command-line-utilities",
}

# each kind's container_image answers (render_core's IMAGE_LABELS)
IMAGES = {"bin": (True, False), "lib": (None, True), "both": (True, False), "workspace": (True, False)}
CASES = [
    {"project_kind": k, "license": lic, **extra} | image_answer(image)
    for k in ("bin", "lib", "both", "workspace")
    for image in IMAGES[k]
    for lic in ("MIT OR Apache-2.0", "MIT", "Apache-2.0")
    for extra in ({}, {"author_email": ""})
]


def label(case: Mapping[str, object]) -> str:
    return (
        f"{case['project_kind']}/{case['license']}"
        + ("/no-email" if case.get("author_email") == "" else "")
        + IMAGE_LABELS[case.get("container_image")]
    )


def starter_code(check: Check) -> None:
    """The starter function's two copies -- src/lib.rs for the single-package layouts,
    crates/<name>-core/src/lib.rs for the workspace -- differ in prose on purpose, never in code."""
    print("== duplicated starter code")

    def fn_body(rel: str) -> str:
        text = check.texts[rel]
        return re.sub(r"\s+", " ", text[text.index("#[must_use]") :]).strip()

    core, single = "crates/{{project-name}}-core/src/lib.rs", "src/lib.rs"
    if core not in check.texts or single not in check.texts:
        check.fail("expected both a single-package and a workspace copy of lib.rs")
    elif fn_body(single).replace("{{crate_name}}::", "CRATE::") != fn_body(core).replace(
        "{{crate_name}}_core::", "CRATE::"
    ):
        check.fail("src/lib.rs and the workspace core lib.rs have drifted apart")


def member_licences(check: Check) -> None:
    """Each workspace member carries the root's licence texts: a member's .crate holds its own
    directory alone."""
    print("== member licence copies")
    check.licence_copies(f"crates/{member.name}" for member in sorted((check.template / "crates").iterdir()))


def manifest(check: Check, case: Case) -> None:
    """Cargo.toml describes the layout: the metadata, the kind's tables, the authors, the licence."""
    fail, vars_, kind = check.fail, case.vars, case.vars["project_kind"]
    parsed = tomllib.loads(case.outputs["Cargo.toml"])
    is_workspace = kind == "workspace"
    pkg = parsed["workspace"]["package"] if is_workspace else parsed["package"]
    # A workspace root inherits keywords but not categories or description: those are per-member,
    # and each member manifest sets them (members, below).
    for key in ["keywords"] if is_workspace else ["keywords", "categories"]:
        if not pkg.get(key):
            fail(f"{case.label}: clippy::cargo_common_metadata needs a non-empty {key}")
        elif any(not v.strip() for v in pkg[key]):
            fail(f"{case.label}: blank entry in {key}")
    if is_workspace != ("workspace" in parsed):
        fail(f"{case.label}: [workspace] table presence does not match project_kind")
    if ("bin" in parsed) != (kind not in ("lib", "workspace")):
        fail(f"{case.label}: [[bin]] present={'bin' in parsed} for project_kind")
    if ("profile" in parsed and "dist" in parsed["profile"]) != (kind != "lib"):
        fail(f"{case.label}: [profile.dist] does not match project_kind")
    author = "Jane Doe" if vars_["author_email"] == "" else "Jane Doe <jane@example.com>"
    if pkg["authors"] != [author]:
        fail(f"{case.label}: authors is {pkg['authors']!r}, expected [{author!r}]")
    if pkg["license"] != vars_["license"]:
        fail(f"{case.label}: license is {pkg['license']!r}")


def members(check: Check, case: Case) -> None:
    """A workspace's members each set their own description and categories, and inherit the lints;
    a single package's source files are its kind's, and only those."""
    kind = case.vars["project_kind"]
    if kind == "workspace":
        crates = sorted((check.template / "crates").iterdir())
        if len(crates) != 2:
            check.fail(f"{case.label}: expected 2 member crates, found {len(crates)}")
        for member in crates:
            whole = tomllib.loads(case.outputs[f"crates/{member.name}/Cargo.toml"])
            m = whole["package"]
            if not m.get("description") or not m.get("categories"):
                check.fail(f"{case.label}: {member.name} must set its own description and categories")
            # `[lints]` is a top-level table: a member without `workspace = true` silently opts
            # out of the whole policy
            if whole.get("lints") != {"workspace": True}:
                check.fail(f"{case.label}: {member.name} must inherit the lints: [lints] workspace = true")
    else:
        for name, wanted in (("lib.rs", kind != "bin"), ("main.rs", kind != "lib")):
            if (f"src/{name}" in case.kept) != wanted:
                check.fail(f"{case.label}: src/{name} present={f'src/{name}' in case.kept}, wanted={wanted}")


def image(check: Check, case: Case) -> None:
    """The image: its workflow, its script and the flake's output, all or none."""
    wanted = image_wanted(case.vars)
    for name in (".github/workflows/image.yml", ".github/image-registries.sh"):
        if (name in case.kept) != wanted:
            check.fail(f"{case.label}: {name} {'missing' if wanted else 'kept'}")
    if ("dockerTools" in case.outputs["flake.nix"]) != wanted:
        check.fail(f"{case.label}: flake.nix's image does not match container_image")


def publishing(check: Check, case: Case) -> None:
    """crates.io: publish-crates.yml always, called by dist's release.yml (dist-workspace.toml's
    custom publish job, given the OIDC token Trusted Publishing needs) or, a library's alone, by
    publish.yml, with release-notes.sh for its GitHub release."""
    lib = case.vars["project_kind"] == "lib"
    for name, wanted in (
        (".github/workflows/publish-crates.yml", True),
        (".github/workflows/publish.yml", lib),
        (".github/release-notes.sh", lib),
    ):
        if (name in case.kept) != wanted:
            check.fail(f"{case.label}: {name} {'missing' if wanted else 'kept'}")
    if lib:
        return
    dist = tomllib.loads(case.outputs["dist-workspace.toml"]).get("dist", {})
    if "./publish-crates" not in dist.get("publish-jobs", []):
        check.fail(f"{case.label}: dist-workspace.toml's publish-jobs lacks ./publish-crates")
    granted = dist.get("github-custom-job-permissions", {}).get("publish-crates", {})
    if granted != {"contents": "read", "id-token": "write"}:
        check.fail(f"{case.label}: dist's publish-crates job is given {granted}, not contents: read, id-token: write alone")


def lock_and_msrv(check: Check, cases: list[Case]) -> None:
    """The shipped flake.lock: every rendered flake.nix's, as it stands; the `msrv` regex, the
    stable releases its rust-overlay knows from the floor -- 1.<minor> or exact -- and no other
    (rust-overlay refuses a release it does not know: `Stable <version> is not available`) -- its
    prompt naming the range."""
    print("== flake.lock and the msrv cap")
    if "msrv" not in check.names():
        check.fail("no msrv prompt: the toolchain's version is its answer")
    nix = shutil.which("nix")
    if nix is None:
        print("  SKIP: no nix on PATH (CI's checks.yml has it)")
        return
    flakes = {case.label: case.outputs["flake.nix"] for case in cases if "flake.nix" in case.outputs}
    releases: list[Release] = []
    for text in sorted(set(flakes.values())):
        try:
            releases = rust_releases(nix, text, check.template / "flake.lock")
        except Exception as exc:  # noqa: BLE001 - report and continue
            names = [k for k, v in flakes.items() if v == text]
            check.fail(f"{names[0]} (and {len(names) - 1} more alike): {exc}")
    if not releases:
        return
    known = {".".join(map(str, r)) for r in releases if r[0] == 1 and r[1] >= MSRV_FLOOR}
    known |= {f"1.{r[1]}" for r in releases if r[0] == 1 and r[1] >= MSRV_FLOOR}
    newest = ".".join(map(str, releases[-1]))
    span = msrv_span(releases)
    # every 1.<minor> and 1.<minor>.<patch> far past the newest, and malformed ones
    tried = [f"1.{m}" for m in range(200)]
    tried += [f"1.{m}.{p}" for m in range(200) for p in range(20)]
    tried += ["1", "1.", "1.97.", "1.097", "1.97.01", "1.97.1.0", "01.97", "2.0", "1.97 "]
    tried += [" 1.97", "1.97-beta", "stable", "nightly", "1.100.0-nightly", ""]
    for expr, name, spec in check.prompts:
        if name != "msrv":
            continue
        where = "" if expr is None else f" ({expr})"
        regex = spec["regex"]
        bad = [value for value in tried if bool(re.search(regex, value)) != (value in known)]
        # exactly the regex these releases ask for: nothing else matches, and nothing in it Rust's
        # regex crate would read otherwise than Python's re (the tried values above show what it
        # takes; the equality, that it takes nothing more)
        if bad or regex != msrv_regex(releases):
            check.fail(
                f"msrv regex{where} is not flake.lock's rust-overlay's (newest {newest})"
                + (f", on {', '.join(repr(v) for v in bad[:8])}" if bad else "")
                + (" ..." if len(bad) > 8 else "")
                + f"; the regex it asks for:\n    regex = '{msrv_regex(releases)}'"
            )
        # the prompt names the range, as cargo-generate's refusal does not
        if not re.search(rf"(?<![\w.]){re.escape(span)}(?![\w.])", spec["prompt"]):
            check.fail(f"msrv prompt{where} does not name its range, {span!r}")
    apart = len(set(flakes.values()))
    print(
        f"  {len(flakes)} flake.nix rendered ({apart} apart), one lock; msrv: "
        f"{len(known)} answers, {span}, {len(tried)} tried"
    )


if __name__ == "__main__":
    sys.exit(
        run(
            "rust",
            base_vars=BASE_VARS,
            cases=CASES,
            label=label,
            rules=(starter_code, member_licences),
            case_rules=(manifest, members, image, publishing),
            final_rules=(lock_and_msrv,),
        )
    )
