# Contributing to `{{project-name}}`

Thank you for considering contributing to `{{project-name}}`!

A project just generated from its template: start at
[First steps](#first-steps), under Maintainers.

## Prerequisites

To build and test `{{project-name}}` locally you will need either **Nix** --
`nix develop` gives every tool below at the versions `flake.lock` pins, the
toolchain read from `rust-toolchain.toml`, and `just miri` its nightly shell --
or, installed yourself:

- **Rust {{msrv}} or later** (pinned in `rust-toolchain.toml`, so `rustup` will
  fetch it automatically the first time you build).
- **[just](https://github.com/casey/just)** -- the command runner this project's
  automation is written in.
- **[jq](https://jqlang.org/)** -- `just test` asks `cargo metadata` through it
  whether there are doctests to run.
- **[dprint](https://dprint.dev/)** -- formats the Markdown and TOML.
- **[ShellCheck](https://www.shellcheck.net/)** and
  **[shfmt](https://github.com/mvdan/sh)** -- the shell's linter and formatter
  (its style is `.editorconfig`'s); `just shell-check` reads the justfile's
  recipes through jq.
- **[actionlint](https://github.com/rhysd/actionlint)** -- lints the workflows
  (and, through ShellCheck, their `run:` scripts).
- **[cocogitto](https://docs.cog.tools/)** (`cog`) -- enforces Conventional
  Commits.
- **A nightly toolchain with the `miri` component**
  (`rustup toolchain install nightly --component miri`). `just checks` runs
  `cargo +nightly miri test`, and so does CI.
- **cargo-audit** (`cargo install cargo-audit`), for the dependency advisory
  scan.
- **[git-cliff](https://git-cliff.org/)**, for maintainers: `just changelog`
  and `just release` write the changelog with it.
- **[Nix](https://nixos.org)** for the last of `just checks`, the flake's
  formatter and checks (`just nix`).

The nightly Miri toolchain and cargo-audit are easy to miss: without them
`just checks` fails on tooling rather than on anything wrong with your change.

## Setup

1. Fork this repository and create your branch from `main`.
2. Clone your fork locally:

```sh
git clone https://github.com/<you>/{{project-name}} && cd {{project-name}}
```

3. Optionally, `just install-hooks`: `.githooks/` then checks formatting, the
   shell, the workflows and dprint before each commit, the message as a
   Conventional Commit, and every pushed commit's message before a push --
   what CI would refuse, minutes earlier. They need `just`, `cargo`, `jq`,
   `shellcheck`, `shfmt`, `actionlint`, `dprint` and `cog` on `PATH` (inside
   `nix develop`, with Nix); `git config --unset core.hooksPath` turns them
   off.

## Guidelines

Before you start, read [AGENTS.md](AGENTS.md). It documents the lint policy --
which lints are on, why, and what to do when one fires -- and applies to human
and AI-assisted contributions alike.

The short version: this crate denies the operations that can panic, abort or
silently truncate (`unwrap`, `expect`, `panic!`, indexing, unchecked
arithmetic, `as`, `exit`). Reach for the total counterpart, or annotate the site
with `#[expect(lint, reason = "...")]` explaining why the lint is wrong there.

## Testing Strategy

- **Pure functions:** isolate logic from side effects wherever possible and
  cover it with unit tests.
- **Regressions:** if you are fixing a bug, include a test that reproduces the
  previous failure state.
{% if project_kind == "workspace" -%}
- **Public API:** `crates/{{project-name}}-core/tests/public_api.rs` is an
  integration test, so it sees only what a downstream dependent sees. Anything
  you intend to publish should be reachable from there.
- **Where logic goes:** in `crates/{{project-name}}-core`, not in the binary.
  Code in `crates/{{project-name}}` can only be exercised by running the
  process; code in the core crate can be unit-tested directly.
{% elsif project_kind != "bin" -%}
- **Public API:** `tests/public_api.rs` is an integration test, so it sees only
  what a downstream dependent sees. Anything you intend to publish should be
  reachable from there.
{% endif -%}
- **Doctests:** examples in rustdoc are compiled and run. `--all-targets` skips
  them, which is why `just test` runs `cargo test --doc` as a separate step
  whenever the package has a library target.

## Development Workflow

1. The [Conventional Commits](https://www.conventionalcommits.org/)
   specification is enforced on every commit.
2. Run the automated checks locally. This repository includes a `justfile` that
   mirrors the GitHub Actions pipeline:

```sh
just checks
```

That runs twelve recipes in order: `cargo check`, the test suite, Miri,
`cargo clippy` with warnings denied, `cargo fmt --check`, a docs build with
warnings denied, the shell (`just shell-check`), the workflows (actionlint),
`dprint check`, `cog check`, `cargo audit`, and last the flake (`just nix`:
`nix fmt -- --ci`, every system evaluated, this one's checks built) -- the set
the workflows under `.github/workflows/` run, here on the toolchain
`rust-toolchain.toml` pins (Miri on nightly). CI's Rust jobs (check, test,
clippy, fmt, docs) run on the latest stable, where a lint newer than the MSRV
can still fire; the pinned toolchain runs there in the MSRV job (check, test)
and in `nix.yml`, the flake's formatter and checks -- clippy, rustfmt, rustdoc
and the tests, the format, the shell and the workflows in the Nix sandbox --
which `just nix` runs locally.

`just fmt` writes what the format checks ask for: rustfmt's, shfmt's, the
justfile's, dprint's, and last `nix fmt`'s (without Nix, it stops there).

## Creating a Pull Request

1. Ensure your code passes `just checks` locally.
2. Open a Pull Request against the `main` branch, titled as a conventional
   commit: a squash merge makes the title the commit, and so a changelog entry
   (CI checks it).
3. In your PR description, outline the problem you are solving. Link the
   relevant issue (e.g. `Fixes #123`), if any.
4. Wait for a maintainer to review your code.

## Maintainers

### First steps

`cargo-generate` initialises a git repository here but does not commit
anything, so the first commit is yours to make -- and `cog check` (run by
`just checks` and by CI) requires it to follow
[Conventional Commits](https://www.conventionalcommits.org/). nixpkgs' build of
`cargo-generate` makes no repository, so `git init -b main` first if `.git` is
missing:

```sh
git add .
git commit -m "chore: initial commit from template"
```

With [Nix](https://nixos.org), `nix develop` enters a shell with the pinned
toolchain and every tool above, at the versions `flake.lock` pins.

Then, in whichever order suits you:

- Push to `https://github.com/{{github_username}}/{{project-name}}`.
- Enable the repository settings the auto-merge workflow needs -- they are
  listed at the top of `.github/workflows/dependabot-automerge.yml`. Without
  required status checks, it merges bumps that CI never gated.
- Enable private vulnerability reporting (Settings → Code security): it is off
  by default, and [SECURITY.md](SECURITY.md) and the issue form point to it.
{% if project_kind != "lib" -%}
- Run `nix develop --command dist init` (the dev shell's dist, the version the
  flake's `pins` check holds; `just pins-update` does it once the lock moves
  dist) to generate `.github/workflows/release.yml` from
  `dist-workspace.toml`, then `just fmt` (dist rewrites that file in its own
  style), and commit both. The release refuses a `release.yml` dist did not
  write, so leave it to dist: Dependabot does.
{% endif -%}
- After the first `just release` ([Releasing](#releasing)): crates.io trusts a
  workflow only for a crate that exists, so its publish job stops, naming the
  crates new to it. Publish that version by hand, from its tag:
  `git checkout v<version>`, `cargo login` (a crates.io API token: Account
  Settings, API Tokens, publish-new and publish-update; crates.io asks a
  verified email), `cargo publish --workspace` -- a version on crates.io is
  there for good.
- Then, on crates.io, {% if project_kind == "workspace" %}each{% else %}the{% endif %} crate's Settings, Trusted Publishing: this
  repository, the environment `crates-io`, the workflow {% if project_kind == "lib" %}`publish.yml`.{% else %}`release.yml`
  (dist's, which calls `publish-crates.yml`: crates.io reads the caller).{% endif %}
- Once it is set, re-run the release's failed jobs: the publish job mints its
  token, which fails without Trusted Publishing, and passes over what crates.io
  has. Every release after publishes from CI. If you limit the `crates-io`
  environment's deployments (Settings → Environments), admit the tags `v*`.
{% if project_kind != "lib" and container_image -%}
- After the first release, make the image public: GHCR publishes a new package
  as private (its page, Package settings → Change visibility).
- To publish the image to Docker Hub too: create its repository there, then set
  the repository variable `DOCKERHUB_USERNAME` and the secret `DOCKERHUB_TOKEN`
  (an access token that writes) -- and the variable `DOCKERHUB_REPOSITORY`
  (`namespace/name`) unless it is `<username>/<this repository's name>`. A
  Docker Hub failure holds the GHCR release back too.
{% endif -%}
- Run `just checks` once to confirm your toolchain is complete: a step that
  stops on a missing command names it -- `just`, `jq`, `shellcheck`, `shfmt`,
  `actionlint`, `dprint`, `cog`, `cargo-audit`, the nightly Miri component or,
  last, Nix ([Prerequisites](#prerequisites) lists them; `nix develop` has
  the rest).
- `just install-hooks`, if you want git to run the quick checks before each
  commit and push ([Setup](#setup)).
- Read [AGENTS.md](AGENTS.md) before writing code: the lint policy denies
  `unwrap`, `panic!`, indexing, unchecked arithmetic and `as` casts, and it is
  much less surprising if you know that going in.
- Make the project yours: the code, the tests, the README (the crate's page on
  crates.io), {% if project_kind == "workspace" %}the keywords in the root's `Cargo.toml`, and each member's
  description and categories in its own{% else %}the description, keywords and categories in `Cargo.toml`{% endif %}.

### Releasing

`just release <major|minor|patch>`, from a clean `main` equal to `origin/main`,
CI green on it: the recipe runs no tests. It bumps the version, writes
`CHANGELOG.md` with git-cliff, commits, tags `v<version>` (the first release
the version Cargo.toml declares, whatever the level), and pushes the commit and
the tag together.
{%- if project_kind == "lib" %} The tag's `publish.yml` runs `publish-crates.yml`:
`cargo publish --workspace` to crates.io, each version crates.io holds already
passed over, so a re-run completes a partial publish; then it makes the GitHub
release, its notes the version's section of the changelog.
{%- else %} The tag's `release.yml` (dist's) builds the binaries and
makes the GitHub release, then runs `publish-crates.yml`: `cargo publish
--workspace` to crates.io, each version crates.io holds already passed over,
so a re-run completes a partial publish.
{%- if container_image %} The tag runs `image.yml` too: the
binary's OCI image to GHCR, from the flake's `image` (`nix build .#image`
builds it here).
{%- endif %}
{%- endif %}

Before the first one:

- crates.io: the first release's publish job stops on the crates new to it,
  whose first version you publish by hand, set their Trusted Publishing, then
  re-run the failed jobs ([First steps](#first-steps)).
{%- if project_kind != "lib" %}
- dist's `release.yml` committed ([First steps](#first-steps)): the release
  refuses to start without it, as it builds what `cargo binstall` fetches.
{%- endif %}
- The commits since the last tag must hold a change a user meets (`feat`,
  `fix`, `perf`, `build`...): `chore`, `ci` and `style` alone make no release.
- The release pushes to `main` directly: with "Require a pull request before
  merging" on, the maintainer cutting it needs the rule's bypass. A refused
  push leaves the commit and the tag local -- push them again with
  `git push --atomic origin main v<version>` once allowed.

## Updating the tools

The tools `nix develop` gives -- nixpkgs', and the toolchain rust-overlay builds
from `rust-toolchain.toml` -- move with `flake.lock`: Dependabot moves the
flake's inputs in a monthly pull request; by hand, `nix flake update`, then
`just checks`.{% if project_kind != "lib" %} When
the flake's `pins` check fails, naming `cargo-dist-version`, run
`just pins-update` on that branch (`nix develop --command just pins-update`):
`dist init` with the dev shell's dist (another is refused) moves the version and
rewrites `release.yml`, then `just fmt`; commit both.{% endif %}
