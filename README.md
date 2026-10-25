# templates

[`cargo-generate`](https://github.com/cargo-generate/cargo-generate) templates in one repository:
a Typst package, a Python project and a Rust crate, each with its toolchain wired up, its checks
run locally as CI runs them, a Nix flake, and a release flow.

- **[typst](docs/typst.md)**: a Typst package -- a library, or a template package `typst init`
  starts projects from -- held to Typst Universe's rules.
- **[python](docs/python.md)**: a Python project on uv -- a package with its command, a library, or
  a uv workspace.
- **[rust](docs/rust.md)**: a Rust crate under a strict lint policy -- a binary, a library, both,
  or a workspace.

## Usage

```sh
cargo install --locked cargo-generate   # 0.25 or later (the templates refuse older)
cargo generate --git https://github.com/veralvx/templates typst
cargo generate --git https://github.com/veralvx/templates python
cargo generate --git https://github.com/veralvx/templates rust
```

Each command names its template's folder; with none named, cargo-generate asks which (under
`--silent`, it takes the first). It generates from the default branch, `main`, which CI checks.
nixpkgs' cargo-generate is built without its `git` feature and refuses `--git`: generate from a
clone instead, as each template's documentation shows, with its prompts, what it generates and how
to answer them all non-interactively.

## What every template generates

- A `justfile` that runs locally what CI runs remotely: `just checks`, its formatter (`just format`,
  rust's `just fmt`), `just release`.
- GitHub Actions workflows, every action pinned to a commit and moved by Dependabot, as are the
  flake's inputs, monthly, every tool with them (python's and rust's `just pins-update` moving the
  pins that follow them).
- Conventional Commits, enforced by cocogitto and opt-in git hooks; a changelog written by
  git-cliff at each release, never by hand.
- A release tag publishes: python's packages to PyPI and rust's crates to crates.io, through Trusted
  Publishing (no token stored with the repository), rust's binaries through dist; typst's prepares
  its Typst Universe submission. Each makes its GitHub release, the changelog's section its notes.
- A Nix flake: the development shell, `nix fmt`, the checks as derivations.
- dprint for the Markdown and TOML, an `.editorconfig` for the shell, and the community documents:
  `CONTRIBUTING.md`, `AGENTS.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue and pull request
  templates.

## Releases

A release tags every template at once, `v<version>`, and writes its section of `CHANGELOG.md` (from
the first release on); its GitHub release carries every tracked file as a tarball, which `cargo
generate --path <unpacked> <template>` generates from.

## How it is verified

Each check below is run, not reasoned about; what was verified of each template is its
`dev/<template>/README.md` ([typst](dev/typst/README.md), [python](dev/python/README.md),
[rust](dev/rust/README.md)).

- **Generation.** Once the templates had moved here, every kind and option each smoke test covers
  generated, from this repository, byte for byte -- contents and modes -- what the template's own
  repository generated, but for a few comments of the shared workflows, reworded here; by `--path`
  and by `--git`, from a branch and from a tag. What changed since is this repository's history. And
  with no network at all -- each in a network namespace of its own, by cargo-generate's release
  build and by nixpkgs' kind (no `git` feature) -- every combination the smoke tests generate, each
  project the same as with it; what the projects need of the network after, each
  `docs/<template>.md` says, each claim run offline, from cold caches and warm, but Nix's and the
  package-check image's, which nothing here can fetch.
- **Each template.** render-check renders every templated file for each template's answer
  combinations and parses the result, and catches each defect planted in it; the smoke test's own
  steps -- every answer combination generated, the answers it must refuse refused, every kind's
  project -- run as written; `just smoke` passes for every kind, with Nix stood in where nothing can
  be built here: each `nix develop` the dev shell's own packages at their versions and nothing else
  -- but git, awk, valgrind, Python's and Rust's patch releases and stdenv's other tools, this
  machine's -- each in the generated project's own shell, Miri's tests run natively, `nix fmt` and
  `nix flake check` left to CI. Every kind's flake evaluates on every system, and its format, shell
  and workflows checks -- and python's and rust's pins (a rust library has none) -- pass as their
  derivations run them, git and awk aside.
- **The shared files.** `just sync --check` fails on each drift planted: every copy changed, its
  executable bit flipped or missing, every line of every shared recipe, a dprint plugin apart, a
  template root missing from the lists that must name it, and Liquid in a root original wherever
  cargo-generate itself renders it. Its reading of a template's exclude list matches cargo-generate
  0.25.0's own, fuzzed against the libraries cargo-generate uses.
- **CI.** The template selection (`dev/changes.sh`) and the one gate, `smoke-gate`, run as their
  workflow holds them, over merge commits made as GitHub makes them and every job result -- a
  failed or cancelled job, a template added with no job; every required check reports on every pull
  request; every workflow passes actionlint.
- **This repository's own tooling.** The root flake evaluates on every system, with its lock as
  committed, and its checks pass, emulated here as their derivations run them, with the same tool
  versions but git's and awk's; every step of `just checks` passes but the last, the flake's checks,
  which build -- and in the root's dev shell too, Nix stood in as above; `just generate` makes what
  the smoke tests make; four releases against a bare remote tag, write the changelog, push the
  commit and the tag together and refuse what they should.
- **The lock updates.** `just lock-update` moves back to the shipped tree, exactly, each staleness
  planted -- python's pins, rust's MSRV prompt and `cargo-dist-version`, the lock's three copies --
  names each dev-shell tool the lock moved, and leaves an idle tree as it is; `locks.yml`'s own
  scripts open, update, keep or refuse each pull request as they should, against a bare remote.
  `nix flake update`, unreachable here, is stood in for. No tool version is written by hand
  (`just tool-versions-check`, which refuses each form planted).
- **The dprint plugins' update.** `just dprint-update` moves every `dprint.json` alike, formats the
  root's Markdown and TOML and writes the shared files' copies anew, says each plugin moved (a move
  to npm too) and each file formatted, fails on dprint's own failure warning but its npm fallback,
  notes what it skipped, leaves an idle tree as it is and refuses a change outside
  `dev/dprint.files`. Its pull request is the locks' script's (`dev/propose.sh`), which refuses a
  change that rewrites its matcher, widens its list or does more than change tracked files'
  content, against a bare remote. `dprint config update`, unreachable here, is stood in for.

The rest of each smoke workflow -- the git hooks' refusals, typst's lint-warning, `just floor` and
bundler steps, the changelogs and packages, the images, the releases, clippy on the latest stable,
Miri, the Nix builds -- the lock and plugin updates' workflows, and GitHub's side of CI run on
GitHub.

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) (the tools, the checks, the release, adding a template),
[AGENTS.md](AGENTS.md) (the rules), [SECURITY.md](SECURITY.md),
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Attribution

The repository's tooling -- the workflows, the justfiles' shape, `cliff.toml`, `cog.toml`, the
hooks, the community documents -- is adapted from the three repositories below, which took it,
directly or through [ffsuite](https://github.com/veramachine/ffsuite), from
[`veralvx/imi`](https://github.com/veralvx/imi) (MIT OR Apache-2.0); each template's own attribution
is its documentation's.

## Earlier releases

The templates were [typst-template](https://github.com/veralvx/typst-template),
[python-template](https://github.com/veralvx/python-template) and
[rust-template](https://github.com/veralvx/rust-template), which stay online with their releases
and changelogs:
[typst-template's](https://github.com/veralvx/typst-template/blob/v0.1.1/CHANGELOG.md) (0.1.0,
0.1.1), [python-template's](https://github.com/veralvx/python-template/blob/v0.1.0/CHANGELOG.md)
(0.1.0) and [rust-template's](https://github.com/veralvx/rust-template/blob/v0.1.1/CHANGELOG.md)
(0.1.0, 0.1.1). This repository's `CHANGELOG.md` begins with its first release, `v0.1.0`.

## License

Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) or
  <http://www.apache.org/licenses/LICENSE-2.0>)
- MIT license ([LICENSE-MIT](LICENSE-MIT) or <http://opensource.org/licenses/MIT>)

at your option.

The generated projects are yours: their licence is the one you choose at generation.
