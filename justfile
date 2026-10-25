# This repository's automation: the templates', not a generated project's (each template root's
# justfile is that). A template root is a top-level folder holding a cargo-generate.toml. The
# commands are the workflows' (.github/workflows/). Formatted with `just --fmt --unstable`.

# The GitHub repository the changelog's compare links name: cliff.toml, every template's copy,
# names none.
export repository := "veralvx/templates"

[doc("List the recipes")]
default:
    @just --list --unsorted

# python-liquid stands in for cargo-generate's Liquid; the versions are dev/requirements.txt's, into
# .venv (the recipe says when it is made anew). With no template named, every template root runs
# (alphabetical). Each runs whatever another's verdict; the recipe fails if one did, or if a name is
# no template root or has no render-check.
[doc("Every templated file rendered for every answer combination, and checked: the templates named, or all (dev/<template>/render-check.py)")]
[positional-arguments]
render-check *templates:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ "$#" -eq 0 ]; then
        shopt -s nullglob
        configs=(*/cargo-generate.toml)
        set -- "${configs[@]%/cargo-generate.toml}"
        if [ "$#" -eq 0 ]; then
            echo "no template root (a folder holding a cargo-generate.toml): nothing to check" >&2
            exit 0
        fi
    fi
    failed=0
    templates=()
    for template in "$@"; do
        template="${template%/}"
        if [ ! -f "$template/cargo-generate.toml" ]; then
            echo "error: $template: not a template root (no $template/cargo-generate.toml)" >&2
            failed=1
        elif [ ! -f "dev/$template/render-check.py" ]; then
            echo "error: $template: no dev/$template/render-check.py" >&2
            failed=1
        else
            templates+=("$template")
        fi
    done
    if [ "${#templates[@]}" -gt 0 ]; then
        # made anew when its Python no longer runs (a Nix store path collected, say), or
        # dev/requirements.txt is not what it was made from (its copy there): installing never
        # removes what a pin dropped
        if ! .venv/bin/python -c '' 2> /dev/null || ! cmp -s dev/requirements.txt .venv/requirements.txt; then
            python3 -m venv --clear .venv
        fi
        .venv/bin/pip install --quiet --disable-pip-version-check --no-deps --requirement dev/requirements.txt
        # each one's own requirements met by the others: what is missing, or apart, said
        if ! broken="$(.venv/bin/pip check --disable-pip-version-check)"; then
            echo "error: dev/requirements.txt: $broken" >&2
            exit 1
        fi
        cp dev/requirements.txt .venv/requirements.txt
    fi
    for template in "${templates[@]}"; do
        echo "=== $template"
        .venv/bin/python "dev/$template/render-check.py" || failed=1
    done
    exit "$failed"

# With the real cargo-generate, the answers the smoke test gives (dev/<template>/answers.toml, its
# --values-file), under target/ (which git ignores here); the kinds are the template's project_kind
# choices. cargo-generate makes no repository inside this one, and nixpkgs' build none at all: so
# `git init`, the first commit made. Prints the project's path alone.
[doc("A template generated: just generate <template> <kind>, into target/<template>/<kind>/demo")]
[positional-arguments]
generate template kind:
    #!/usr/bin/env bash
    set -euo pipefail
    template="${1%/}"
    kind="$2"
    # both checked before a path is made of them
    if [[ ! $template =~ ^[a-z][a-z0-9-]*$ ]] || [ ! -f "$template/cargo-generate.toml" ]; then
        echo "error: $template: not a template root (no $template/cargo-generate.toml)" >&2
        exit 1
    fi
    answers="dev/$template/answers.toml"
    if [ ! -f "$answers" ]; then
        echo "error: $template: no $answers" >&2
        exit 1
    fi
    # a command substitution, so a failing read stops here
    read_kinds='import sys, tomllib; config = tomllib.load(open(sys.argv[1], "rb"))'
    read_kinds+='; print(*config["placeholders"]["project_kind"]["choices"], sep="\n")'
    choices="$(python3 -c "$read_kinds" "$template/cargo-generate.toml")"
    kinds=()
    while IFS= read -r choice; do
        kinds+=("$choice")
    done <<< "$choices"
    known=0
    for choice in "${kinds[@]}"; do
        if [ "$choice" = "$kind" ]; then known=1; fi
    done
    if [ "$known" -eq 0 ] || [[ ! $kind =~ ^[a-z][a-z0-9-]*$ ]]; then
        list="${kinds[*]}"
        echo "error: $template's kind is one of ${list// /, } (got '$kind')" >&2
        exit 1
    fi
    destination="target/$template/$kind"
    rm -rf "$destination"
    mkdir -p "$destination"
    # the template root itself, not the repository and a subfolder: cargo-generate copies what
    # --path names before it reads the subfolder, target/ and .venv/ included
    cargo-generate generate --path "$PWD/$template" --name demo --destination "$destination" \
        --silent --values-file "$answers" -d "project_kind=$kind" >&2
    cd "$destination/demo"
    if [ ! -e .git ]; then git init --quiet -b main; fi
    git add --all
    git -c user.name=generate -c user.email=generate@localhost commit --quiet \
        -m "chore: initial commit from template"
    echo "$destination/demo"

# The smoke test's checks of a generated project, its releases aside: its justfile's format
# checked, then dev/<template>/smoke.sh in it, which runs them in the project's own flake's shell.
[doc("A template generated, then its own checks run: just smoke <template> <kind>")]
[positional-arguments]
smoke template kind:
    #!/usr/bin/env bash
    set -euo pipefail
    project="$(just generate "$1" "$2")"
    smoke="$PWD/dev/${1%/}/smoke.sh"
    if [ ! -x "$smoke" ]; then
        echo "error: ${1%/}: no executable dev/${1%/}/smoke.sh" >&2
        exit 1
    fi
    cd "$project"
    just --fmt --check --unstable
    "$smoke"

# dev/<template>/lock.py (dev/lock_core.py): the template's flake.lock moved to its inputs' newest,
# then what follows it -- pins, a prompt, dist's version -- and render-check; the summary, for a
# pull request, to the file `--summary` names (a relative one, from here). No template named: every
# template with a dev/<template>/lock.py, in turn, as locks.yml runs them -- the root's lock is
# typst's (`just flake-sync`) -- each to the end whatever another does, the recipe failing if one
# did. Needs Nix, Python 3.11 or later and the inputs' sources reachable; cargo-generate for
# python's and rust's (a generated project).
[doc("Templates' locks updated, and what follows them: just lock-update [<template> [--summary <file>]] (none: every one, the root's with typst's)")]
[positional-arguments]
lock-update *args:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ "$#" -gt 0 ] && [[ $1 != -* ]]; then
        template="${1%/}"
        shift
        if [[ ! $template =~ ^[a-z][a-z0-9-]*$ ]] || [ ! -f "$template/cargo-generate.toml" ] || [ ! -f "dev/$template/lock.py" ]; then
            echo "error: $template: no template root with a dev/$template/lock.py" >&2
            exit 1
        fi
        exec python3 "dev/$template/lock.py" "$@"
    fi
    if [ "$#" -gt 0 ]; then
        echo "error: $*: one template's options -- just lock-update <template> [--summary <file>]" >&2
        exit 2
    fi
    shopt -s nullglob
    failed=()
    for update in dev/*/lock.py; do
        template="${update#dev/}"
        template="${template%/lock.py}"
        [ -f "$template/cargo-generate.toml" ] || continue
        echo "=== $template"
        python3 "$update" || failed+=("$template")
    done
    if [ "${#failed[@]}" -gt 0 ]; then
        echo "error: the lock update failed for ${failed[*]} (its output above says why)" >&2
        exit 1
    fi

# shellcheck and shfmt over every shell script git does not ignore -- shfmt finds them, by extension
# or shebang, and formats them as .editorconfig says -- and over this justfile's shell script
# recipes (a sh, bash, dash or ksh shebang), which no file holds: each taken from `just --dump`,
# the names the justfile exports declared before it for shellcheck (their values are just's
# expressions, not shell's), formatted in the justfile's own style (4 spaces). A script recipe
# takes its values as arguments, never as `{{ }}` spliced into its text, and names its shell in a
# shebang, not a `[script]` attribute (whose body holds none to read): both are refused here.
[doc("The shell: shellcheck and shfmt over the scripts, the git hooks and the justfile's script recipes")]
shell-check:
    #!/usr/bin/env bash
    set -euo pipefail
    work="$(mktemp -d)"
    trap 'rm -rf "$work"' EXIT
    failed=0
    just shfmt --diff || failed=1
    scripts=()
    while IFS= read -r file; do
        scripts+=("$file")
    done < <(just shfmt --find)
    if [ "${#scripts[@]}" -gt 0 ]; then
        shellcheck "${scripts[@]}" || failed=1
    fi
    dump="$(just --dump --dump-format json)"
    while IFS= read -r recipe; do
        if jq -e --arg recipe "$recipe" '.recipes[$recipe].attributes | any(type == "object" and has("script"))' <<< "$dump" > /dev/null; then
            echo "error: $recipe: a [script] recipe -- name its shell in a shebang instead" >&2
            failed=1
            continue
        fi
        # its shebang's program, or the one `env` runs, past env's options (`-S`)
        read -r -a shebang < <(jq -r --arg recipe "$recipe" '.recipes[$recipe].body[0][0] | ltrimstr("#!")' <<< "$dump")
        program="${shebang[0]-}"
        program="${program##*/}"
        if [ "$program" = env ]; then
            program=""
            for word in "${shebang[@]:1}"; do
                if [[ $word != -* ]]; then
                    program="$word"
                    break
                fi
            done
        fi
        case "$program" in
            sh | bash | dash | ksh) ;;
            *) continue ;;
        esac
        jq -r --arg recipe "$recipe" '
            .recipes[$recipe].body
            | map(map(if type == "string" then . else error("\($recipe): an interpolation in a script recipe: pass the value as an argument") end) | join(""))
            | join("\n")
        ' <<< "$dump" > "$work/$recipe" || {
            failed=1
            continue
        }
        # after the shebang, the variables just exports to it: the `export`ed assignments and
        # `$`-parameters, or every one under `set export`
        {
            head -n 1 "$work/$recipe"
            jq -r --arg recipe "$recipe" '
                .settings.export as $all
                | (.assignments[], .recipes[$recipe].parameters[])
                | select($all or .export)
                | "export \(.name)="
            ' <<< "$dump"
            tail -n +2 "$work/$recipe"
        } > "$work/$recipe.with-exports"
        (cd "$work" && shellcheck --shell="$program" "$recipe.with-exports") || failed=1
        (cd "$work" && shfmt --diff --indent 4 --case-indent --space-redirects --binary-next-line "$recipe") || failed=1
    done < <(jq -r '.recipes | to_entries[] | select(.value.shebang) | .key' <<< "$dump")
    exit "$failed"

# shfmt over every shell script git does not ignore and that exists (shfmt finds them, by extension
# or shebang): `just shfmt --find` lists them, `--diff` checks, `--write` formats.
[positional-arguments]
[private]
shfmt mode:
    #!/usr/bin/env bash
    set -euo pipefail
    # a process substitution's failure goes unseen (set -e): outside a repository, ls-files' would
    git rev-parse --is-inside-work-tree > /dev/null
    files=()
    while IFS= read -r -d '' file; do
        if [ -f "$file" ]; then files+=("$file"); fi
    done < <(git ls-files -z --cached --others --exclude-standard)
    # with no file, shfmt would read stdin; a command substitution, so a failing shfmt stops here
    found=""
    if [ "${#files[@]}" -gt 0 ]; then found="$(shfmt --find "${files[@]}")"; fi
    if [ -z "$found" ]; then exit 0; fi
    scripts=()
    while IFS= read -r file; do
        scripts+=("$file")
    done <<< "$found"
    case "$1" in
        --find) printf '%s\n' "${scripts[@]}" ;;
        *) shfmt "$1" "${scripts[@]}" ;;
    esac

# The justfile's own script recipes formatted as `just shell-check` holds them: each sh, bash, dash
# or ksh recipe taken from `just --dump`, through shfmt in the justfile's style, and put back in
# its place, 4 spaces in. A `[script]` recipe, or one with a `{{ }}` in it, is shell-check's to
# refuse, and is left as it is.
[private]
shfmt-recipes:
    #!/usr/bin/env bash
    set -euo pipefail
    work="$(mktemp -d)"
    trap 'rm -rf "$work"' EXIT
    dump="$(just --dump --dump-format json)"
    # the shebang's program, or the one `env` runs, past env's options (`-S`), as shell-check reads it
    names="$(jq -r '
        .recipes[]
        | select(.shebang)
        | select(.attributes | any(type == "object" and has("script")) | not)
        | select(all(.body[][]; type == "string"))
        | select(
            (.body[0][0] | ltrimstr("#!") | [splits("[ \t]+")] | map(select(. != ""))) as $words
            | ($words[0] | split("/") | last) as $program
            | if $program == "env" then [$words[1:][] | select(startswith("-") | not)][0] else $program end
            | IN("sh", "bash", "dash", "ksh")
        )
        | .name
    ' <<< "$dump")"
    if [ -z "$names" ]; then exit 0; fi
    while IFS= read -r recipe; do
        jq -r --arg recipe "$recipe" '.recipes[$recipe].body | map(join("")) | join("\n")' <<< "$dump" > "$work/body"
        shfmt --indent 4 --case-indent --space-redirects --binary-next-line "$work/body" > "$work/formatted"
        if cmp -s "$work/body" "$work/formatted"; then continue; fi
        # the recipe's line, then its body in place of the old: every line to the next at the
        # margin, less the blank lines before that one
        awk -v recipe="$recipe" -v formatted="$work/formatted" '
            function body(line) {
                while ((getline line < formatted) > 0) print (line == "" ? "" : "    " line)
                close(formatted)
            }
            state == 1 && $0 == "" { blanks++; next }
            state == 1 && /^[ \t]/ { blanks = 0; next }
            state == 1 {
                body()
                for (; blanks > 0; blanks--) print ""
                state = 2
            }
            state == 0 && $0 ~ ("^@?" recipe "([ \t][^:]*)?:") && $0 !~ ("^" recipe "[ \t]*:=") { state = 1 }
            { print }
            END { if (state == 1) body() }
        ' justfile > "$work/justfile"
        cat "$work/justfile" > justfile
    done <<< "$names"

# A command run in every template root, in turn (alphabetical); with none, nothing runs. The first
# failure stops it.
[positional-arguments]
[private]
each-template +command:
    #!/usr/bin/env bash
    set -euo pipefail
    shopt -s nullglob
    for config in */cargo-generate.toml; do
        (cd "${config%/*}" && "$@")
    done

# Every copy of a shared file, and the recipes every justfile holds, as shared/ has them
# (shared/manifest.toml; dev/sync.py says all it checks).
[doc("The shared files copied where shared/manifest.toml says, then all checked (modifies files); `just sync --check` checks only")]
[positional-arguments]
sync *args:
    python3 dev/sync.py "$@"

# The templates' justfiles' script recipes, which only their own `just shell-check` reads.
[doc("Each template's `just shell-check`, in its root")]
template-shell-check:
    just each-template just shell-check

# actionlint runs shellcheck on each `run:` script too, when it is on PATH. Its project is the
# repository a file is in -- this one, for a template root's workflows -- which resolves a `uses:
# ./.github/workflows/...` and reads .github/actionlint.yaml: so each template root's .github is
# linted as a repository of its own, a generated project's.
[doc("The workflows linted (actionlint): this repository's and every template's")]
actionlint:
    #!/usr/bin/env bash
    set -euo pipefail
    # a process substitution's failure goes unseen (set -e): outside a repository, ls-files' would
    git rev-parse --is-inside-work-tree > /dev/null
    files=()
    while IFS= read -r -d '' file; do
        if [ -f "$file" ]; then files+=("$file"); fi
    done < <(git ls-files -z --cached --others --exclude-standard -- \
        '.github/workflows/*.yml' '.github/workflows/*.yaml')
    # with no file named, actionlint looks for a repository's workflows, and fails without one
    if [ "${#files[@]}" -gt 0 ]; then actionlint "${files[@]}"; fi
    work="$(mktemp -d)"
    trap 'rm -rf "$work"' EXIT
    failed=0
    shopt -s nullglob
    for config in */cargo-generate.toml; do
        template="${config%/*}"
        # its .github as git has it (an ignored file left out, an untracked one in)
        listed="$(git ls-files --cached --others --exclude-standard -- "$template/.github")"
        if ! grep -qF "$template/.github/workflows/" <<< "$listed"; then continue; fi
        while IFS= read -r file; do
            if [ -f "$file" ]; then
                mkdir -p "$work/$(dirname "$file")"
                cp -p "$file" "$work/$file"
            fi
        done <<< "$listed"
        git -C "$work/$template" init --quiet
        if ! (cd "$work/$template" && actionlint); then
            echo "error: $template/.github: the workflows above, as a generated project has them" >&2
            failed=1
        fi
    done
    exit "$failed"

# Every formatter a check holds the files to: the shell (the templates' too), the justfiles, the
# Markdown and the TOML (each template root's are a generated project's), then the Nix through
# `nix fmt` (nixfmt, and shfmt and just's own again) -- without Nix, it stops there, the rest
# formatted. The lock as it is (`just nix`).
[doc("Format the shell scripts, the justfiles, the Markdown and the TOML, then the Nix (modifies files)")]
format:
    just shfmt --write
    just shfmt-recipes
    just each-template just shfmt-recipes
    just --fmt --unstable
    just each-template just --fmt --unstable
    dprint fmt
    nix fmt --no-update-lock-file

[doc("Markdown and TOML formatted (dprint.json)")]
dprint-check:
    dprint check

# dev/dprint_plugins.py: every dprint.json's plugins -- here and each template's, held equal -- to
# their newest releases (`dprint config update`), then the root's Markdown and TOML formatted by
# them and the shared files' copies synced; the summary, for a pull request, to the file
# `--summary` names. dprint-plugins.yml runs it monthly. Needs dprint, just and Python 3.11 or
# later, and the plugins' sources reachable (plugins.dprint.dev, npm).
[doc("The dprint plugins to their newest, every dprint.json's, and what they format anew: just dprint-update [--summary <file>]")]
[positional-arguments]
dprint-update *args:
    python3 dev/dprint_plugins.py "$@"

[doc("Every commit conventional (cog.toml)")]
cog:
    cog check

# What CI or a recipe installs is a lock's -- a flake's nixpkgs, through `nix develop`, a flake's
# `tools` or dev/nix-tools.sh -- or an action's own (Dependabot's), but cargo-generate's floor
# (dev/install-cargo-generate.sh, held to the templates' `cargo_generate_version`):
# dev/tool_versions.py refuses a version written in anywhere else, and an action named by a tag or
# a branch rather than its commit.
[doc("No tool version written by hand: each a lock's, but cargo-generate's floor; every action at its commit")]
tool-versions-check:
    python3 dev/tool_versions.py

# One lock, the root's and typst's: shared/root/flake.lock, which `just sync` copies to both, so
# the shell's tools are at a typst project's versions. The inputs here are typst's
# (typst/flake.nix): change both alike, `nix flake update` (or `nix flake lock`) here or in typst/,
# then this. The lock changed since the last commit -- the root's, typst's or the original, git
# says which -- becomes all three; two changed apart are refused: which one is meant is yours to say.
[doc("The lock changed here, in typst/ or in shared/root/ made all three (`just sync`)")]
flake-sync:
    #!/usr/bin/env bash
    set -euo pipefail
    original=shared/root/flake.lock
    updated=""
    for lock in flake.lock typst/flake.lock "$original"; do
        if git diff --quiet HEAD -- "$lock"; then continue; fi
        if [ -n "$updated" ] && ! cmp -s "$updated" "$lock"; then
            echo "error: $updated and $lock both changed, and differ: keep the one meant, restore the other (git restore), then just flake-sync" >&2
            exit 1
        fi
        updated="$lock"
    done
    if [ -n "$updated" ] && [ "$updated" != "$original" ]; then cp "$updated" "$original"; fi
    just sync

# `nix fmt -- --ci` formats -- treefmt has no check-only mode -- and fails if that changed a file:
# look at the change, then commit it. The flake's `format` check is the same verdict, on a copy.
# The lock is never rewritten: a stale one (the inputs changed, the lock not) fails here, where
# Nix would otherwise rewrite it unseen (`just flake-sync`).
[doc("The flake: its formatter's verdict (`nix fmt`), every system evaluated, this one's checks built")]
nix:
    nix fmt --no-update-lock-file -- --ci
    nix flake check --no-update-lock-file --no-build --all-systems
    nix flake check --no-update-lock-file

# `nix` last: the slowest, and the one a machine without Nix cannot run. The flake sees git's files
# only: a new file is invisible to it until `git add`ed. `just smoke <template> <kind>` is the
# smoke test's, and slow.
[doc("Every check but the smoke test, the flake's last")]
checks: render-check (sync "--check") tool-versions-check shell-check template-shell-check actionlint dprint-check cog nix

# Opt-in, as every git hook is: a clone never installs one, so CI stays the gate.
# `git config --unset core.hooksPath` turns them off again.
[doc("Use .githooks: the shell, the workflows and dprint before a commit; Conventional Commits for the message and before a push")]
install-hooks:
    git config core.hooksPath .githooks

[doc("The changelog (cliff.toml): `just changelog --unreleased` previews the next release")]
[positional-arguments]
changelog *args:
    git cliff --offline --github-repo "$repository" "$@"

# Every step here, in order. The templates have no version file: a release is its tag, `v<version>`,
# every template's at once, and the changelog's section; the first is 0.1.0, whatever the level.
# The tag makes the GitHub release (release.yml). No tests here: what is released is origin's main,
# which CI checks.
[doc("Release: just release <major|minor|patch> -- changelog, commit, tag, push")]
[positional-arguments]
release level:
    #!/usr/bin/env bash
    set -euo pipefail

    # 0. The level -- passed as $1, never spliced into this script's text
    case "$1" in
        major | minor | patch) level="$1" ;;
        *)
            echo "error: the level must be major, minor or patch (got '$1')" >&2
            exit 1
            ;;
    esac

    # 1. From a clean main that is origin's -- pushed, so the commit released is the one CI ran on
    if [ -n "$(git status --porcelain)" ]; then
        echo "error: the working tree is not clean: commit or stash first" >&2
        exit 1
    fi
    if [ "$(git branch --show-current)" != main ]; then
        echo "error: a release is cut from main" >&2
        exit 1
    fi
    git fetch origin
    if ! git rev-parse --quiet --verify origin/main > /dev/null; then
        echo "error: origin has no main: push it first" >&2
        exit 1
    fi
    if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
        echo "error: main is not origin/main: push (and let CI pass) or pull first" >&2
        exit 1
    fi

    # 2. The version: the latest release tag's, bumped by the level; 0.1.0 with no tag yet. Its
    # glob also takes a pre-release's (v1.2.3-rc.1), which no arithmetic reads: left out
    tags="$(git tag --list 'v[0-9]*.[0-9]*.[0-9]*' --sort=-version:refname)"
    latest="$(grep -m 1 -E '^v[0-9]+\.[0-9]+\.[0-9]+$' <<< "$tags" || true)"
    if [ -z "$latest" ]; then
        version=0.1.0
    else
        IFS=. read -r major minor patch <<< "${latest#v}"
        case "$level" in
            major) version="$((major + 1)).0.0" ;;
            minor) version="$major.$((minor + 1)).0" ;;
            patch) version="$major.$minor.$((patch + 1))" ;;
        esac
    fi
    tag="v$version"
    if git rev-parse --quiet --verify "refs/tags/$tag" > /dev/null; then
        echo "error: $tag is already tagged" >&2
        exit 1
    fi

    # 3. Something to release: a commit since the last tag that enters the changelog
    entries="$(just changelog --unreleased --context | jq '[.[].commits | length] | add // 0')"
    if [ "$entries" -eq 0 ]; then
        echo "error: nothing to release -- no commit since the last tag would enter the changelog" >&2
        exit 1
    fi

    # If anything below fails before the commit, put back what it changed: the tree was clean, so
    # HEAD's files are exactly that, and a changelog the first release created goes.
    restore() {
        echo "Release aborted -- restoring the files it changed." >&2
        git reset --quiet --hard HEAD
        if ! git cat-file -e HEAD:CHANGELOG.md 2> /dev/null; then
            rm -f CHANGELOG.md
        fi
    }
    trap restore ERR

    # 4. The changelog, the release's section on top
    just changelog --tag "$tag" --output CHANGELOG.md

    # 5. Commit, then change the trap: a refused commit (a git hook) still restores the files, but
    #    once committed, a failure is finished by hand -- a re-run would bump again
    git add CHANGELOG.md
    git commit -m "chore(release): $tag"
    finish() {
        echo "error: $tag is committed; finish it by hand: git tag -a $tag -m 'Release $tag' (unless tagged), then git push --atomic origin main $tag" >&2
    }
    trap finish ERR
    git tag -a "$tag" -m "Release $tag"

    # 6. The commit and the tag together, both or neither
    git push --atomic origin main "$tag"
    echo "Released $tag: release.yml takes it from here."
