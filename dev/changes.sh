#!/usr/bin/env bash
# changes.sh [<base> <head>]: which templates' smoke tests a run needs, as GitHub step outputs: one
# `<template>=true|false` line for every template root (a top-level folder holding a
# cargo-generate.toml), then `needed=<a JSON list of those true>`, which smoke-gate holds to the
# jobs it waits for. Bash 4 or later (an associative array).
#
# With no commits given (a push, the schedule, by hand): every template. With two (a pull request:
# its merge commit's first parent and the merge commit), by each path that differs between them,
# renames read as a deletion and an addition, so both sides count:
#   <t>/..., dev/<t>/..., .github/workflows/smoke-<t>.yml   template <t>
#   docs/...                                                none: no project changes
#   anything else (shared/, the rest of dev/, the root, the other workflows)   every template
set -euo pipefail
cd "$(dirname "$0")/.."

shopt -s nullglob
templates=()
for config in */cargo-generate.toml; do templates+=("${config%/*}"); done
for t in "${templates[@]}"; do
  # an output's name, a job's (smoke-<t>), a JSON string: nothing to quote
  if [[ ! $t =~ ^[a-z][a-z0-9-]*$ ]] || [ "$t" = needed ]; then
    echo "error: template root '$t': not a lowercase letter, then lowercase letters, digits and hyphens, or 'needed'" >&2
    exit 1
  fi
done

declare -A run=()
every() {
  local t
  for t in "${templates[@]}"; do run[$t]=true; done
}

case $# in
  0) every ;;
  2)
    # into a file, not a process substitution, so a diff that fails (an unknown commit) fails here
    paths="$(mktemp)"
    trap 'rm -f "$paths"' EXIT
    git diff --name-only --no-renames -z "$1" "$2" -- > "$paths"
    while IFS= read -r -d '' path; do
      case $path in
        docs/*) continue ;;
      esac
      chosen=""
      for t in "${templates[@]}"; do
        case $path in
          "$t"/* | dev/"$t"/* | .github/workflows/smoke-"$t".yml)
            chosen=$t
            break
            ;;
        esac
      done
      if [ -n "$chosen" ]; then run[$chosen]=true; else every; fi
    done < "$paths"
    ;;
  *)
    echo "usage: $0 [<base> <head>]" >&2
    exit 2
    ;;
esac

needed=""
for t in "${templates[@]}"; do
  echo "$t=${run[$t]:-false}"
  if [ "${run[$t]:-false}" = true ]; then needed+="${needed:+,}\"$t\""; fi
done
echo "needed=[$needed]"
