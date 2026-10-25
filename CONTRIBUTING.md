# Contributing to `templates`

Thank you for considering contributing to `templates`!

## Prerequisites

Either **Nix** -- `nix develop` gives every tool below, at the versions `flake.lock` pins (the
nixpkgs a typst project's `flake.lock` pins too: the lock is typst's), a generated project's being
its own flake's -- or, installed yourself:

- **[cargo-generate](https://cargo-generate.github.io/cargo-generate/)** 0.25 or later, which the
  templates are for (`just generate`, `just smoke`, and `just lock-update` for python and rust).
- **Python** 3.11 or later, for `just render-check` (it installs `dev/requirements.txt` into
  `.venv`), `just sync`, `just generate` and `just lock-update`.
- **[just](https://github.com/casey/just)** and **[jq](https://jqlang.org/)** -- the automation,
  and what it reads JSON with.
- **[ShellCheck](https://www.shellcheck.net/)** and **[shfmt](https://github.com/mvdan/sh)** --
  the shell's linter and formatter (its style is `.editorconfig`'s).
- **[actionlint](https://github.com/rhysd/actionlint)** -- lints the workflows, this repository's
  and every template's.
- **[dprint](https://dprint.dev/)** -- formats the Markdown and TOML.
- **[cocogitto](https://docs.cog.tools/)** (`cog`) -- enforces Conventional Commits.
- **[git-cliff](https://git-cliff.org/)**, for maintainers: `just changelog` and `just release`
  write the changelog with it.
- **[Nix](https://nixos.org)** for the last of `just checks`, the flake's checks (`just nix`):
  without it, `just checks` stops there, every other check passed; for render-check's parse of the
  rendered Nix files, rust's check of its lock against its MSRV prompt and typst's of its `compiler`
  prompt against its lock's Typst, which it skips without Nix (CI's `checks.yml` refuses to); for
  `just smoke`, which runs a generated project's checks in its own flake's shell (typst's first
  compiles typst-package-check, which nixpkgs does not carry, for some minutes); and for `just
  lock-update`, which also needs GitHub reachable.

## Setup

1. Fork this repository and create your branch from `main`.
2. Clone your fork:

```sh
git clone https://github.com/<you>/templates && cd templates
```

3. Optionally, `just install-hooks`: `.githooks/` then checks the shell, the workflows and dprint
   before each commit, the message as a Conventional Commit, and every pushed commit's message
   before a push -- what CI would refuse, minutes earlier. They need `just`, `jq`, `shellcheck`,
   `shfmt`, `actionlint`, `dprint` and `cog` on `PATH` (inside `nix develop`, with Nix);
   `git config --unset core.hooksPath` turns them off.

## Guidelines

Before you start, read [AGENTS.md](AGENTS.md): how a template root and the rest differ, what
cargo-generate does with a file, which files are copies. It applies to human and AI-assisted
contributions alike. Each template's own checks, and what was verified of it, are its
`dev/<template>/README.md` ([typst](dev/typst/README.md), [python](dev/python/README.md),
[rust](dev/rust/README.md)).

## Development Workflow

1. The [Conventional Commits](https://www.conventionalcommits.org/) specification is enforced on
   every commit. A commit's subject is its changelog entry -- git-cliff writes the changelog from
   them at each release, each entry showing its scope -- so write it for the templates' users; a
   change to a template takes its name as the scope (AGENTS.md, Commits).
2. Run the checks. The `justfile` runs the workflows' commands:

```sh
just checks                    # every render-check, sync, no tool version by hand, the shell,
                               # the workflows, dprint, cog, the flake's last
just render-check [template]   # every templated file rendered for its answer combinations, checked
just sync                      # the shared files copied from shared/ (`just sync --check`: checked)
just smoke <template> <kind>   # generated with cargo-generate, then its own checks
just generate <template> <kind>  # into target/<template>/<kind>/demo, to look at, committed once
just lock-update [template]    # its flake.lock moved, and what follows it; none: every template's
just shell-check               # shellcheck and shfmt, this repository's (each template's:
                               # `just template-shell-check`)
just format                    # every formatter the checks hold the files to, `nix fmt` last
```

`just` alone lists the recipes; `nix fmt` alone formats the Nix, the shell and the justfiles.

`just checks` runs every template's render-check; `just sync --check`; `just tool-versions-check`
(no tool version by hand: each a lock's, but cargo-generate's floor; every action at its commit);
`just shell-check` (shellcheck and shfmt over every shell script, the git hooks and the root
justfile's script recipes) and `just template-shell-check` (each template's, its justfile's recipes
included); actionlint over every workflow, the root's and each template's; dprint over the root's
Markdown and TOML (a template root's are a generated project's); `cog check`; and `just nix` -- `nix
fmt -- --ci` (nixfmt, shfmt and just's own, through treefmt; it formats, and fails if that changed a
file), every system evaluated and the flake's checks, which run the shell and actionlint again in
the sandbox.

## Creating a Pull Request

1. Make sure `just checks` passes -- and, for a change to a template, `just smoke` for each of its
   kinds.
2. Open a pull request against `main`, titled as a conventional commit: a squash merge of two or
   more commits makes the title its commit, and so a changelog entry (CI checks it). Describe the
   problem it solves, and link its issue (`Fixes #123`), if any.
3. Wait for a maintainer's review. CI runs the smoke test of each template the pull request changes
   -- its folder, its `dev/<template>/` or its smoke workflow -- and every template's for a change
   to anything else but `docs/` (the root documents included), behind one check, `smoke-gate`.

## Maintainers

### Repository settings

- The required status checks are the jobs every pull request reports, whatever it touches:
  `checks`, `smoke-gate`, `nix flake check`, `dprint check` and `Check Conventional Commits`. None
  is path-filtered on pull requests: a required check that never reports blocks the merge.
- The auto-merge workflow's settings are listed at the top of
  `.github/workflows/dependabot-automerge.yml`. Without required status checks, it merges bumps
  that CI never gated.
- Enable "Allow GitHub Actions to create and approve pull requests" (Settings → Actions → General),
  off by default: `locks.yml` and `dprint-plugins.yml` open their pull requests with `GITHUB_TOKEN`,
  as github-actions[bot], and fail without it. Their workflows wait for a maintainer to approve them
  on the pull request, and the required checks with them.
- Enable private vulnerability reporting (Settings → Code security): it is off by default, and
  [SECURITY.md](SECURITY.md) and the issue form point to it.
- A merge queue, if ever enabled, needs `merge_group:` in every workflow behind a required check
  (`checks.yml`, `smoke.yml`, `nix.yml`, `style-check-dprint.yml`, `style-check-cocogitto.yml`), or
  its check never reports in the queue; cocogitto's steps for a pull request's commits and title
  then need a queue's equivalent.

### Releasing

The templates have no version file: a release is a tag, `v<version>`, every template's at once, and
the changelog's section. From a clean `main` equal to `origin/main`, CI green on it:

```sh
just changelog --unreleased   # the section the release will write
just release <major|minor|patch>
```

The recipe shows every step, in order, and runs no tests -- CI's verdict on that commit is the
release's: it refuses a release with nothing in it, writes the changelog (git-cliff), commits,
tags `v<version>` and pushes the commit and the tag together. The first release is `0.1.0`,
whatever the level. The tag runs `release.yml`: the GitHub release, the changelog's new section as
its notes, every tracked file as a tarball (`cargo generate --path <unpacked> <template>`).

- The commits since the last tag must hold a change a user meets (`feat`, `fix`, `perf`,
  `build`...): `chore`, `ci` and `style` alone make no release.
- The release pushes to `main` directly: with "Require a pull request before merging" on, the
  maintainer cutting it needs the rule's bypass. A refused push leaves the commit and the tag
  local -- push them again with `git push --atomic origin main v<version>` once allowed.

### Updating the tools

- **The locks** move monthly: `locks.yml` runs `just lock-update <template>` for every template with
  a `dev/<template>/lock.py` (by hand too, one template or all, on the default branch), each its own
  pull request on `locks/<template>`. The update moves the template's `flake.lock` to its inputs'
  newest, then what follows it -- python's dependency groups' pins and uv's `required-version`,
  rust's MSRV prompt and `cargo-dist-version` -- and runs render-check; it stops there, and the
  smoke tests are the pull request's. Its description lists each input and value moved, each
  dev-shell tool that moved with them (and the smoke tests' cargo-generate), and what is left to a
  person: render-check's failures, each line naming a version that moved (a document's, a prompt's),
  and typst's test references (a new Typst) and typst-package-check (an input at a tag). Fix those
  on the branch: the next run rebuilds it from the default branch unless it holds a person's commit,
  which it leaves as it is, failing that template's job, until its pull request is merged or closed
  (if GitHub refuses the force-push -- the default branch's workflows moved since -- the branch is
  made anew, and a new pull request replaces the old one). A failure -- a fetch, an evaluation --
  fails that template's job, and no pull request is opened for it that month: run it again by hand
  once it clears. Its work runs with a token that only reads; the push and the pull request are a
  second job's, which runs nothing else and refuses a change to anything `dev/<template>/lock.files`
  does not list, read from its own checkout, or to more than tracked files' content (a file added,
  deleted, linked or given another mode). `just lock-update <template> [--summary <file>]` is the
  same here, without the pull request, and refuses the same paths; a failure leaves what it moved in
  the working tree. `just lock-update` alone runs every template's in turn -- the root's lock is
  typst's -- each to its end, failing if one did. A generated project keeps its own lock current:
  its Dependabot moves the flake's inputs monthly, and python's and rust's `just pins-update` moves
  what follows them (python's pins; rust's dist).
- **A new Python, Rust or Typst, or a floor raised**, in a generated project and in the template:
  each template's page lists the files, step by step --
  [python](docs/python.md#new-pythons-and-the-floor),
  [rust](docs/rust.md#new-rust-releases-and-the-msrv),
  [typst](docs/typst.md#new-typst-releases-and-the-floor).
- **The dprint plugins** move monthly too: `dprint-plugins.yml` runs `just dprint-update`
  (`dev/dprint_plugins.py`; by hand too, on the default branch), one pull request on
  `dprint/plugins`. It moves every `dprint.json`'s plugins to their newest releases, as `dprint
  config update` finds them -- a release under three days old held back where dprint takes it from
  npm, as Dependabot's cooldown -- then formats the root's Markdown and TOML with them and writes
  the shared files' copies anew (`just sync`): dprint's warning that it could not update one fails
  it, rather than reading as nothing moved. A template root's Markdown and TOML hold Liquid,
  formatted in a generated project: the pull request's smoke tests run their `dprint check`. Its
  description lists each plugin moved, each file formatted, and what is left to a person; it is
  proposed as the locks are, by the same script (`dev/propose.sh`), refusing a change to anything
  `dev/dprint.files` does not let through, or more than tracked files' content. Dependabot has no
  dprint ecosystem, and nixpkgs' plugins lag their releases. A generated project moves its own by
  hand (`just dprint-update`), its Dependabot leaving them.
- **No tool version is written by hand** but cargo-generate's floor: a tool is a lock's -- in `nix
  develop`, a typst project's CI (its flake's `tools`), and this repository's CI (`dev/nix-tools.sh
  <template> <attribute>...`: the template's lock's nixpkgs, its tools on PATH) -- or an action's
  own, moved with the action by Dependabot (dprint/check's dprint, the latest; cocogitto-action's
  cog; rustsec/audit-check's cargo-audit). So a lock update moves them all, and `just
  tool-versions-check` refuses an installer given a version. **typst's tools** are its flake's, at
  typst's lock, which is also the root's, one original in `shared/`: after `nix flake update` here
  or in `typst/`, `just flake-sync` makes all three the updated one -- the root flake's inputs are
  typst's. render-check holds typst's `compiler` prompt to its lock's Typst, and nothing newer.
- **python's and rust's tools** are their own flakes'
  ([python/CONTRIBUTING.md](python/CONTRIBUTING.md), [rust/CONTRIBUTING.md](rust/CONTRIBUTING.md)).
  Their locks are made in a generated project and copied back (their `flake.nix` holds Liquid);
  rust's MSRV prompt then moves to what its rust-overlay knows
  ([dev/rust/README.md](dev/rust/README.md#the-lock)). Every lock follows nixos-unstable, each moved
  by the same monthly run: the templates' tools are at the root shell's nixpkgs.
- **The smoke tests** take each template's tools from its lock (`dev/nix-tools.sh`), as its dev
  shell has them; cargo-generate is the exception: the combinations jobs, and typst's and rust's
  generate jobs, generate with the floor, 0.25.0 (`dev/install-cargo-generate.sh`, the release's
  archive checked against its SHA-256), moved by hand when the templates' `cargo_generate_version`
  is, and the Nix jobs and python's generate job with the lock's -- both ends tested. Each
  generation runs with no network (`dev/offline.sh`: a network namespace of its own, made by sudo,
  as the runner's user), so both builds are held to need none, as the users' docs say (each
  `docs/<template>.md`, What needs the network).
- **Dependabot** moves the actions, in every folder of workflows -- this repository's, `shared/`'s
  and each template's -- in one pull request (each original and its copies move together, as
  `just sync --check` asks), as `build(deps)`, a changelog entry: they change what a project is
  generated with. It moves render-check's Python packages too (`dev/requirements.txt`: each pinned,
  what python-liquid and PyYAML pull in too; a move that needs another fails `just render-check`,
  which names it, until the file is compiled again, as its header says).

### Adding a template

A template root is any top-level folder holding a `cargo-generate.toml`; the tooling finds it. Its
name is a lowercase letter, then lowercase letters, digits and hyphens, and not `needed`
(`dev/changes.sh` and `just generate` refuse another). Refused until it is there:

- In the root `cargo-generate.toml`'s `sub_templates`, `dprint.json`'s excludes (`./<name>/`),
  `dev/dprint.files`' refusals (`!<name>/*`) and `.github/dependabot.yml`'s directories; the shared
  files `shared/manifest.toml` gives every template (`just sync` writes them), a `justfile` holding
  the shared recipes (each added by name, then `just sync`), a `dprint.json` with every template's
  plugins and TOML settings, and its `cargo-generate.toml` excluding the shared workflows, which
  hold GitHub's `${{ }}`, and `cliff.toml`, which holds Tera's `{% %}`: `just sync --check` fails
  without each.
- A `project_kind` placeholder with its `choices`, which `just generate` and `just smoke` take the
  kinds from; `dev/<template>/render-check.py` (`just render-check`: `dev/render_core.py`'s
  checks, run with the template's answer combinations and its own rules), `answers.toml` (the
  answers `just generate` and the smoke workflow generate with, cargo-generate's `--values-file`)
  and an executable `smoke.sh` (`just generate`, `just smoke`).
- `.github/workflows/smoke-<template>.yml` (actionlint refuses `smoke.yml` naming a workflow that
  is not there), and in `smoke.yml` the template's output of `changes`, its job, conditioned on
  that output (actionlint refuses an output that is not there), and its place among `smoke-gate`'s
  needs: the gate fails until the job is there and among them.
- Its `flake.nix`, if it holds Liquid, among the root formatter's nixfmt excludes (`flake.nix`),
  where `nix fmt` would fail on it.

Not refused, but expected: its `cargo-generate.toml` excluding its justfile, workflows and any other
file with another `{{ }}` syntax (AGENTS.md, What cargo-generate does with a file); its name in
`shared/manifest.toml`'s lists, for each shared file it should take that is not every template's;
`dev/<template>/README.md` and `docs/<template>.md`, its maintainers' and its users' documentation;
`dev/<template>/lock.py` (`dev/lock_core.py`'s), its lock's update and what follows it, with
`lock.files`, what it may change, which `locks.yml` then runs monthly; and its name in the lists
that name every template -- the README's templates, commands and records, CONTRIBUTING's and AGENTS'
links and counts, the pull request template's kinds, the bug report's templates.
