# The python template

A [`cargo-generate`](https://github.com/cargo-generate/cargo-generate) template for a Python
project on [uv](https://docs.astral.sh/uv/) that starts with the whole toolchain wired up: every
ruff rule and basedpyright's strictest mode, tests with a 100% coverage gate, GitHub Actions CI on
every supported Python, Conventional Commits, changelogs by git-cliff, a release recipe that shows
every step, publishing to PyPI by Trusted Publishing, dependency auditing, a Nix flake whose tools
are the dev group's, and a `justfile` that runs locally what CI runs remotely.

It is one of [this repository](../README.md)'s templates, the counterpart of [rust](rust.md) and
[typst](typst.md), with what [ffsuite](https://github.com/veramachine/ffsuite)'s setup taught. See
[Attribution](#attribution).

## Usage

```sh
cargo install --locked cargo-generate   # 0.25 or later (the template refuses older)
cargo generate --git https://github.com/veralvx/templates python
```

The trailing `python` is the folder that holds this template: the repository holds every template,
each in its own folder, and with none named cargo-generate asks which (under `--silent`, it takes
the first). It generates from the default branch, `main`, which CI checks.

Another ref -- a release's tag (`--tag v<version>`), `--branch`, `--revision` -- names the new
project's branch after itself (cargo-generate's doing: `v<version>`, the branch, the commit's hash);
`--path` takes its clone's checked-out branch, or, from a detached HEAD or an unpacked release,
git's `init.defaultBranch` (`main` if unset). The project's CI and `just release` take `main`:
whatever the branch is named, `git branch -m main`.

cargo-generate is language-agnostic: Liquid over files, with conditionals; nothing here is Rust.
nixpkgs-unstable carries 0.25 (`nix run nixpkgs#cargo-generate`; 26.05's, 0.23.9, is below the
floor), built without its `git` feature: it refuses `--git` and makes no repository. Generate from
a clone instead, then `git init -b main` in the new project:

```sh
git clone https://github.com/veralvx/templates
nix run nixpkgs#cargo-generate -- generate --path templates python
cd my-project && git init -b main   # the name you gave
```

Everything can be answered non-interactively, which is what the smoke test does:

```sh
cargo generate --git https://github.com/veralvx/templates python \
  --name my-project --silent \
  -d project_kind=workspace \
  -d description="Does a thing." \
  -d author_name="Jane Doe" \
  -d author_email=jane@example.com \
  -d github_username=jane \
  -d license="MIT OR Apache-2.0" \
  -d python_min=3.13 \
  -d keywords="cli, parser"
```

Then, in the new project, the first steps its `CONTRIBUTING.md` gives (Maintainers, First steps):
`uv lock`, the first commit, the repository's settings, PyPI's pending publisher.

### If generation fails

`cargo-generate` creates the destination directory *before* it validates any answer, and leaves
it behind when validation rejects one. The retry then stops with
`Target directory already exists, aborting!` -- remove the empty directory and try again.

### What needs the network

Generating needs none: from a clone (`--path`), every kind generates with no network at all, as
the smoke test generates it; `--git` fetches the template first. After it:

- `uv lock`, the first and whenever the lock must change (`pyproject.toml` edited): PyPI's index,
  which uv's cache serves for as long as PyPI allows (ten minutes), or however old with
  `--offline` (`UV_OFFLINE=1`). A lock already current asks PyPI nothing: `uv lock` and the git
  hooks' lock check pass offline, the Python below once there.
- Whatever installs a group -- `uv sync`, `uv run`, `just checks`, the hooks' ruff check, `just
  audit`'s pip-audit, `just changelog`'s and `just release`'s git-cliff: the packages, from PyPI
  unless uv's cache holds them.
- Outside `nix develop`, a Python: whatever of uv's resolves the project -- the lock check, `uv
  sync`, `uv run`, `uv build` -- downloads the first of `.python-versions` (python-build-standalone,
  from GitHub) if it is not installed. The dev shell's is its own (`UV_PYTHON_DOWNLOADS=never`).
- `just audit` (and `just checks`): pip-audit asks PyPI of each package -- its own cache answers
  for fifteen minutes after, as PyPI allows.
- dprint, on its first run (`just dprint-check`, the hooks): its plugins, `dprint.json`'s URLs;
  then from its cache.
- `nix develop` and the flake's checks: the lock's inputs and its tools, from GitHub and Nix's
  binary cache, unless the store holds them.

git and the commit-message check (`cog`) need none.

## What you are asked

| Prompt            | Default             | Goes into                                                         |
| ----------------- | ------------------- | ----------------------------------------------------------------- |
| *(project name)*  | —                   | distribution name, command, import name (`-` as `_`), repository  |
| `description`     | `A Python package.` | `project.description`, README, the flake's `description`          |
| `project_kind`    | `bin`               | `bin`, `lib` or `workspace` -- see below                          |
| `author_name`     | —                   | `project.authors`, the licence's copyright line                   |
| `author_email`    | *(empty)*           | `project.authors`, code of conduct -- omitted if blank            |
| `github_username` | —                   | the repository's URLs, security advisory link                     |
| `license`         | `MIT OR Apache-2.0` | `project.license`, which `LICENSE-*` files are kept, README       |
| `python_min`      | `3.13`              | `requires-python`, `.python-versions`, classifiers, ruff, pyright |
| `keywords`        | *(empty)*           | `project.keywords` (comma-separated)                              |
| `container_image` | `true` (not `lib`)  | the flake's `image` and `image.yml` -- see below                  |

Every answer is validated at the prompt: the description, the author and the email cannot hold a
`"` or `\` (they land in TOML strings), nor the description a `$` (it lands in a Nix string). The
project name is checked before anything is written
([python/validate-name.rhai](../python/validate-name.rhai), a pre hook): its import name must be an
ASCII Python identifier, no keyword and no standard-library module's: `3d-tool`, `async` or
`calendar` is refused.

`container_image` is asked for `bin` and `workspace` alone: a library has no command to run.

### What `project_kind` selects

| Value       | Layout                                                                                                                                                            |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bin`       | one package, `src/<name>/`: a library and its command line (`[project.scripts]`)                                                                                  |
| `lib`       | one package, `src/<name>/`: a library                                                                                                                             |
| `workspace` | a uv workspace: `packages/<name>-core` (the library) and `packages/<name>` (the command line using it), each its own distribution, version, changelog and release |

The workspace's root is uv's virtual root: no `[project]` of its own, the tool groups and the tools'
configuration for every member. A member's requirement on another (`<name>-core>=0.1.0`) is resolved
from the workspace by uv (`[tool.uv.sources]`) and from PyPI by anyone else;
`tests/test_workspace.py` refuses a range the other member's version falls outside, and a member
whose licence texts differ from the root's -- an sdist holds the member's folder alone. One member
is the main package, `<name>`, marked in its own pyproject.toml (`[tool.<name>] main = true`: a
`tool.<name>` table is `<name>`'s owner's, PEP 518): the flake's default, the image's command and
GitHub's latest release; another member's tag makes no image, a command of its own or not. A single
package is its own main package.

### The Pythons

`python_min` is the floor; every newer one up to 3.15 is supported, listed once in
`.python-versions`. CI's matrix reads that file at run time and tests each. The flake runs the tests
and the types on each nixpkgs caches -- 3.13 and 3.14 at the shipped lock -- as an uncached package
set builds from source on every run (a fresh runner keeps no store), its packages' test suites too.
Its package, image and command build on the floor's Python. So a floor nixpkgs does not cache costs
every run: 3.12's, the package's build tools (about twenty small packages); 3.15's, which lists no
cached Python, its tests and types on 3.15 too (about sixty in all, pytest and its plugins among
them); either, the project's own dependencies. A new Python, or a higher floor, is the files
[New Pythons, and the floor](#new-pythons-and-the-floor) lists.

### The OCI image

With `container_image`, the flake has an `image` on Linux: `dockerTools.buildLayeredImage` of the
main package's command -- its closure alone, no base image and no `/bin/sh`, run as `nobody`,
labelled for GHCR. `nix build .#image` gives the gzipped docker-archive and the flake's checks build
it; `.#image.stream` streams it uncompressed, sparing the store a second copy of the closure.
`image.yml`, on the main package's release tag, streams it into Docker on amd64 and arm64, runs it,
pushes each, and joins them as `ghcr.io/<owner>/<repository>:<version>` (`latest` too while it is
the main package's highest release), with the job's token -- and to Docker Hub too, under the same
tags, once the variable `DOCKERHUB_USERNAME` and the secret `DOCKERHUB_TOKEN` are set
(`.github/image-registries.sh`; a Docker Hub failure holds the GHCR release back too); run by hand,
it builds and runs the image on both, pushing nothing (on a tag, it publishes that release again).
The image holds no CA certificates: Python's `ssl` verifying against the system's needs `contents =
[ pkgs.cacert ]` and `SSL_CERT_FILE` in `config.Env`.

## What you get

```
pyproject.toml        the project (or the workspace), the pinned dev group, every tool's config
.python-versions      the supported Pythons, one a line: CI's matrix, the flake's checks
uv.lock               written by the first `uv lock`, committed; `--locked` everywhere after
justfile              `just checks` = what CI runs, the flake's checks last; `just format`,
                      `just release`
flake.nix, nix/       the dev shell, `nix fmt`, the packages, the checks, the image (if chosen);
                      flake.lock pins nixpkgs (nixos-unstable)
.githooks/            opt-in (`just install-hooks`): the lock, ruff, the shell, the workflows,
                      dprint before a commit; Conventional Commits for the message and the push
.editorconfig         shfmt's style, for the shell scripts and the git hooks
cliff.toml, cog.toml  git-cliff changelogs, cocogitto's commit checks
dprint.json           Markdown and TOML formatting, its plugins pinned (`just dprint-update`)
src/, tests/          starter code: typed, documented, every line and branch tested
                      (a workspace puts these under packages/<name>/ and packages/<name>-core/)
AGENTS.md             the lint and type policy, and what to do when a rule fires
README, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT
LICENSE-MIT / LICENSE-APACHE (a workspace member carries its own copies)
.github/              8 workflows (9 with the image), dependabot, issue and PR templates,
                      the tag, release-notes (and image registries) scripts
```

### The tools, pinned to nixpkgs

The dev group's tools are exact pins (`ruff`, `basedpyright`, `pytest`
...), each the version the flake's nixpkgs carries, and `required-version` pins uv itself. So
`uv run` (and CI) and `nix flake check` judge the code with the same tools: with floors, the lock
took newer releases, and a new ruff rule or stub disagreed with Nix's verdict on the same code
(measured, in ffsuite). The flake's `pins` check holds them: a `nix flake update` that moves a
tool names each pin to move, and `just pins-update` moves them, the lock with them. Dependabot
moves the flake's inputs in a monthly pull request, `just pins-update` run on it when the check
names a pin. That is also why the template ships its `flake.lock`: the pins are only right for the
nixpkgs they were taken from.

### The CI workflows

- `checks.yml` -- the lock, ruff (lint and format), basedpyright, ty (advisory), vulture, and
  pytest with its coverage gate, on every Python `.python-versions` lists.
- `nix.yml` -- `nix fmt -- --ci` (nixfmt, shfmt and just's own, through treefmt: it formats, and
  fails if that changed a file), then `nix flake check`, on x86_64 Linux, aarch64 Linux and Apple
  silicon: the tests and the types on each Python nixpkgs caches against the built packages, ruff,
  the format, the shell (`just shell-check`: shellcheck and shfmt over the scripts, the hooks and
  the justfile's script recipes), the workflows (actionlint), dead code, the pins, and the command
  run through its wrapper; every system also evaluated.
- `security.yml` -- pip-audit over the exported lock, daily and when the lock changes.
- `dependency-review.yml` -- licence and advisory review on pull requests.
- `style-check-dprint.yml`, `style-check-cocogitto.yml` -- formatting, and Conventional Commits:
  every commit, and a pull request's title (a squash merge makes it the commit).
- `publish.yml` -- a release tag builds its package once, publishes it to PyPI by Trusted
  Publishing (no token stored; attestations), then makes the GitHub release of the same files,
  the changelog's section as notes. Only the PyPI job can mint a token; only the release job can
  write.
- `image.yml` (with the image) -- the main package's release tag pushes its OCI image to GHCR (and
  Docker Hub, given its secrets), for amd64 and arm64, after running it; by hand on a branch, a
  rehearsal that pushes nothing.
- `dependabot-automerge.yml` -- merges Dependabot's patch and minor action bumps once the
  required checks pass. Read its setup comment: without required checks it merges what CI never
  gated.

Every action is pinned to a commit, its version in a comment; Dependabot moves them -- in this
repository too, every template's workflows with the repository's own, in one pull request
([.github/dependabot.yml](../.github/dependabot.yml)). In a project, it watches the actions and
the flake's inputs (monthly, in one `build(deps)` pull request: `nix build` ships the package); the
dependency groups' pins move with nixpkgs (`just pins-update`), and pip-audit watches the lock.

### The changelog and `just release`

There is no `CHANGELOG.md` until the first release writes one: git-cliff generates it from the
commits, never a hand; a workspace member's from the commits touching its folder.
`just release [package] <major|minor|patch>` shows every step in order, none hidden in a hook or
another tool's config, and runs no tests -- it releases `origin/main`, which CI checks: it refuses a
dirty tree, another branch, a `main` that is not `origin/main` or a release with nothing in it; in a
workspace (step 4), a member ahead of any it needs, directly or through another -- one whose `src`
or installed fields changed since its release, a release not on PyPI, a requirement below one -- and
a library version its dependent's range excludes; sets the version (`uv version --bump`, the lock
with it -- the first release is the declared version, whatever the level); writes the changelog;
commits; tags `v<version>` (a member's `<package>-v<version>`); pushes the commit and the tag
atomically. If a step fails before the commit -- a git hook refusing it, say -- it puts the files
back.

## New Pythons, and the floor

What to change, file by file, in a generated project and in this template (each walked through:
[dev/python/README.md](../dev/python/README.md#in-this-repository)).

### In a project

**A new Python** (3.16, say):

1. `.python-versions`: `3.16`, on a line of its own at the end.
2. Each package's `pyproject.toml` -- the root's, or a workspace's members' (its root has no
   `[project]`): the classifier `"Programming Language :: Python :: 3.16"`, after the last.

Nothing else: CI's matrix reads `.python-versions` and tests it, and the lock stands,
`requires-python` being a floor alone. The tools must know the new Python: ruff, basedpyright and ty
at the shipped lock's pins took 3.15; one older than a Python it is given takes it after
`nix flake update` and `just pins-update`. The flake tests it too (`tests-py316`, `types-py316`)
once nixpkgs caches its package set, as it caches those its release recurses into
(`recurseIntoAttrs` in its `pkgs/top-level/all-packages.nix`: 3.13's and 3.14's at the shipped
lock): another's would build from source on every run, its packages' test suites too
(`nix/pythons.nix`'s `checked`; listing none of them, a project's flake tests its oldest). A lock
whose nixpkgs lacks the Python fails evaluation (`attribute 'python316Packages' missing`), and
`nix flake update` moves it.

**The floor raised** (3.13 to 3.14):

1. `.python-versions`: the old floor's line out. Its first line is the floor: the Python uv runs
   here, the dev shell's and the flake's packages'.
2. Each package's `pyproject.toml`: `requires-python = ">=3.14"`, and the old floor's classifier
   out.
3. The root `pyproject.toml`: `[tool.ruff]`'s `target-version = "py314"` and
   `[tool.basedpyright]`'s `pythonVersion = "3.14"`.
4. `uv lock`: the lock records `requires-python` (`uv lock --check`, `just checks`' first, refuses
   it until then).
5. `README.md`'s "Python 3.13 or later" and `CONTRIBUTING.md`'s "nixpkgs' Python 3.13".

ruff then names each version gate the new floor leaves dead (UP036, "Version block is outdated for
minimum Python version"), in the `_compat.py` AGENTS.md asks for. A `.python-versions` still
listing a Python below `requires-python` fails the flake's evaluation, the package refused for it.
Whether a floor raised is a breaking change is your policy: a `!` in its commit (`build!: require
Python 3.14`) puts it under the changelog's breaking changes.

### In the template

**A new Python** (3.16, say):

1. `python/cargo-generate.toml`: `python_min`'s `choices` gain `"3.16"`.
2. `python/.python-versions`: the last line gets its guard -- `{% if python_min <= "3.15" %}3.15`,
   its `{% endif %}` opening the next line -- and `3.16` follows it, unguarded. The classifiers of
   `python/pyproject.toml` and of both members (`python/packages/*/pyproject.toml`), the same:
   `{%- if python_min <= "3.15" %}` above the 3.15 one, `{%- endif %}` below it, the 3.16 one after.
   A guard compares strings, which holds while each minor has two digits.
3. `dev/python/render-check.py`: `PYTHONS` gains it.
4. `python/validate-name.rhai`: its two lists are the union, over the supported Pythons, of
   `keyword.kwlist` and of `sys.stdlib_module_names`' lowercase names without a leading `_` (a crate
   name is lowercase): the new Python's added (3.15 added the module `profiling`), sorted and
   wrapped at 100, and the range in its comment. Each Python's, the new one's here:

   ```sh
   uv run --no-project --python 3.16 python -c 'import keyword, sys; print(keyword.kwlist);
   print(sorted(n for n in sys.stdlib_module_names if n == n.lower() and not n.startswith("_")))'
   ```
5. `.github/workflows/smoke-python.yml`: its combinations generate every choice -- the oldest from
   the MIT licence, the newest from Apache-2.0, those between from the default licence, by the email
   answer (and by the kind too, once they outnumber two). The newest's arm
   (`Apache-2.0) python=3.15`) takes the new Python, and the previous newest joins those between.
6. `python/flake.lock`: its nixpkgs must carry `python316Packages` -- `just lock-update python` if
   it does not.
7. This page: "up to 3.15" ([The Pythons](#the-pythons)).

Then `just render-check python`, and `just smoke python <kind>` for each kind.

**The oldest dropped** (3.12, say): its choice; its line in `.python-versions` with the
`{% endif %}` that opens the next line (a stray one breaks every render), and its classifier with
its guard; `PYTHONS`; the smoke test's combination for the oldest (`MIT) python=3.12`), to the new
oldest; `validate-name.rhai`'s lists and range, recomputed without it. AGENTS.md's version-gate
example names 3.12 and 3.13: an example still.

**The default floor moved** (`3.13`): `python_min`'s `default`, `dev/python/answers.toml`'s
`python_min`, and this page's table and usage example.

## Developing this template

How the template is checked here, and what was verified of it, is the maintainers' side:
[dev/python/README.md](../dev/python/README.md); the repository's tools, rules and release,
[CONTRIBUTING.md](../CONTRIBUTING.md) and [AGENTS.md](../AGENTS.md).

## Attribution

The workflows, the justfile, `cliff.toml`, `cog.toml`, the hooks and the community documents are
adapted from the rust template, when it was the
[rust-template](https://github.com/veralvx/rust-template) (now [rust](rust.md)), and from
[ffsuite](https://github.com/veramachine/ffsuite), which took them from
[`veralvx/imi`](https://github.com/veralvx/imi) (MIT OR Apache-2.0).

## License

Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](../LICENSE-APACHE) or
  <http://www.apache.org/licenses/LICENSE-2.0>)
- MIT license ([LICENSE-MIT](../LICENSE-MIT) or <http://opensource.org/licenses/MIT>)

at your option.
