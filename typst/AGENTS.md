# AGENTS.md

Repository rules for `{{project-name}}`. These apply to every contributor, human or AI-assisted.
The tools, the tests and the release are [CONTRIBUTING.md](CONTRIBUTING.md)'s.

## 1. The public API is what `src/lib.typ` imports

Typst has no `pub`: everything a module defines is importable from it. So `typst.toml`'s entrypoint,
`src/lib.typ`, defines nothing; it imports from the modules beside it the names users may call,
and only those. A helper stays in its module, unimported by `lib.typ`, and so private.

Every name `lib.typ` exposes is documented twice: a `///` comment above its definition (the
parameters each with their own, and `-> type`, as tinymist and tidy read them), and the README,
which Typst Universe shows. A change to a public name or parameter is a breaking change: `feat!:`.

## 2. Warnings are errors

`just checks` and CI fail on a Typst warning in the README's examples{% if project_kind == "template" %} or the template initialized{% endif %};
on any warning typst-package-check gives the bundle, the linter typst/packages runs on a
submission; and on any lint tinymist reports (`just lint`: a set or show rule that takes no
effect, a value a function's return discards, a font name it does not know). Neither Typst nor
tinymist can silence one at the site, so fix the cause: a deprecated name replaced, a font that
exists, a missing language tag on a code block.

Code is formatted by typstyle, the shell scripts by shfmt (`.editorconfig` holds its style) --
both at the versions `flake.lock` locks -- the justfile by just, the Markdown and TOML by dprint,
and the Nix by nixfmt: `just format` runs them all, `nix fmt` all but dprint. A script is named
`*.sh`, a git hook excepted: `.editorconfig` and `nix fmt` reach no other. The workflows pass
actionlint.
Shell passes ShellCheck, a justfile script recipe included (`just shell-check` reads them out of
`just --dump`, and refuses one that splices a value into its text: it takes arguments). Names
users call are kebab-case (`page-margin`, not `pageMargin`), as Typst's own are and package-check
asks.

## 3. What a package can and cannot hold

- **Paths are the package's.** `image("logo.png")` inside the package reads the package's file,
  never the user's project. To let a user change an asset, take it as content (`logo:
  image("logo.png")` as a default, which the user overrides with their own `image(...)`); from
  Typst 0.15, a `path` value works too, but only if `compiler` in `typst.toml` is 0.15 or later.
- **No fonts.** Typst Universe refuses font files. Use the fonts Typst embeds, or document the one
  the user must install -- the checks compile with the embedded fonts alone, which every Typst
  has, the web app's and the command line's, so an unknown font family is a warning, and fails.
- **Imports by package specification.** The README's examples{% if project_kind == "template" %} and the template{% endif %} import
  `@preview/{{project-name}}:<version>`, never a relative path: a user must be able to copy them
  as they are. `just release` moves every such version; `just versions-check` refuses a stale
  one.
- **Every code block in the README has a language.** `typ` blocks are compiled, each alone,
  against the bundle -- fenced with backticks or tildes, indented in a list or not; Universe's
  linter reads a block without a language as Typst. Use `text` for one that should not compile.
- **What typst/packages gets** is the repository less `.gitattributes`' `export-ignore` paths.
  A new file for users goes in the bundle by default; a new development file gets a line there.

## 4. Tests

Each test is a directory under `tests/` with a `test.typ`, run by tytanic (`just test`):

- **with a `ref/` directory**, its pages are compared with the reference images in it -- how
  something *looks*. A change to them is deliberate: `just update <test>`, then look at the new
  image before committing it.
- **without one**, it is only compiled: assertions about what a function *returns* or *refuses*
  (`assert.eq`, and tytanic's `catch` for a panic's message).
{%- if project_kind == "template" %}
- **the template**, as `typst init` makes it, is a test of its own (`@template`), compiled.
{%- endif %}

A function that can be given the wrong thing checks its arguments with `assert` and a message
naming the parameter, and a test holds that message.

## 5. Comments: only what is essential

A comment says what the code cannot: why it is so, the source it follows, the constraint it
keeps. Make it concise and precise -- a line where a line does -- and never restate the code:
that is noise, and it goes stale. A change that falsifies a comment rewrites it.

## 6. Commits

[Conventional Commits](https://www.conventionalcommits.org/) are enforced by `cog check` locally
and in CI. The changelog is generated from the commits (`cliff.toml`), so the subject line is
user-facing text; `chore`, `ci` and `style` commits stay out of it, and `!` or a
`BREAKING CHANGE` footer lists a commit first:

```text
{% if project_kind == "template" -%}
feat: accept a subtitle
fix: keep the title block on the first page
docs: document the report's parameters
feat!: rename `authors` to `by`
{%- else -%}
feat: accept a list of names
fix: keep the greeting on one line
docs: document the greeting's parameters
feat!: rename `name` to `who`
{%- endif %}
```

The git hooks (`just install-hooks`) check the same before a commit and a push; never bypass them
with `--no-verify`. `git revert` writes `Revert "..."`, which CI refuses: reword it as
`revert: ...`.

## 7. Before you claim a change is done

Run `just checks`. It is what CI runs: the format, the lints, the shell, the workflows, the
tests, the imports' versions, the README's examples, {% if project_kind == "template" %}the template as initialized, {% endif %}the bundle through typst-package-check, dprint,
the commit messages, and the flake's checks. CI also compiles the README{% if project_kind == "template" %} and the template{% endif %} on the oldest
Typst `typst.toml` declares (`compiler`): `just floor` runs that, given that Typst. Reporting
"done" on a change that has not passed them is the one thing that wastes the most time here.

If a check fails for reasons unrelated to your change, say so explicitly rather than working
around it -- a broken check that everyone routes around stops protecting anything.
