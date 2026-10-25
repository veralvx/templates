# Contributing to `{{project-name}}`

Thank you for considering contributing to `{{project-name}}`!

A project just generated from its template: start at [First steps](#first-steps), under
Maintainers.

## Prerequisites

Either **Nix** -- `nix develop` gives every tool below, at the versions `flake.lock` locks, the
ones CI runs; the first one compiles typst-package-check, which nixpkgs does not carry, for some
minutes -- or, installed yourself:

- **The tools whose verdict depends on their version**: CI's are the flake's, so another version
  of yours may judge apart from it (`nix build .#tools` gives all but typst-package-check).
  - **[Typst](https://github.com/typst/typst)**, the compiler.
  - **[tytanic](https://typst-community.github.io/tytanic/)** (`tt`), the test runner: its
    version is tied to one Typst's, whose rendering the tests' references are.
  - **[typstyle](https://github.com/typstyle-rs/typstyle)**, the formatter.
  - **[tinymist](https://github.com/Myriad-Dreamin/tinymist)**, the linter (`tinymist lint`; also
    Typst's language server, for an editor).
  - **[just](https://github.com/casey/just)**, the command runner the automation is written in:
    `just shell-check` reads the justfile's own recipes through its `--dump`.
  - **[ShellCheck](https://www.shellcheck.net/)** and **[shfmt](https://github.com/mvdan/sh)**,
    the shell's linter and formatter (its style is `.editorconfig`'s).
  - **[actionlint](https://github.com/rhysd/actionlint)**, the workflows' linter (and, through
    ShellCheck, their `run:` scripts').
  - **[typst-package-check](https://github.com/typst/package-check)**, the linter typst/packages
    runs on a submission: `cargo install --locked --git https://github.com/typst/package-check
    --tag v<version>` (it needs OpenSSL's headers), or its image, as CI runs it
    (`.github/install-tools.sh`).
- **[jq](https://jqlang.org/)** -- what the recipes read `typst eval`'s and `just --dump`'s JSON
  with.
- **[dprint](https://dprint.dev/)** -- formats the Markdown and TOML.
- **[cocogitto](https://docs.cog.tools/)** (`cog`) -- enforces Conventional Commits.
- **[git-cliff](https://git-cliff.org/)**, for maintainers: `just changelog` and `just release`
  write the changelog with it.
- **[Nix](https://nixos.org)** for the last of `just checks`, the flake's checks (`just nix`):
  without it, `just checks` stops there, every other check passed.

## Setup

1. Fork this repository and create your branch from `main`.
2. Clone your fork:

```sh
git clone https://github.com/<you>/{{project-name}} && cd {{project-name}}
```

3. Optionally, `just install-hooks`: `.githooks/` then checks the Typst code's format, the shell,
   the workflows, the imports' versions and dprint before each commit, the message as a
   Conventional Commit, and every pushed commit's message before a push -- what CI would refuse,
   minutes earlier. They need `just`, `typst`, `jq`, `typstyle`, `shellcheck`, `shfmt`,
   `actionlint`, `dprint` and `cog` on `PATH` (inside `nix develop`, with Nix);
   `git config --unset core.hooksPath` turns them off.

## Guidelines

Before you start, read [AGENTS.md](AGENTS.md): what the public API is, why warnings fail, what a
Typst package can hold, and how it is tested. It applies to human and AI-assisted contributions
alike.

## Testing Strategy

The tests are [tytanic](https://typst-community.github.io/tytanic/)'s, under `tests/`:

- **Visual tests** compare a test's pages with the reference images in its `ref/`. A change to
  how something looks updates them: `just update <test>`, then look at the new images before you
  commit them. CI keeps a failing test's output and difference images (the run's `tests`
  artifact).
- **Assertions** in a test without `ref/` are only compiled: what a function returns, and what it
  refuses -- `catch(() => ...)` gives a panic's message, to compare.
- **Regressions:** a fix comes with the test that failed before it.
{%- if project_kind == "template" %}
- **The template** is a test of its own, `@template`: tytanic compiles `template/` as `typst init`
  copies it, its import of this package pointed at this directory.
{%- endif %}

A new test: `tt new <name>` (a visual one), or a directory with a `test.typ` alone.

## Development Workflow

1. The [Conventional Commits](https://www.conventionalcommits.org/) specification is enforced on
   every commit. A commit's subject is its changelog entry -- git-cliff writes the changelog from
   them at each release -- so write it for the package's users.
2. Run the checks. The `justfile` runs the workflows' commands:

```sh
just checks          # everything CI runs, the flake's checks last
just test            # the tests alone
just lint            # tinymist's linter on the package{% if project_kind == "template" %} and its template{% endif %}
just format          # typstyle, shfmt, the justfile and dprint in place, then `nix fmt`
just bundle          # dist/preview/<name>/<version>: what typst/packages would get
just install         # the bundle as @local/<name>:<version>, to try it in a document{% if project_kind == "template" %}
just install preview # ... as @preview, for `typst init` of it (shadows the published version){% endif %}
just floor           # the README{% if project_kind == "template" %} and the template{% endif %} on `compiler`'s Typst, as typst-<version>
```

`just` alone lists every recipe.

A dependency on another Universe package is an import of it, its version exact
(`#import "@preview/<other>:1.2.3"`). The flake's tests run offline, in the Nix sandbox, where
Typst downloads nothing: give it the package there (Typst's `--package-cache-path`), or leave the
tests that need it to CI.

## Creating a Pull Request

1. Make sure `just checks` passes.
2. Open a pull request against `main`, titled as a conventional commit: a squash merge makes the
   title its commit, and so a changelog entry (CI checks it). Describe the problem it solves, and
   link its issue (`Fixes #123`), if any.
3. Wait for a maintainer's review.

## Maintainers

### First steps

`cargo-generate` made the git repository (a build without its `git` feature makes none:
`git init -b main` first -- the release is cut from `main`), but committed nothing:

```sh
git add .
git commit -m "chore: initial commit from template"
```

With [Nix](https://nixos.org), `nix develop` enters a shell with every tool `just checks` and
`just release` run. Then, in whichever order suits you:

- Push to `https://github.com/{{github_username}}/{{project-name}}`, as a **public** repository:
  `typst.toml` links it, and typst/packages checks that the link answers.
- Enable the repository settings the auto-merge workflow needs -- they are listed at the top of
  `.github/workflows/dependabot-automerge.yml`. Without required status checks, it merges bumps
  that CI never gated.
- Enable private vulnerability reporting (Settings → Code security): it is off by default, and
  [SECURITY.md](SECURITY.md) and the issue form point to it.
- To have a release prepare its Typst Universe submission ([below](#publishing-on-typst-universe)):
  fork [typst/packages](https://github.com/typst/packages), then set the repository variable
  `UNIVERSE_FORK` and the secret `UNIVERSE_TOKEN`.
- Run `just checks` once to confirm your tools are complete: a step that stops on a missing
  command names it.
- Make the package yours: the code under `src/`, the tests, the README (it is the package's page
  on Universe), the description and keywords in `typst.toml`. The name must not be the obvious
  one for what the package does (typst/packages' [naming rules](https://github.com/typst/packages/blob/main/docs/manifest.md#naming-rules)).

### Releasing

From a clean `main` equal to `origin/main`, CI green on it:

```sh
just changelog --unreleased   # the section the release will write
just release <major|minor|patch>
```

The recipe shows every step, in order, and runs no tests -- CI's verdict on that commit is the
release's: it refuses a release with nothing in it, sets the version in `typst.toml` and in every
`@preview/{{project-name}}:<version>` import, writes the changelog (git-cliff), commits, tags
`v<version>` and pushes the commit and the tag together. The first release is the version
`typst.toml` declares, `0.1.0`, whatever the level.

- The commits since the last tag must hold a change a user meets (`feat`, `fix`, `perf`,
  `build`...): `chore`, `ci` and `style` alone make no release.
- The release pushes to `main` directly: with "Require a pull request before merging" on, the
  maintainer cutting it needs the rule's bypass. A refused push leaves the commit and the tag
  local -- push them again with `git push --atomic origin main v<version>` once allowed.

### Publishing on Typst Universe

The tag runs `publish.yml`. It bundles the package, lints the bundle as typst/packages will (online:
the repository must be public), and makes the GitHub release -- the bundle as a tarball, the
changelog's new section as notes. With `UNIVERSE_FORK` set, it also pushes the bundle to a branch
`<name>-<version>` on your fork of typst/packages, at `packages/preview/{{project-name}}/<version>`,
committed as the release's author, and its run's summary links the pull request to open: title
`{{project-name}}:<version>`, as typst/packages asks; its checklist is yours to fill in. Merged, the
package is on Universe within about half an hour.

The settings it reads (Settings → Secrets and variables → Actions):

- the variable `UNIVERSE_FORK`: the fork, `<owner>/<repository>` (`{{github_username}}/packages`,
  as forked);
- the secret `UNIVERSE_TOKEN`: a fine-grained personal access token for that fork alone, with
  *Contents* and *Workflows* read and write -- the job first syncs the fork's main with
  typst/packages', whose workflow files the fork may not have yet, and that needs *Workflows*.
  It can be the `universe` environment's secret rather than the repository's, and that
  environment can admit release tags alone (Settings → Environments → universe, deployment tags
  `v*`).

Without them the release is made all the same; submit by hand: `just bundle`, then copy
`dist/preview/{{project-name}}/<version>` into a clone of your fork (typst/packages' guide
recommends a sparse checkout) at `packages/preview/{{project-name}}/<version>`.

## Updating the tools

The tools are the flake's, at the versions `flake.lock` locks -- the dev shell's and CI's alike
(`.github/install-tools.sh` builds the flake's `tools`) -- so moving the lock moves them all.
Dependabot does in a monthly pull request; by hand, `nix flake update`, then `just checks`. A new
Typst can render differently: `just update` the references that fail, after looking at the
difference. typst-package-check is its own flake input, at a tag, and the version typst/packages
runs on a submission (its `.github/workflows/lint.yml`): Dependabot leaves it, so move it when
typst/packages does -- the tag in `flake.nix`, then `nix flake update package-check` (CI runs the
image of that tag).
