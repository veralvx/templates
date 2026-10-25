#!/usr/bin/env bash
# The tools CI runs, onto PATH, at the versions flake.lock locks: the flake's `tools` (nixpkgs'
# typst, tytanic, typstyle, tinymist, just, jq, shellcheck, shfmt and actionlint), which Nix
# fetches from its binary cache; and typst-package-check as the image typst/packages' CI runs (its
# action.yml), at the tag the flake's `package-check` input names -- nixpkgs builds none of it --
# pulled here, and a command that runs it on the working directory.
# checks.yml's and publish.yml's, on Linux runners with Nix and Docker (and jq, the runner's, which
# reads flake.lock before the tools are there).
set -euo pipefail

root="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# the input's tag, as flake.lock holds it (`v0.7.0`); the image's is its version alone
tag="$(jq --raw-output '.nodes[.nodes[.root].inputs["package-check"]].original.ref // empty' "$root/flake.lock")"
if [[ ! $tag =~ ^v?[0-9]+(\.[0-9]+)*$ ]]; then
  echo "error: flake.lock's package-check input names no version tag (read: '$tag'): typst-package-check's image is that tag's" >&2
  exit 1
fi
# by its tag, not a digest: what typst/packages runs is the tag (package-check's action.yml), and a
# digest would hold this to an image the tag may since have left
image="ghcr.io/typst/package-check:${tag#v}"
# the lock as committed: one flake.nix no longer matches is refused, never relocked here
tools="$(nix build --no-update-lock-file --no-link --print-out-paths "$root#tools")"
# pulled now, so a tag with no image fails here, not at the first check
docker pull --quiet "$image" > /dev/null
bin="$HOME/.local/bin"
mkdir -p "$bin"
cat > "$bin/typst-package-check" << EOF
#!/bin/sh
# the working directory mounted at its own path, so the paths given are the container's too
exec docker run --rm --volume "\$PWD:\$PWD" --workdir "\$PWD" $image "\$@"
EOF
chmod +x "$bin/typst-package-check"
{
  echo "$bin"
  echo "$tools/bin"
} >> "${GITHUB_PATH:?}"
