#!/usr/bin/env bash
# nix-tools.sh <directory> <attribute>...: each attribute of the nixpkgs <directory>/flake.lock
# locks -- its root's `nixpkgs` input -- built by Nix (from its binary cache), its bin/ put on PATH
# (GITHUB_PATH): a template's tools at that lock's versions, its dev shell's, for a job that runs
# outside the shell. <directory> is a template root, a generated project or this repository's;
# only the lock is read, never a flake.nix (python's and rust's hold Liquid).
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "usage: nix-tools.sh <directory> <attribute>..." >&2
  exit 2
fi
lock="$1/flake.lock"
shift
# the input's locked source, as a flake reference that names it exactly
ref="$(jq --exit-status --raw-output '
  .nodes[.nodes[.root].inputs.nixpkgs].locked
  | if .type == "github" then "github:\(.owner)/\(.repo)/\(.rev)?narHash=\(.narHash)"
    else error("nixpkgs is locked as \(.type), not github") end
' "$lock")"
installables=()
for attribute in "$@"; do
  # one result an installable, matched by its place: a duplicate would shift them
  if [[ " ${installables[*]-} " == *" $ref#$attribute "* ]]; then
    echo "error: nix-tools.sh: $attribute named twice" >&2
    exit 2
  fi
  installables+=("$ref#$attribute")
done
# one result each, in order: its default outputs (a tool's executables may be its `bin`, not its
# `out`), the first holding a bin/ put on PATH
built="$(nix build --no-link --json "${installables[@]}")"
for i in "${!installables[@]}"; do
  # the loop, not `head`: a pipe it closed early could fail the step (pipefail)
  bin=""
  while IFS= read -r dir; do
    if [ -d "$dir" ]; then
      bin="$dir"
      break
    fi
  done < <(jq --raw-output --argjson i "$i" '.[$i].outputs[] | . + "/bin"' <<< "$built")
  if [ -z "$bin" ]; then
    echo "error: nix-tools.sh: ${installables[i]} has no bin/" >&2
    exit 1
  fi
  echo "$bin" >> "${GITHUB_PATH:?}"
done
