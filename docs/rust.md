# The rust template

A [`cargo-generate`](https://github.com/cargo-generate/cargo-generate) template
for a Rust crate that starts out with the whole toolchain already wired up:
a deliberately strict lint policy, GitHub Actions CI, Conventional Commits,
changelog generation, dependency auditing, a Nix flake, and a `justfile` that
runs the same checks locally that CI runs remotely.

It is one of [this repository](../README.md)'s templates, the counterpart of
[python](python.md) and [typst](typst.md). The configuration is adapted from
[`veralvx/imi`](https://github.com/veralvx/imi) (MIT OR Apache-2.0). See
[Attribution](#attribution).

## Usage

```sh
cargo install --locked cargo-generate   # 0.25 or later (the template refuses older)
cargo generate --git https://github.com/veralvx/templates rust
```

The trailing `rust` is the folder that holds this template: the repository
holds every template, each in its own folder, and with none named
cargo-generate asks which (under `--silent`, it takes the first). It generates
from the default branch, `main`, which CI checks.

Another ref -- a release's tag (`--tag v<version>`), `--branch`, `--revision`
-- names the new project's branch after itself (cargo-generate's doing:
`v<version>`, the branch, the commit's hash); `--path` takes its clone's
checked-out branch, or, from a detached HEAD or an unpacked release, git's
`init.defaultBranch` (`main` if unset). The project's CI and `just release`
take `main`: whatever the branch is named, `git branch -m main`.

nixpkgs-unstable carries 0.25 (`nix run nixpkgs#cargo-generate`; 26.05's,
0.23.9, is below the floor), built without its `git` feature: it refuses
`--git` and makes no repository. Generate from a clone instead, then
`git init -b main` in the new project:

```sh
git clone https://github.com/veralvx/templates
nix run nixpkgs#cargo-generate -- generate --path templates rust
cd my-crate && git init -b main   # the name you gave
```

From a local checkout, any build generates with `--path`:
`cargo generate --path ./templates rust`.

Everything can be answered non-interactively, which is what the smoke test does:

```sh
cargo generate --path ./templates rust \
  --name my-crate --silent \
  -d description="Does a thing." \
  -d project_kind=both \
  -d author_name="Jane Doe" \
  -d author_email=jane@example.com \
  -d github_username=jane \
  -d license="MIT OR Apache-2.0" \
  -d msrv=1.97 \
  -d keywords="cli,parser" \
  -d categories="command-line-utilities"
```

Then, in the new project, the first steps its `CONTRIBUTING.md` gives
(Maintainers, First steps): the first commit, the repository's settings, and
for a binary `dist init`.

### If generation fails

`cargo-generate` creates the destination directory *before* it validates any
answer, and leaves it behind when validation rejects one. The retry then stops
with `Target directory already exists, aborting!`, which reads as though the
first run succeeded. It did not -- remove the empty directory and try again:

```sh
rm -rf ./my-crate && cargo generate --git ... rust --name my-crate
```

This template validates ten answers, so it runs into this more often than a
template that validates none.

### What needs the network

Generating needs none: from a clone (`--path`), every kind generates with no
network at all, as the smoke test generates it; `--git` fetches the template
first. After it:

- The toolchain `rust-toolchain.toml` pins: rustup installs it on first use
  (`cargo`, and so the git hooks' format check), and `just miri`'s nightly.
  The crates need nothing: there are none to fetch until you add one.
- `just audit` (and `just checks`): cargo-audit fetches its advisory database.
- dprint, on its first run (`just dprint-check`, the hooks): its plugins,
  `dprint.json`'s URLs; then from its cache.
- `nix develop`, `nix build` and the flake's checks: the lock's inputs and its
  tools, from GitHub and Nix's binary cache, unless the store holds them.

git and the commit-message check (`cog`) need none.

## What you are asked

| Prompt            | Default             | Goes into                                                         |
| ----------------- | ------------------- | ----------------------------------------------------------------- |
| *(project name)*  | —                   | package name, `[[bin]]`, repository URL, docs                     |
| `description`     | `A Rust crate.`     | `package.description`, README, the flake's `meta`                 |
| `project_kind`    | `bin`               | `bin`, `lib`, `both`, or `workspace` -- see below                 |
| `author_name`     | —                   | `package.authors`, licence copyright line                         |
| `author_email`    | *(empty)*           | `package.authors`, code of conduct -- omitted if blank            |
| `github_username` | —                   | repository URL, security advisory link                            |
| `license`         | `MIT OR Apache-2.0` | `package.license`, which `LICENSE-*` files are kept, README       |
| `msrv`            | `1.97`              | `package.rust-version`, `rust-toolchain.toml`, CI's MSRV job, Nix |
| `keywords`        | `rust`              | `package.keywords` (comma-separated, max 5)                       |
| `categories`      | `development-tools` | `package.categories` (comma-separated, max 5)                     |
| `container_image` | `true` (not `lib`)  | the flake's `image` and `image.yml` -- see below                  |

Every answer is validated at the prompt, so a typo is caught before generation
rather than at `cargo publish`. The project name is checked before anything is
written ([rust/validate-name.rhai](../rust/validate-name.rhai), a pre hook): its
crate name must be a Rust identifier, no keyword and no crate of Rust's own --
`3d-tool`, `fn`, `self` or `std` is refused.
`description` and `author_name` land in TOML strings, so they may not hold `"`
or `\`. `keywords` and `categories` follow crates.io's rules (max 5 each, 20
characters per keyword), and neither may be empty:
`clippy::cargo_common_metadata` is enabled and requires both.

`container_image` is asked for the layouts with a binary alone: a library has
nothing to run.

### What `project_kind` selects

| Value       | Layout                                                                  |
| ----------- | ----------------------------------------------------------------------- |
| `bin`       | one package, `src/main.rs`                                              |
| `lib`       | one package, `src/lib.rs` + `tests/`                                    |
| `both`      | one package with both targets; the binary calls into its own library    |
| `workspace` | `crates/<name>` (binary) + `crates/<name>-core` (library), two packages |

`workspace` mirrors the reference project's shape. The root manifest holds
`[workspace.package]`, `[workspace.dependencies]`, the profiles, and the lint
policy under `[workspace.lints]`; each member inherits the policy with
`[lints] workspace = true`. `description` and `categories` stay per member,
because crates.io shows them per package.

Nothing else changes: every CI command and every `just` recipe already passes
`--workspace`, so the same twelve checks cover one package or five.

Three things worth knowing if you pick it:

- `cargo publish --workspace` (the release's `publish-crates.yml`) publishes
  members in dependency order. `just release` bumps the root version *and* the
  version on any dependency line that also carries a `path =` -- those are the
  intra-workspace ones, and a stale one makes publishing fail. A new member is
  new to crates.io: the release that first has it stops its publish job, naming
  it, until its first version is published by hand and its Trusted Publishing
  set.
- A new member that omits `[lints] workspace = true` silently opts out of the
  entire lint policy. There is no warning for it; it is the one footgun the
  workspace layout adds.
- A member's `.crate` holds its own directory only, so each member carries
  copies of the licence texts; a new member needs them too.

### Why the MSRV prompt behaves the way it does

The prompt takes a stable release, `1.<minor>` or exactly `1.<minor>.<patch>`,
between a floor and a ceiling.

The hard floor is **1.90**. Edition 2024 alone would allow 1.85, but a release
publishes with `cargo publish --workspace`, which cargo stabilised in 1.90 --
and `rust-toolchain.toml` pins cargo to the MSRV, there and in CI's publish job,
so an older MSRV would leave a project unable to release. The default is
**1.97**, which is the version at which every lint name in the manifest exists.

The ceiling is the newest stable release the shipped `flake.lock`'s
rust-overlay knows, which the prompt names, and a patch release only if it knows
that one: the flake's toolchain is rust-overlay's, which has no other (`No
stable 1.<minor>.* is available`, `Stable 1.<minor>.<patch> is not available`).
To raise a project's MSRV past it later, `nix flake update` first
([New Rust releases, and the MSRV](#new-rust-releases-and-the-msrv)).

Three of the names are newer than 1.90: `clippy::unchecked_time_subtraction`
arrived in 1.92 (renamed from `unchecked_duration_subtraction`), and
`clippy::inline_trait_bounds` and `clippy::inline_modules` arrived in 1.97.

Choosing an MSRV between 1.90 and 1.96 is supported. The consequence is narrow:

- `cargo check` and `cargo test` are **completely silent** -- rustc ignores
  `clippy::` names it does not recognise, so an older MSRV job sees nothing.
- `cargo clippy` prints `warning[E0602]: unknown lint` for each name it does not
  know and **exits 0**, so it fails no build, including under `-D warnings`.
- You only see those warnings locally, because `rust-toolchain.toml` pins your
  toolchain to the MSRV. The CI clippy job runs on stable, where all three
  names exist.

That behaviour was measured on rustc 1.85.1 with clippy 0.1.85, when 1.85 was
the floor; the floor's toolchain itself has not been re-run since it moved to
1.90 (see its
[verification status](../dev/rust/README.md#verification-status)).

## What you get

```
Cargo.toml            strict lint policy, release profile, crates.io metadata
Cargo.lock            committed, so CI's --locked builds work from commit one
clippy.toml           test code exempted from the panic-family lints
rust-toolchain.toml   pinned to the MSRV
rustfmt.toml          edition 2024, 100 columns
dprint.json           Markdown + TOML formatting, its plugins pinned
                      (`just dprint-update`)
cliff.toml            git-cliff changelog generation, grouped by commit type
cog.toml              cocogitto / Conventional Commits
dist-workspace.toml   cargo-dist config (binaries only)
justfile              `just checks` = the checks CI runs, the flake's last;
                      `just fmt`, `just release`
.githooks/            opt-in (`just install-hooks`): formatting, the shell,
                      the workflows and dprint before a commit, Conventional
                      Commits for the message and the push
flake.nix             Nix: the pinned toolchain and every tool, `nix fmt`, the
                      package, CI's checks as derivations, the OCI image (if
                      chosen)
flake.lock            nixpkgs and rust-overlay, those the template's smoke test
                      runs on
.editorconfig         shfmt's style, for the shell scripts and the git hooks
.cargo/config.toml    Miri flags
.gitignore            target/, Nix's result links, direnv
src/, tests/          starter code that passes the lint set as-is
                      (a workspace puts these under crates/<name>/ and
                      crates/<name>-core/ instead)
AGENTS.md             the lint policy, and what to do when a lint fires
README, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT
LICENSE-MIT / LICENSE-APACHE (a workspace member carries its own copies)
.github/              8 workflows (9 with the image, and its registries
                      script; a library's 9, publish.yml its own, with
                      the release-notes script),
                      dependabot, issue + PR templates, and actionlint's
                      config: dist's release.yml's shellcheck notes are
                      dist's (not a library's)
```

### The lint policy

`[lints.rust]` carries 26 lints (not `unused_crate_dependencies`, which fails a
target for a dependency only another uses). `[lints.clippy]` enables four
groups -- `pedantic` and `nursery` at **deny**, `restriction` and `cargo` at
warn -- and then turns off, one at a time and with a written reason, the lints
that are wrong for a normal crate. `just clippy` and CI run
`cargo clippy --all-targets -- -D warnings`, so warn and deny both fail the
build; the difference shows only in a bare `cargo clippy` (a warning or an
error) -- `cargo check` runs no clippy lint at all.

On top of the groups, the operations that panic, abort or silently truncate are
denied by name: `unwrap_used`, `expect_used`, `panic`,
`panic_in_result_fn`, `unreachable`, `unimplemented`, `todo`, `exit`,
`indexing_slicing`, `string_slice`, `arithmetic_side_effects`,
`unchecked_time_subtraction`, and `as_conversions`.

This is stricter than most crates want, and that is the point of it being a
template: it is far easier to delete a lint you have decided against than to
retrofit one onto a codebase that has been ignoring it for a year. `AGENTS.md`
in the generated project explains each rule and how to opt out at a single site
with `#[expect(lint, reason = "...")]`.

### The CI workflows

- `rust-ci.yml` -- check, test (including doctests), Miri, clippy with `-D
  warnings`, MSRV, `cargo fmt --check`, and a rustdoc build with warnings
  denied. rustup obeys `rust-toolchain.toml` over a toolchain action's default,
  so the stable jobs set `RUSTUP_TOOLCHAIN=stable`, which outranks the file;
  the MSRV job reads `rust-version` out of `Cargo.toml` at run time and fails
  if `rust-toolchain.toml` names another version.
- `rust-audit.yml` -- `cargo audit` on every manifest change and nightly.
- `dependency-review.yml` -- licence and advisory review on pull requests.
- `dependabot-automerge.yml` -- auto-merges patch/minor bumps. Read the setup
  comment at the top: without required status checks it merges things CI never
  gated.
- `style-check-dprint.yml`, `style-check-cocogitto.yml` -- formatting and
  Conventional Commits: every commit (no tag needed), and a pull request's
  title, which a squash merge makes the commit.
- `nix.yml` -- `nix fmt -- --ci` (nixfmt, shfmt and just's own, through
  treefmt: it formats, and fails if that changed a file), then
  `nix flake check`: the flake's clippy, rustfmt, rustdoc and test derivations
  built (the image too, with it), the format, the shell (`just shell-check`:
  shellcheck and shfmt over the scripts, the hooks and the justfile's script
  recipes) and the workflows (actionlint), on x86_64 and aarch64 Linux, and
  every system it declares evaluated.
- `publish-crates.yml` -- the release's crates to crates.io (`cargo publish
  --workspace` at the tag, each version crates.io holds already passed over),
  through Trusted Publishing: no token stored with the repository. dist's
  `release.yml` calls it once the binaries are built and its GitHub release
  made (`dist-workspace.toml`'s `publish-jobs`), so no crate goes out without
  its binaries; a library's `publish.yml` calls it on the tag. With every
  package `publish = false`, it publishes nothing; to drop it, take
  `./publish-crates` out of `publish-jobs` and run `dist init` again (a
  library: its job out of `publish.yml`, and out of the release's `needs`).
- `publish.yml` (a library) -- a release tag runs `publish-crates.yml`, then
  makes the GitHub release, titled and noted as dist's for a binary: the
  version's changelog heading, its link dropped (`1.2.3 - <date>`), the section
  beneath as notes (`.github/release-notes.sh`, python's and typst's too). Its
  "Latest" is the highest release's, never a patch to an older line, which
  dist leaves to GitHub (the newest release).
- `image.yml` (with the image) -- a release tag pushes the binary's OCI image to
  GHCR (and Docker Hub, given its secrets), for amd64 and arm64, after starting
  it; by hand on a branch, a rehearsal that pushes nothing.

Every action is pinned to a commit, its version in a comment; Dependabot moves
them. Its Cargo bumps are `build(deps)` commits, which enter the changelog, and
its action bumps `ci(deps)`, which do not; the flake's inputs move monthly, in
one pull request -- `build(deps)` where `nix build` ships the binary, a
library's `chore(deps)`, merged by a person (a commit's move is no patch or
minor bump). The toolchain is the MSRV's: a `1.<minor>` one moves to
rust-overlay's newest patch of it (`1.<minor>.<patch>` stays), the miri shell's
nightly to its newest. dist follows, where it is used: the flake's `pins`
check fails once the dev shell's moved, and `just pins-update` on the branch
moves `cargo-dist-version` and `release.yml` to it (`dist init`, then `just
fmt`). In this repository, Dependabot moves every template's workflows with
the repository's own, in one pull request
([.github/dependabot.yml](../.github/dependabot.yml)).

### The changelog and `just release`

There is no `CHANGELOG.md` until the first release writes one: git-cliff
generates it from the commits (`cliff.toml`), never by hand. `just changelog
--unreleased` previews the next section. `just release <major|minor|patch>` runs
no tests -- it releases `origin/main`, which CI checks. It refuses a dirty tree,
another branch, a `main` that is not `origin/main`, a version below
Cargo.toml's, an empty release or, for a binary, no dist `release.yml` (`dist
init`); then bumps the version (the workspace's intra-member pins too), writes
the changelog, commits, tags `v<version>` -- the first release the version
Cargo.toml declares, `v0.1.0` as generated, whatever the level -- and pushes the
commit and the tag atomically; the tag's workflow publishes the crates
(`publish-crates.yml`) and makes the GitHub release, its notes the version's
section (dist's `release.yml`, or a library's `publish.yml`). Each heading
links its GitHub compare view, from Cargo.toml's `repository`.

### Nix

`nix develop` gives the toolchain `rust-toolchain.toml` pins (read by
[rust-overlay](https://github.com/oxalica/rust-overlay), so the MSRV is written
once) and every tool `just checks` and `just release` call; `just miri` enters
the flake's nightly `miri` shell itself. `nix fmt` formats the Nix, the shell
and the justfile (nixfmt, shfmt and just's own, through treefmt); `just fmt` all
of it, the Rust, the Markdown and the TOML too. `nix flake check` builds clippy,
rustfmt, rustdoc and the tests offline in the sandbox, and checks the format
(`nix fmt`'s verdict), the shell and the workflows; `nix build` the binary
(every layout but `lib`). The systems are those the flake's `nixos-unstable`
input supports: x86_64 and aarch64 Linux, Apple silicon. The template ships its
`flake.lock`, the nixpkgs and rust-overlay its smoke test runs on, so a project
generated later builds against them, not whatever those branches hold by then;
`nix flake update` moves them, and Dependabot in a monthly pull request.

With `container_image`, the flake has an `image` on Linux:
`dockerTools.buildLayeredImage` of the binary's package -- its closure alone, no
base image and no `/bin/sh`, run as `nobody`, labelled for GHCR.
`nix build .#image` gives the gzipped docker-archive, and the flake's checks
build it; `.#image.stream` streams it uncompressed, sparing the store a second
copy of the closure. `image.yml`, on a release tag, checks the tag against
Cargo.toml's version, streams the image into Docker on amd64 and arm64, starts
it, pushes each, and joins them as `ghcr.io/<owner>/<repository>:<version>`
(`latest` too while it is the highest release), with the job's token -- and to
Docker Hub too, under the same tags, once the variable `DOCKERHUB_USERNAME` and
the secret `DOCKERHUB_TOKEN` are set (`.github/image-registries.sh`; a Docker
Hub failure holds the GHCR release back too); run by hand, it builds and starts
the image on both, pushing nothing (on a tag, it publishes that release again).
The image holds no CA certificates: a binary that verifies TLS against the
system's needs `contents = [ pkgs.cacert ]` and `SSL_CERT_FILE` set in
`config.Env`.

`release.yml` is deliberately **not** included. It is generated from
`dist-workspace.toml` by `dist init`, so run that once in the new project, then
`just fmt` (dist rewrites `dist-workspace.toml` in its own style), and commit
both; a copy shipped here would pin you to whatever `dist` version this
template was built against. It stays dist's: the release's `dist plan` refuses
a `release.yml` that is not what dist writes, so Dependabot leaves it out
(`exclude-paths`), and its actions move with dist: `cargo-dist-version` is
the dev shell's dist, which the flake's `pins` check holds, and `just
pins-update` moves both (`dist init`) once the lock moves it. dist publishes
no crate itself: `dist-workspace.toml` names `publish-crates.yml` among its
`publish-jobs` (a custom job, given `id-token: write` and `contents: read`
alone), which its release runs once the binaries are built and the GitHub
release made, skipped for a pre-release.

The crates.io side, once: crates.io trusts a workflow only for a crate that
exists, so the first release's publish job stops, naming the crates new to it;
their version is published by hand from the tag (`cargo publish
--workspace`), each crate's Trusted Publishing on crates.io names this
repository, the calling workflow -- `release.yml`, or a library's
`publish.yml`: crates.io reads the caller -- and the environment `crates-io`,
and the failed jobs are re-run. The job mints its token even when nothing is
left to publish, so that re-run fails if no Trusted Publishing matches. The
project's `CONTRIBUTING.md` (First steps) says so.

## New Rust releases, and the MSRV

What to change, file by file, in a generated project and in this template.

### In a project

**A new stable release**: nothing, but what its lints find. CI's stable jobs
take it the day it ships, every clippy group on: a lint it adds fails them, and
you fix the code, or `#[expect]` it with a reason (AGENTS.md). The MSRV's
toolchain, the dev shell's and the flake's, stays: a `1.<minor>` channel moves
with the lock to that minor's newest patch, an exact `1.<minor>.<patch>` not at
all. ([The CI workflows](#the-ci-workflows) say both.)

**The MSRV raised** (1.97 to 1.98, say):

1. `Cargo.toml`: `rust-version = "1.98"` -- `[package]`'s, or a workspace's
   `[workspace.package]`, which its members inherit.
2. `rust-toolchain.toml`: `channel = "1.98"`. CI's MSRV job fails while the two
   differ.
3. `README.md` and `CONTRIBUTING.md`: "Rust 1.98 or later".
4. If the flake says `No stable 1.98.* is available`,
   `nix flake update rust-overlay` first (see
   [the MSRV prompt](#why-the-msrv-prompt-behaves-the-way-it-does)).

clippy reads `rust-version`, so a lint that waits for an MSRV -- a newer
standard API to use -- may fire after the raise. Whether a raised MSRV is a
breaking change is your policy: a `!` in its commit (`build!: require Rust
1.98`) puts it under the changelog's breaking changes.

(Each walked through:
[dev/rust/README.md](../dev/rust/README.md#in-this-repository).)

### In the template

**A new stable release**: `locks.yml` (monthly) or `just lock-update rust` moves
`rust/flake.lock` and rewrites the `msrv` prompt's regex and range to the
releases the new rust-overlay knows ([dev/rust/msrv.py](../dev/rust/msrv.py)),
which render-check holds; its pull request's smoke tests run every kind on it.
What is a person's: the smoke test's clippy on stable -- on main's every push
and weekly, and on every pull request touching rust, lock or not -- fails on a
lint the release adds to the starter code. Fix the code, or `allow` the lint in
`rust/Cargo.toml`'s table with the release that brought it (as
`inline_modules`'s), then see whether its lint-name note, and the default below,
still hold.

**The default MSRV moved** (`1.97`): `msrv`'s `default` in
`rust/cargo-generate.toml` and its prompt's "1.97 keeps clippy quiet",
`dev/rust/answers.toml`'s `msrv`, and this page's usage example, table and
[MSRV prompt](#why-the-msrv-prompt-behaves-the-way-it-does) section. The
default is the oldest release that knows every lint name `rust/Cargo.toml`
sets (its lint table names the newer ones); a new default keeps that, or that
section says what moved.

**The floor raised** (1.90, `cargo publish --workspace`'s): `MSRV_FLOOR` in
`dev/rust/msrv.py`; then `just render-check rust` names the regex to write
(`regex = '...'`), and fails until the prompt names the range from the new floor
(`just lock-update rust` writes both, and moves the lock too). By hand:
render-check's base answer (`"msrv": "1.92"` in `dev/rust/render-check.py`),
which must stay one the prompt takes; the text that names the floor, the
prompt's "(1.90: ...)" and the comment below it, and the comments in
`rust/Cargo.toml`, the `rust/justfile` and `publish-crates.yml`; and this page's
[MSRV prompt](#why-the-msrv-prompt-behaves-the-way-it-does) section, whose lint
names newer than the floor are rethought, not a number swapped.
`grep -rn '1\.90' rust dev/rust docs/rust.md` lists the candidates, with the dev
README's records and the prompt's range, which stay or are written for you.

## Developing this template

How the template is checked here, and what was verified of it, is the
maintainers' side: [dev/rust/README.md](../dev/rust/README.md); the repository's
tools, rules and release, [CONTRIBUTING.md](../CONTRIBUTING.md) and
[AGENTS.md](../AGENTS.md).

## Attribution

The lint policy, workflows, `justfile`, `cliff.toml`, `cog.toml` and community
documents are adapted from [`veralvx/imi`](https://github.com/veralvx/imi),
dual-licensed MIT OR Apache-2.0.

Two deliberate divergences from the source: `clippy::as_conversions` is denied
here where imi allows it (imi relies on the pedantic `cast_*` lints instead),
and `pedantic`/`nursery` are at deny rather than warn.

## License

Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](../LICENSE-APACHE) or
  <http://www.apache.org/licenses/LICENSE-2.0>)
- MIT license ([LICENSE-MIT](../LICENSE-MIT) or
  <http://opensource.org/licenses/MIT>)

at your option.
