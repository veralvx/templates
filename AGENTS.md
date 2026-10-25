# AGENTS.md

Repository rules for `templates`, the cargo-generate templates. These apply to every contributor,
human or AI-assisted. The tools, the checks and the release are
[CONTRIBUTING.md](CONTRIBUTING.md)'s.

## 1. Templates, and the repository around them

- **A template root** -- a top-level folder holding a `cargo-generate.toml`: `typst/`, `python/`,
  `rust/` -- is what a generated project gets: every file in it but its `cargo-generate.toml`, its
  hook and what its answers `ignore`, rendered by cargo-generate's Liquid unless that
  `cargo-generate.toml` excludes it. Its own rules are its `AGENTS.md`'s
  ([typst](typst/AGENTS.md), [python](python/AGENTS.md), [rust](rust/AGENTS.md)), and they hold
  for what it generates.
- **The rest** is this repository's: `shared/` (the originals of the files templates share), `dev/`
  (render-check -- `render_core.py`, each template's rules on it -- and its `requirements.txt`; the
  lock updates -- `lock_core.py`, each template's `lock.py` on it (rust's, with the `msrv.py` it and
  render-check share) and the `lock.files` it may change; the plugins' update, `dprint_plugins.py`,
  and `dprint.files`; what the updates' workflows share, `propose.sh`, `unlisted.sh` and
  `on-default-branch.sh`; the answers and smoke scripts, `sync.py`, `changes.sh`,
  `tool_versions.py`, `nix-tools.sh`, `install-cargo-generate.sh`, `offline.sh`), `docs/` (each
  template's users' documentation), the workflows that check and update every template, the root
  justfile and flake, and the files any repository has. `dev/<template>/README.md` says how each
  template is checked, and what was verified of it.

A change to a template is judged by what it generates, never by its text alone: `just smoke
<template> <kind>` generates it with the real cargo-generate and runs the project's own checks.

## 2. What cargo-generate does with a file

- **A placeholder names a declared variable.** cargo-generate renders an unknown one as an empty
  string, without a word; `just render-check` refuses it.
- **A file with another `{{ }}` or `{% %}` syntax is excluded** (copied verbatim): in every template
  the workflows (GitHub's expressions), the justfile (just's), `cliff.toml` (Tera, which Liquid
  would evaluate silently) and every binary file, which cargo-generate aborts on (today, typst's
  images); typst's hooks, flake and lock, starter code and tests; python's hooks and `nix/`; rust's
  lock. An excluded file holds no placeholder: render-check refuses one.
- **Every answer combination renders and parses.** render-check renders each templated file for each
  template's answer combinations (typst's 32, python's 108, rust's 48) and parses the TOML, YAML,
  JSON and, with `nix-instantiate` on `PATH`, Nix; whitespace is the smoke test's, as python-liquid
  trims one newline liquid-rust keeps.

## 3. Copies stay copies

A file several templates share, or a template and the root, has one original under `shared/`, and
`just sync --check` (in `just checks` and CI) holds every copy byte for byte equal to it, its
executable bit too: `shared/root/` for files the root also has (they hold no Liquid where a
template renders them), `shared/template/` for the templates' alone, `shared/recipes.just` for the
recipes every justfile holds. [shared/manifest.toml](shared/manifest.toml) says which file goes
into which template. Change the original, then `just sync`; never edit a copy, and its wording must
hold in every place it lands. The one lock, the root's and typst's, is updated in either place, then
`just flake-sync`. python's and rust's locks are their own, each made in a generated project and
copied back, and what a template holds to its lock moves with it (rust's `msrv` regex: render-check
names the one it asks for). `just lock-update [<template>]` does all of it (none named: every
template's), `locks.yml` monthly.

## 4. Formats

Shell is formatted by shfmt (`.editorconfig` holds its style) and passes ShellCheck -- a justfile
script recipe included: `just shell-check` reads them out of `just --dump`, and refuses one that
splices a value into its text (it takes arguments). The Nix is nixfmt's, the justfiles just's own
(`nix fmt` formats the three); the Markdown and TOML, dprint's; `just format` runs them all, over
the templates' shell and justfiles too (their Markdown and TOML hold Liquid: a generated project
formats its own). The workflows pass actionlint. Actions are pinned to a full commit SHA, the
version in a comment, as Dependabot keeps them (`just tool-versions-check` refuses a tag or a
branch).

## 5. Comments: only what is essential

A comment says what the code cannot: why it is so, the source it follows, the constraint it
keeps. Make it concise and precise -- a line where a line does -- and never restate the code:
that is noise, and it goes stale. A change that falsifies a comment rewrites it.

## 6. Commits

[Conventional Commits](https://www.conventionalcommits.org/) are enforced by `cog check` locally
and in CI. The changelog is generated from the commits (`cliff.toml`), each entry showing its
scope, so the subject line is what a template user reads; `chore`, `ci` and `style` commits stay
out of it, and `!` or a `BREAKING CHANGE` footer -- a prompt renamed, a file a generated project no
longer has -- lists a commit first. A template's commit takes its name as scope; one touching
several names each; `shared` and `dev` are the shared files' and the tooling's:

```text
feat(typst): ask for the package's disciplines
fix(rust): keep the workspace's members on one version
docs(python,rust): take typst's wording of two shared workflows' comments
fix(shared): the automerge comment made exact
feat(python)!: require Python 3.13 or later
```

The git hooks (`just install-hooks`) check the same before a commit and a push; never bypass them
with `--no-verify`. `git revert` writes `Revert "..."`, which CI refuses: reword it as
`revert: ...`.

## 7. Before you claim a change is done

Run `just checks` -- every render-check, `just sync --check`, no tool version by hand, the shell,
the workflows, dprint, the commit messages and the flake -- and, for a change to a template, `just
smoke <template> <kind>` for each of its kinds. Together they are what CI runs, but the smoke tests'
releases, their other jobs and their Nix builds: CI's. Reporting "done" on a change that has not
passed them is the one thing that wastes the most time here.

If a check fails for reasons unrelated to your change, say so explicitly rather than working
around it -- a broken check that everyone routes around stops protecting anything.
