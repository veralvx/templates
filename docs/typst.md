# The typst template

A [`cargo-generate`](https://github.com/cargo-generate/cargo-generate) template for a
[Typst](https://typst.app) package -- a library, or a template package `typst init` starts projects
from -- that starts with the whole toolchain wired up and with
[Typst Universe](https://typst.app/universe)'s rules already kept: tests by
[tytanic](https://typst-community.github.io/tytanic/) (visual references, assertions, the template
as initialized), formatting by typstyle, linting by tinymist, the bundle linted by the same
`typst-package-check` typst/packages runs on a submission, every warning an error, the README's
examples compiled, the oldest Typst declared tested in CI, Conventional Commits, changelogs by
git-cliff, a release recipe that shows every step, a publish workflow that prepares the Universe
submission, a Nix flake whose tools, at its lock's versions, are CI's, and a `justfile` that runs
locally what CI runs remotely.

It is one of [this repository](../README.md)'s templates, the counterpart of [python](python.md)
and [rust](rust.md). See [Attribution](#attribution).

## Usage

```sh
cargo install --locked cargo-generate   # 0.25 or later (the template refuses older)
cargo generate --git https://github.com/veralvx/templates typst
```

The trailing `typst` is the folder that holds this template: the repository holds every template,
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
nix run nixpkgs#cargo-generate -- generate --path templates typst
cd my-package && git init -b main   # the name you gave
```

Everything can be answered non-interactively, which is what the smoke test does:

```sh
cargo generate --git https://github.com/veralvx/templates typst \
  --name my-package --silent \
  -d project_kind=package \
  -d description="Draw tidy timelines from a list of events." \
  -d author_name="Jane Doe" \
  -d author_email=jane@example.com \
  -d github_username=jane \
  -d license="MIT OR Apache-2.0" \
  -d compiler=0.14.0 \
  -d keywords="timeline, chronology" \
  -d categories="visualization" \
  -d disciplines=""
```

Then, in the new project, the first steps its `CONTRIBUTING.md` gives (Maintainers, First steps):
the first commit, the repository's settings, the fork that receives submissions.

### If generation fails

`cargo-generate` creates the destination directory *before* it validates any answer, and leaves it
behind when validation rejects one. The retry then stops with
`Target directory already exists, aborting!` -- remove the empty directory and try again.

### What needs the network

Generating needs none: from a clone (`--path`), every kind generates with no network at all, as
the smoke test generates it; `--git` fetches the template first. After it:

- dprint, on its first run (`just dprint-check`, the hooks): its plugins, `dprint.json`'s URLs;
  then from its cache.
- typst-package-check: built from source by `nix develop` (crates.io), or pulled as its image
  (`ghcr.io`) as CI runs it. `just package-check` itself runs offline; `just online=true
  package-check` checks the repository's URL too, as `publish.yml` does.
- `nix develop` and the flake's checks: the lock's inputs and its tools, from GitHub and Nix's
  binary cache, unless the store holds them.

Typst itself needs none: the package imports no other, so its tests, the README's examples and
the template compile offline; git and the commit-message check (`cog`) need none either.

## What you are asked

| Prompt            | Default                     | Goes into                                                       |
| ----------------- | --------------------------- | --------------------------------------------------------------- |
| *(project name)*  | —                           | the package's name, the repository, every `@preview/` import    |
| `project_kind`    | `package`                   | `package` or `template` -- see below                            |
| `description`     | one per kind                | `typst.toml`'s `description`, the README                        |
| `author_name`     | —                           | `authors` (`Name <@github-user>`), the licence's copyright line |
| `author_email`    | *(empty)*                   | the code of conduct's contact -- omitted if blank               |
| `github_username` | —                           | the repository's URLs, `authors`' handle, security advisories   |
| `license`         | `MIT OR Apache-2.0`         | `license`, the licence files, the README -- see below           |
| `compiler`        | `0.14.0`                    | `compiler`, the oldest Typst CI compiles the package on         |
| `keywords`        | *(empty)*                   | `keywords` (comma-separated)                                    |
| `categories`      | none; `report` (a template) | `categories`, at most three of Universe's; a template needs one |
| `disciplines`     | *(empty)*                   | `disciplines`, of Universe's list                               |

Every answer is validated at the prompt, against Universe's rules where it has one: its 19
categories and 39 disciplines, a GitHub handle as its bundler checks it in `authors`, nothing that
would break a TOML string or the `Name <@handle>` form, a `compiler` that is a released Typst from
0.12 (the oldest the checks are verified on) to the lock's. The project name is checked before
any file is written -- only the empty directory above is
([typst/validate-name.rhai](../typst/validate-name.rhai), a pre hook): kebab-case, a letter first,
and no "typst", as Universe's naming rules ask -- and, as no regex can say it, a description without
"Typst" and a GitHub handle of at most 39 characters. What a hook cannot judge -- that the name is
not the obvious, canonical one for what the package does -- is typst/packages' review.

### What `project_kind` selects

| Value      | What it is                                                                                                                                           |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `package`  | a library: `greet` in `src/greet.typ`, a visual test and an assertion test                                                                           |
| `template` | a template package: `report` in `src/report.typ`, which `template/main.typ` applies with a show rule, as Universe asks; `[template]` in `typst.toml` |

Either way, `src/lib.typ` is the entrypoint and defines nothing: what it imports is the public API
(Typst has no `pub`), the pattern typst/packages recommends.

### The licence

Universe takes an OSI-approved licence (or CC-BY, CC-BY-SA, CC0) and a file named `LICENSE`, or one
the README links. `LICENSE` is always there: the licence's text, or -- for `MIT OR Apache-2.0` -- a
pointer to `LICENSE-MIT` and `LICENSE-APACHE` beside it, as Universe's own dual-licensed packages
do.

A template package's `template/` is what users copy and make their own, so Universe asks that they
may use and share what they make from it without restriction, and recommends MIT-0 for it. Here it
is always MIT-0: `license` becomes `<choice> AND MIT-0` (`(MIT OR Apache-2.0) AND MIT-0` for the
dual licence), with `LICENSE-MIT-0` beside the others and the README saying which covers what.
Choosing `MIT-0` makes the whole package MIT-0, as Typst's own templates are.

## What you get

```text
typst.toml            the manifest Universe reads: every field its review asks for
src/lib.typ           the entrypoint: the public API, imported from the modules beside it
src/greet.typ         the starter code (a template package's: src/report.typ, template/main.typ)
tests/                tytanic's: a visual test (its reference in ref/), an assertion test
README.md             the package's page on Universe: its examples compile, against the bundle
justfile              `just checks` = what CI runs; `just format`, `just bundle`, `just release`...
.gitattributes        what typst/packages does not get (export-ignore): the bundle is git archive
.editorconfig         shfmt's style, for the shell scripts and the git hooks
flake.nix, flake.lock the tools (the dev shell's, CI's), `nix fmt` and the checks; the lock pins
                      nixos-unstable, every tool's version with it
.githooks/            opt-in (`just install-hooks`): formatting, the shell, the workflows, the
                      imports' versions and dprint before a commit; Conventional Commits for the
                      message and the push
cliff.toml, cog.toml  git-cliff changelogs, cocogitto's commit checks
dprint.json           Markdown and TOML formatting, its plugins pinned (`just dprint-update`)
AGENTS.md             the rules: the public API, warnings, what a package can hold, the tests
CONTRIBUTING, SECURITY, CODE_OF_CONDUCT
LICENSE (+ LICENSE-MIT, LICENSE-APACHE, LICENSE-MIT-0 by the choice and the kind)
.github/              6 workflows, dependabot, issue and PR templates, the tools' and the
                      release notes' scripts
```

### The checks

`just checks` runs, in order: typstyle over every `.typ` file; tinymist's linter over the package
from its entrypoint and a template package's template; shellcheck and shfmt over the shell scripts,
the git hooks and the justfile's script recipes (read out of `just --dump`); actionlint over the
workflows; the tests; every `@preview/<name>:<version>` import against `typst.toml`'s version; each
`typ` block of the README compiled alone, importing the bundle; a template package's template, as
`typst init` makes it from the bundle, compiled; typst-package-check on the bundle; dprint; `cog
check`; and last the flake: `nix fmt -- --ci` (nixfmt, shfmt, typstyle and just's own, through
treefmt; it formats, and fails if that changed a file) and its checks. A compiler warning fails each
compile, and a lint or a package-check warning fails too -- a warning on Universe is a review
comment.

The bundle (`just bundle`, `dist/preview/<name>/<version>`) is `git archive` of the repository, less
what `.gitattributes` marks `export-ignore` -- the tooling, the tests, the contributors' documents
-- laid out as a package path holds it, so `--package-path dist` imports it as `@preview`. A
published version never changes, so the bundle holds the package alone -- `typst.toml`, the README,
the licences, the changelog, the entrypoint's directory, the template -- and what `exclude` names
(documentation the README links); a file new to the repository and none of these stops it, until it
is export-ignored or given a place. For a template package, its thumbnail is rendered there from a
`typst init` of the bundle: always the template as initialized, as Universe asks, and never
committed, as Universe leaves it out of downloads. It is held to what typst/packages' bundler -- not
package-check -- enforces: 250 ppi, or more until its longer edge reaches 1080 px (a business card's
page), and at most 3 MiB.

### The tools, at the lock's versions

tytanic's references are its Typst's rendering, typstyle's and shfmt's format are their own,
tinymist's lints are its version's, compiled by the Typst it is built with, package-check's lints
are typst/packages' at its version, shellcheck's and actionlint's their versions', and
`just shell-check` reads just's own `--dump`: their verdicts depend on their versions, so each is
the version `flake.lock` locks -- nixpkgs', but typst-package-check, typst/packages' own, an input
of its own at a tag (`nix develop --command typst --version` and the like name them). That is why
the template ships its `flake.lock`, as python's and rust's do. CI installs the same:
`.github/install-tools.sh` builds the flake's `tools` (nixpkgs' builds, from its binary cache), and
runs typst-package-check as the image of the input's tag, so `nix develop` and CI judge alike and
there is no version list to keep -- moving the lock moves them all. Installed by hand, a tool may
be another version, and judge apart from CI.

### The CI workflows

- `checks.yml` -- the checks above but the flake's, the commits' and dprint's; tytanic's output
  and differences kept when a test fails, the bundle kept when the checks pass. A second job
  compiles the README and the template on `compiler`'s Typst (`just floor`): the floor is tested,
  not declared.
- `nix.yml` -- `nix fmt -- --ci`, then `nix flake check`, on x86_64 Linux, aarch64 Linux and Apple
  silicon: the format, the lints, the shell, the workflows, the tests (so the references hold on
  each), and typst-package-check built from its flake input (nixpkgs carries none, so an update
  that breaks its build shows here); every system also evaluated.
- `publish.yml` -- see below.
- `style-check-dprint.yml`, `style-check-cocogitto.yml` -- formatting, and Conventional Commits:
  every commit, and a pull request's title (a squash merge makes it the commit).
- `dependabot-automerge.yml` -- merges Dependabot's patch and minor action bumps once the required
  checks pass. Read its setup comment: without required checks it merges what CI never gated.

Every action is pinned to a commit, its version in a comment; Dependabot moves them -- in this
repository too, every template's workflows with the repository's own, in one pull request
([.github/dependabot.yml](../.github/dependabot.yml)). In a project, it moves the flake's inputs
too, monthly, in one pull request (`chore(deps)`: the dev shell is nothing a user of the package
meets), every tool with them: its checks are the new tools' verdict (a new Typst's rendering:
`just update` on its branch). typst-package-check it leaves: its version is typst/packages', moved
by hand when it moves.

### The changelog, `just release` and Typst Universe

There is no `CHANGELOG.md` until the first release writes one: git-cliff generates it from the
commits, never a hand. `just release <major|minor|patch>` shows every step in order and runs no
tests -- it releases `origin/main`, which CI checks: it refuses a dirty tree, another branch, a
`main` that is not `origin/main` or a release with nothing in it; sets the version in `typst.toml`
and in every `@preview/<name>:<version>` import (the README's, the template's: Universe asks that a
release's examples import it), the first release being the declared `0.1.0`; writes the changelog;
commits; tags `v<version>`; pushes the commit and the tag atomically. If a step fails before the
commit -- a git hook refusing it, say -- it puts the files back.

The tag runs `publish.yml`: the bundle made once and linted as typst/packages will, online this time
(the repository must answer); the GitHub release, the bundle as a tarball and the changelog's
section as notes; and, once the repository variable `UNIVERSE_FORK` names your fork of
typst/packages, a branch on it holding the bundle at `packages/preview/<name>/<version>` -- on
typst/packages' main, the fork's main synced to it first, committed as the release's author -- with
the pull request to open linked in the run's summary, titled `<name>:<version>` as typst/packages
asks. The submission itself, and its checklist, stay yours: a fine-grained token for the fork alone
is all it needs (`UNIVERSE_TOKEN`, which the `universe` environment can hold and keep to release
tags), where opening the pull request for you would need one that writes to any public repository.

## New Typst releases, and the floor

What to change, file by file, in a generated package and in this template.

### In a package

**A new Typst**: the package's Typst is the flake's -- nixpkgs' at `flake.lock` -- in the dev shell
and in CI alike (`.github/install-tools.sh` builds the flake's `tools`), and moves with the lock,
typstyle, tinymist and tytanic with it: Dependabot's monthly pull request, or `nix flake update` by
hand. A new Typst may render a visual test apart from its reference, which the tests then fail on
that branch: `just update` writes the new references, which you look at before committing them.
Nothing else is a file to edit.

**The floor raised** (0.14.0 to 0.15.0, say): `typst.toml`'s `compiler`, alone: CI's second job and
`just floor` read it ([The CI workflows](#the-ci-workflows); here, given `typst-0.15.0` on `PATH`),
and Universe takes it as the oldest Typst the package needs. Raise it when the code needs a newer
Typst (AGENTS.md names one: a `path` value, 0.15's), and to no Typst newer than the flake's, which
the other checks run.

### In the template

**A new Typst** in nixpkgs: `locks.yml` (monthly) or `just lock-update typst` moves
`typst/flake.lock` (the root's with it: one original). What follows is a person's, as its summary
says:

1. `typst/cargo-generate.toml`: the `compiler` regex takes the new release, exactly: a new minor as
   its own alternative (`|^0\.16\.0$`), a patch within its minor's (`^0\.15\.[0-2]$`). render-check
   fails until it takes the flake's Typst ("compiler regex refuses the flake's Typst"), and while it
   takes a newer release of those it tries -- its minor's later patches, the next hundred minors'
   and the next two majors' ("accepts ..., above the flake's Typst", naming the lowest).
2. The tests' references: `just smoke typst <kind>` fails where the rendering moved. Generate that
   kind (`just generate typst package`, or `template`), run `nix develop --command just update` in
   it (`target/typst/<kind>/demo`: the new Typst renders them) and look at the difference, then
   copy its `tests/greet/ref/` to `typst/tests/greet/ref/` (a template package's:
   `tests/report/ref/`).

**The default floor moved** (`0.14.0`): `compiler`'s `default` in `typst/cargo-generate.toml`,
`dev/typst/answers.toml`'s `compiler`, `dev/typst/render-check.py`'s base answers, and this page's
table and usage example.

**The lowest floor raised** (0.12, the oldest the checks are verified on): the regex's alternatives
below it out; the render-check control that refuses 0.11.0 (`dev/typst/render-check.py`) moved to
the release below the new lowest; and the text that names 0.12 -- the prompt's comment,
render-check's docstring, the dev README's render-check list, this page's "from 0.12":
`grep -rn '0\.1[12]' typst dev/typst docs/typst.md` lists them, beside the dev README's records of
what was verified.

## Developing this template

How the template is checked here, and what was verified of it, is the maintainers' side:
[dev/typst/README.md](../dev/typst/README.md); the repository's tools, rules and release,
[CONTRIBUTING.md](../CONTRIBUTING.md) and [AGENTS.md](../AGENTS.md).

## Attribution

The workflows, the justfile's shape, `cliff.toml`, `cog.toml`, the hooks, the community documents
and the render-check and smoke-test harness are adapted from the rust and python templates, when
they were the [rust-template](https://github.com/veralvx/rust-template) and the
[python-template](https://github.com/veralvx/python-template) (now [rust](rust.md) and
[python](python.md)), which took them from [`veralvx/imi`](https://github.com/veralvx/imi) (MIT OR
Apache-2.0). The Universe rules followed are typst/packages' documentation and its bundler's and
package-check's source.

## License

Licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](../LICENSE-APACHE) or
  <http://www.apache.org/licenses/LICENSE-2.0>)
- MIT license ([LICENSE-MIT](../LICENSE-MIT) or <http://opensource.org/licenses/MIT>)

at your option.

The generated projects are yours: their licence is the one you choose at generation.
