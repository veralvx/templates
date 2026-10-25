#!/usr/bin/env bash
# unlisted.sh <list>: each path on standard input, one a line, that <list> does not let through,
# printed -- a pattern a line (bash's: `*` crosses folders), the last that matches deciding, `!`
# refusing what it matches; `#` comments and blank lines, a line's surrounding blanks dropped. A
# path is a pattern of itself, but for pattern syntax, which a listed path must not hold: `*`, `?`,
# `[`, `\` and extglob's `+(`, `@(`, `!(` and the like. What an update may change: dev/propose.sh
# holds a pull request's change to it, dev/lock_core.py and dev/dprint_plugins.py their own.
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: unlisted.sh <list> < paths" >&2
  exit 2
fi
patterns=()
while IFS= read -r line || [ -n "$line" ]; do
  # blanks around a line -- a space, a CR (a list saved with CRLF) -- are no part of its pattern: a
  # `!` one would refuse nothing else
  line="${line#"${line%%[![:space:]]*}"}"
  line="${line%"${line##*[![:space:]]}"}"
  if [ -n "$line" ] && [[ $line != '#'* ]]; then patterns+=("$line"); fi
done < "$1"
# a last path with no newline after it is read too: none is let through unread
while IFS= read -r path || [ -n "$path" ]; do
  found=1
  # shellcheck disable=SC2053 # each pattern unquoted, a pattern
  for pattern in ${patterns[@]+"${patterns[@]}"}; do
    if [[ $pattern == '!'* ]]; then
      if [[ $path == ${pattern#!} ]]; then found=1; fi
    elif [[ $path == $pattern ]]; then
      found=0
    fi
  done
  if [ "$found" -ne 0 ]; then printf '%s\n' "$path"; fi
done
