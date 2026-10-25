# The recipes every justfile holds alike: the root's and every template's (copied in place by
# `just sync`, which holds each copy to its text here). Edit them here, then `just sync`.

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
