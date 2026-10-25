# Developing the rust template

The maintainers' side of the rust template; its users' documentation is
[docs/rust.md](../../docs/rust.md). The template is [rust/](../../rust): a
template root, every file a generated project gets, with Liquid in it. What
checks it is here and in the repository's tooling:

```text
dev/rust/render-check.py           every templated file rendered and checked
dev/rust/answers.toml, smoke.sh    `just generate rust` and `just smoke rust`
dev/rust/lock.py, lock.files       `just lock-update rust`, what it may change
dev/rust/msrv.py                   the MSRV, render-check's and lock.py's
.github/workflows/smoke-rust.yml   the end-to-end check, which smoke.yml runs
docs/rust.md                       the users' documentation
```

The rest -- the root justfile and flake, the shared files, the workflows that
check every template -- is the repository's, one set for every template
([CONTRIBUTING.md](../../CONTRIBUTING.md), [AGENTS.md](../../AGENTS.md)). Run
from the root:

```sh
nix develop                # cargo-generate, just, the linters, Python
just render-check rust     # below; with no template named, every template's
just smoke rust workspace  # generated, then its own checks (each kind)
just generate rust bin     # into target/rust/bin/demo, to look at
just lock-update rust      # the lock moved, the msrv prompt and dist with it
just checks                # every template's render-check, sync, no tool
                           # version by hand, the shell, the workflows,
                           # dprint, cog, the flake's last
just format                # every formatter the checks hold, `nix fmt` last
```

`just smoke rust <kind>` needs Nix: the generated project's checks run in its
own flake's dev shell, on the lock the template ships, which they must leave as
it is.

`just checks` at the root runs every template's render-check with the
repository's own checks:
[CONTRIBUTING.md](../../CONTRIBUTING.md#development-workflow) lists them.

## render-check

`just render-check rust` installs `dev/requirements.txt` into `.venv` (Python
3.11+, for tomllib) and runs `dev/rust/render-check.py`, which renders every
templated file for all 48 combinations of `project_kind` × the image (asked of a
layout with a binary; a `lib` given it unasked or not) × `license` ×
empty-or-present email, then checks that nothing is left unexpanded, that the
result still parses as TOML/YAML/JSON -- and as Nix, when `nix-instantiate` is
on `PATH` -- and that the manifest matches the chosen layout. It also guards
config invariants that otherwise fail silently:

- **Every referenced variable is declared.** When Liquid meets an unknown
  variable, cargo-generate catches the error, substitutes an empty string and
  re-renders. A misspelled placeholder therefore does not fail -- it renders as
  nothing, and a "no leftover `{{`" check cannot see it.
- **No file on the `exclude` list contains a placeholder**, since those files
  are copied verbatim and would ship the placeholder unexpanded.
- **Every templated file is UTF-8**: cargo-generate aborts on one that is not,
  so a binary file must be excluded.
- **Every `ignore` entry is a literal path that exists.** `ignore` is not
  glob-matched: cargo-generate joins each entry onto its working copy of the
  template and removes it -- before rendering, so an entry spells a path as the
  template does, `crates/{{project-name}}-core/LICENSE-MIT` included. A pattern
  like `tests/**` resolves to nothing and silently ships the file that was meant
  to be dropped.
- **The workspace members' licence copies equal the root's**, byte for byte.
- **crates.io publishing is each kind's**: `publish-crates.yml` in every one;
  `dist-workspace.toml` naming it among dist's `publish-jobs`, given
  `id-token: write` and `contents: read`, where dist releases; a library's
  `publish.yml`, which calls it and makes the GitHub release, and the
  `release-notes.sh` it reads, there alone.
- **The shipped `flake.lock` and the `msrv` prompt agree**, when `nix` is on
  `PATH` (CI's checks.yml has it): the lock is every rendered `flake.nix`'s,
  nothing to relock; and the `msrv` regex takes exactly the stable releases its
  rust-overlay knows from 1.90 -- `1.<minor>`, or a release itself -- and
  nothing else, as rust-overlay builds no other: it is the regex they ask for,
  which render-check prints on a mismatch, and the prompt names the range. This
  fetches rust-overlay at its locked revision; nixpkgs it does not, the smoke
  test's Nix job builds with it.

The second check guards the sharpest edge in this template. These files are
copied **verbatim** and never processed by Liquid:

- `.github/workflows/**` -- GitHub Actions expressions. Some use `||` inside an
  interpolation, which is not valid Liquid and aborts generation outright.
- `cliff.toml` -- git-cliff's Tera templates. Its conditionals happen to *be*
  valid Liquid, so they would be silently evaluated and the changelog config
  quietly gutted. This one fails without an error message.
- `justfile` -- just's own interpolation shares Liquid's double-brace syntax.
- `flake.lock` -- the inputs, locked: copied as Nix wrote them.

Anything project-specific added to the first three must be derived at run time
instead, the way the MSRV job derives its toolchain version and `just changelog`
the repository.

The checks every template shares are [dev/render_core.py](../render_core.py)'s
-- each prompt's name (none cargo-generate reserves) and default (against its
choices and its regex), the generation answers (`answers.toml`) against the
prompts, the `ignore` paths and the hooks, the variables and the encoding, the
exclude list, every case rendered and parsed (`Cargo.lock` as TOML,
`flake.lock` as JSON) -- and `dev/rust/render-check.py` adds rust's own on
top. Each check runs on its own: one that fails, or cannot run because a file
before it did not render, is reported, the rest still run, and the exit status
is 1.

## The lock

`rust/flake.lock` pins the generated flake's nixpkgs and rust-overlay, so a
project generated next month builds with what the smoke test runs on. The
template's `flake.nix` holds Liquid, so the lock is made in a generated project
and copied back. `just lock-update rust` ([dev/rust/lock.py](lock.py)) does it,
the msrv regex and range included (render-check's own, from [msrv.py](msrv.py)),
and `dist-workspace.toml`'s `cargo-dist-version`, the new dev shell's dist (a
project's `pins` check holds the two equal), then runs render-check; by hand:

```sh
just generate rust bin
# every input; `nix flake update rust-overlay` moves that one alone
(cd target/rust/bin/demo && nix flake update)
cp target/rust/bin/demo/flake.lock rust/flake.lock
just render-check rust   # names the msrv regex the new rust-overlay asks for
```

Then the regex it names goes into `cargo-generate.toml`'s `msrv`, the range into
its prompt, and the shell's dist (`nix develop --command dist --version` in the
project) into `dist-workspace.toml`. Either way, `just smoke rust <kind>` for
each kind is what proves it (in `locks.yml`, its pull request's CI). Every
kind's `flake.nix` has the same inputs, which render-check holds: one lock
serves them all.

## The shared files

What rust shares with the other templates or the root is `just sync --check`'s:
the files [shared/manifest.toml](../../shared/manifest.toml) names, each copy
byte for byte its original and executable alike, and dprint's plugins and TOML
settings, every template's. Change the original, then `just sync`. rust's
`flake.lock` is its own.

## CI

- `checks.yml`, on every pull request, every push to `main`, weekly and by
  hand: `just sync --check`, `just tool-versions-check` and every
  render-check.
- `smoke.yml`: `smoke-rust.yml` when a run needs it -- a pull request touching
  `rust/`, `dev/rust/` or the workflow itself, or anything but another
  template's own files and `docs/`; every push to `main`, weekly and by hand --
  behind one gate, `smoke-gate`. It puts all 24 answer combinations through the
  actual `cargo-generate`, the floor (0.25.0; each manifest parsed, each licence
  file where its choice puts it, `dprint check`); three names the name hook
  refuses; for each `project_kind`, with the dev shell's tools at the lock's
  versions (`dev/nix-tools.sh`), a generated project's git hooks installed and
  shown to refuse an unformatted file, a bad message and a pushed revert, then
  the project put through its own `just` recipes (clippy on the pinned MSRV and
  on stable, Miri on nightly, the shell, actionlint, `cargo audit`, `cog
  check`), `dprint check`, `just changelog` and `cargo package`, and for the
  workspace two `just release`s against a bare remote; and each flake, generated
  by the lock's cargo-generate, through `nix flake check` and, but for lib, `nix
  build`, `just pins-update` moving a planted `cargo-dist-version` back, `just
  fmt` changing nothing, the image run where there is one. A template whose
  output does not compile is worse than no template, and this is the only thing
  that proves it does.
- `nix.yml`: the root flake (`just nix`): its format, the shell (every
  template's) and the workflows (every template's).
- `style-check-dprint.yml`, `style-check-cocogitto.yml`: dprint and the commits.
- `dependabot-automerge.yml`: Dependabot's patch and minor bumps (the actions,
  render-check's packages) merged once the required checks pass.
- `locks.yml`, monthly and by hand: `just lock-update rust` -- the lock, as
  [The lock](#the-lock) makes it, the msrv prompt and `cargo-dist-version` --
  proposed as a pull request on `locks/rust`, whose description names each
  dev-shell tool that moved and what is left to a person.
- `dprint-plugins.yml`, monthly and by hand: `just dprint-update` -- every
  `dprint.json`'s plugins, this template's with them, to their newest, the
  root formatted by them -- proposed as a pull request on `dprint/plugins`.
- `release.yml`: a release tag's GitHub release, every template's at once (`just
  release` cuts it: the changelog, the tag `v<version>`), with every tracked
  file as a tarball, which cargo-generate generates from, unpacked, with
  `--path`.

## Verification status

### In this repository

`rust/` was rust-template's `template/` at its last published commit, `711f5c4`,
when it moved here; once the move was complete, every project generated from it
was byte for byte -- contents and modes -- that commit's, but for the comments
of two workflows, reworded as typst's: `style-check-dprint.yml` and
`dependabot-automerge.yml`, the latter made exact. That was proved by generating
every kind × option the smoke test covers (28 projects, and the 3 names it
refuses) from both repositories, by `--path` and by `--git` from a branch and
from a tag; what changed since is this repository's history. Also run here:

- **render-check** passes, and still catches each defect planted in it: a
  misspelled variable, a glob in `ignore`, a regex refusing its default,
  Liquid in an excluded file, invalid YAML, broken Liquid, an answer in
  `answers.toml` no prompt takes or one its prompt refuses. The shared files'
  drift is `just sync --check`'s, which fails on each copy changed (a byte
  appended or changed in place), its executable bit flipped or the copy
  missing, any line of the three shared recipes changed, a dprint plugin
  apart, and Liquid in a `[root]` original where cargo-generate itself renders
  it.
- **smoke-rust.yml's steps**: the combinations and the refused names, each
  kind's generation, and the Nix jobs' generation by nixpkgs' cargo-generate
  (0.25.0 without its `git` feature), each project equal to the released
  binary's. Every generation runs with no network (`dev/offline.sh`), proved
  as the runner's user, through sudo, by both builds of cargo-generate: each
  project the same as with it.
- **The root's recipes**: every kind `just generate rust` makes equals what
  smoke-rust.yml's generate and Nix jobs make; `just smoke rust` passes for
  every kind with a stand-in `nix`: each `nix develop` the dev shell's own
  packages at their versions, and nothing else (but git, awk, valgrind, Rust's
  patch release and stdenv's other tools, this machine's), so the project's
  `just checks` -- Miri's tests run natively, as its nightly cannot be had here
  -- and `just fmt` run in the dev shell (CI's generate job runs the same
  recipes on rustup's toolchains), on the lock the template ships, left as it
  is, and the project left clean; `nix fmt` and `nix flake check` were left to
  CI.
- **The flake**, every kind's, on the lock it ships: it evaluates on every
  system, its `format`, `shell` and `workflows` checks (and, with dist, `pins`)
  pass as their derivations run them, git and awk aside, and `nix flake lock`
  changes nothing. The lock was written from its inputs' sources -- nixpkgs at
  the root lock's revision, rust-overlay at its newest, fetched by git, as
  GitHub's archives are unreachable here -- and is byte for byte what `nix flake
  lock` writes; every MSRV at the cap's edges (1.90, 1.99.1) evaluates, and
  those past it (1.99.2, 1.100) do not.
- **New Rust releases, and the MSRV**
  ([docs/rust.md](../../docs/rust.md#new-rust-releases-and-the-msrv)), each
  procedure as written: a generated bin's and workspace's MSRV raised
  from 1.97 to 1.98 (the four files; CI's MSRV comparison agreeing); on the
  bin, the flake's dev shell giving `rust-minimal-1.98.1` against the shipped
  lock's rust-overlay, git-fetched, and `No stable 1.100.* is available` for a
  release it does not know; msrv.py's regex and range, from that rust-overlay's
  stable manifests, equal to the shipped prompt's, and moving with
  `MSRV_FLOOR`. Not run: cargo on 1.98, whose toolchain this machine cannot
  download.

### In rust-template, before the move

The template was driven end to end with the real tooling, not reasoned about.
With **cargo-generate 0.25.0**, **rustc / clippy 1.97.0** (the default MSRV),
**just 1.58.0**, **cocogitto 7.0.0**, **git-cliff 2.13.1**, **cargo-audit
0.22.2** and **dprint 0.61.0 with the markdown 0.26.0 and TOML 0.9.0 plugins**,
all 24 combinations -- `bin`, `lib`, `both` and `workspace`, × the three
licences, × email present and absent -- generate and, after their first commit,
pass:

```
just --fmt --check --unstable
just cargo-check test clippy fmt-check docs-check dprint-check cog audit
just changelog --unreleased
cargo package --workspace --locked
```

Also confirmed by running it, not by reading it:

- The release recipe, against a bare remote: the first `just release minor`
  tags `v0.1.0` and writes the changelog; a second, after a `build(deps)` and a
  `fix!` commit, bumps to `v0.2.0` -- Cargo.toml, Cargo.lock and the
  intra-workspace pin -- groups the breaking change first, leaves the release
  commit out, links the compare view, and pushes commit and tag together; it
  refuses an empty release, a dirty tree, an unknown level and an unpushed
  `main`. `just checks` still passes after it.
- Every conditional drops exactly the right files, for all four layouts and all
  three licence choices, a workspace member's licence copies included.
- The workspace's hand-written `Cargo.lock` is byte-identical to what
  `cargo generate-lockfile` produces, which is what makes `--locked` work from
  the first commit.
- The workspace lint policy is genuinely inherited: injecting `v[0] + 1` into a
  member fails clippy with `indexing may panic` and `arithmetic operation that
  can potentially result in unexpected side-effects`.
- `cargo publish --workspace --dry-run` packages and "uploads" the members in
  dependency order.
- The flake of every layout evaluates on all three systems (`nix flake check
  --no-build --all-systems`, Nix 2.34.6, nixpkgs-unstable of 2026-10-06,
  rust-overlay of 2026-10-07) and is `nixfmt`-clean; this is how x86_64-darwin,
  which nixpkgs-unstable has dropped, was found and removed.
- The image prompt: all 42 combinations with it (`bin`, `both` and `workspace`
  with the image or without, `lib`, × licence × email) generate and pass dprint,
  nixfmt, actionlint and shellcheck, and their flakes evaluate on all three
  systems; the image, its check and its workflow exist exactly where chosen, on
  Linux alone. One per layout and choice passes the justfile's checks above, the
  changelog and `cargo package`. The package's meta carries its licence and
  homepage.
- Docker Hub: image.yml's push and multi-architecture steps, run against a
  recording `docker`, make with no Docker Hub settings the very calls they made
  before it; with both, each architecture pushed to both registries and each
  index made from its own; with one alone, a name Docker would refuse, or a
  dotted repository name, they stop after GHCR's login, before any push.
- The answer validation refuses an MSRV below 1.90, a `"` or `\` in the
  description or author, a sixth keyword and an uppercase category; the name
  hook refuses `3d-tool`, `fn`, `self`, `gen` and `async`.
- `cargo`'s `[env]` reaches a target runner, which is how Miri's runner gets
  `.cargo/config.toml`'s `MIRIFLAGS`.
- `just test` fails, rather than skipping the doctests, when `jq` is missing;
  `just valgrind` (valgrind 3.22) runs clean on `both`, and a target it fails
  keeps its own report.
- The smoke test's combinations and release steps, run locally as written
  (`just miri` standing in as a native `cargo test`): the 24 generations with
  their licence files and `dprint check`, and the two releases with their tags,
  version and compare link, the empty third refused.
- The git hooks, run as the smoke test's step does, for `bin`, `lib` and
  `workspace`: an unformatted file, a message cog rejects and a pushed revert
  refused, each for that reason, and a clean push accepted. The two releases
  then commit and push through them, the tag included; a release commit a hook
  refuses -- the first, too -- leaves a clean tree and no tag. A merge commit
  passes whatever its message, as CI ignores merges.
- **The shell**: for each layout, with the image or without, the generated
  project's `just shell-check` passes, as does its formatter (`nix fmt`), run as
  treefmt 2.6.0 with the same settings and `--ci`, and the flake's `shell`
  check, run as its derivation runs it in a namespace without `/usr/bin/env`;
  each flake, nixfmt-clean, evaluates on all three systems with its new
  `format` and `shell` checks (rust-overlay stood in for by a stub, as its
  source is out of this environment's reach). Reformatting the recipes to the
  justfile's 4-space style changed their layout alone -- shfmt's minified
  output of each is unchanged -- but for `valgrind`'s two quoted options and
  `release`'s portable rewrite of `Cargo.toml`, which a workspace's two
  releases then ran through (the intra-workspace pin moved to `0.2.0`).
- **rust-template's own tooling**: render-check's copies caught each planted
  drift; `just shell-check`, `just template-shell-check`, actionlint and dprint
  passed; its flake evaluated on all three systems; its history passed `cog
  check` (its one commit that did not, "add dotted files", reworded as a
  Conventional Commit).
- The workflows pass actionlint 1.7.12 with shellcheck 0.11.0.
- **`just fmt`**, in rust-template and in each layout generated, with `nix fmt`
  emulated (its formatter's settings, evaluated, run by treefmt 2.6.0): it
  changes nothing on what generation wrote, and, in a lib project, puts back
  each planted drift -- Rust rustfmt would reformat, a justfile recipe line, a
  script recipe shfmt would reformat (`just shell-check`'s verdict), Markdown,
  the Nix. `nix fmt -- --ci` fails on a misindented recipe line, in
  rust-template's either justfile and in a generated project's.
- **actionlint in the generated projects**: `just actionlint` and the pre-commit
  hook pass in each layout, and the hook refuses a workflow with an unquoted
  variable in a `run:` script; the flake's new `workflows` check, run as its
  derivation runs it (a copy in a repository of its own, no `/usr/bin/env`),
  passes for each; the smoke test's actionlint step, run as written, installs
  1.7.12 and refuses an archive whose SHA-256 is not the pinned one.

rust-template's smoke test on GitHub, at 5061c45 (2026-10-09), covered what
this environment cannot: every layout built and checked under Nix (`nix flake
check`, `nix build`), the `bin` and `both` images loaded into Docker and run,
their user and labels read; clippy on stable 1.99 and `just miri` on nightly
1.101 passing on the starter code; dprint's plugins fetched from
`plugins.dprint.dev`. Its one failure was its own: the `workspace` image was
expected to print `bin`'s greeting, where its `main.rs` calls the library as
`both`'s does -- fixed, not yet re-run.

### Not covered

What neither covers:

- **The MSRV floor's toolchain** (1.90): the smoke test generates with 1.97.
- **cargo-dist** (`dist init`), and the generated project's own workflows on
  GitHub -- its GHCR and Docker Hub pushes and its crates.io publish included:
  they are linted, not run (the publish job's selection was run against a
  stubbed crates.io, and its dry run, `--exclude` of a member crates.io holds
  and a `publish = false` member included, against crates.io; a library's
  release step on the tags of two `just release`s and an older line's patch,
  with a recording `gh`).
