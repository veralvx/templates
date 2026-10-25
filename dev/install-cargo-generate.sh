#!/usr/bin/env bash
# cargo-generate at the templates' floor -- 0.25.0, each cargo-generate.toml's
# `cargo_generate_version` (`just tool-versions-check` holds the two equal) -- from its GitHub
# release, the archive checked against the SHA-256 it had when pinned, into ~/.local/bin, put on
# PATH: the smoke tests' combinations jobs, typst's and rust's generate jobs, and locks.yml's, on
# Linux x86_64 runners.
# The floor is no lock's: it moves by hand, when the templates raise it -- a new URL and a new sum.
# The newest cargo-generate is the lock's, the smoke tests' Nix jobs' and python's generate job's
# (dev/nix-tools.sh).
set -euo pipefail

version=0.25.0
sum=2e71538c10410827579987c546db7030f71c0283774891bd8ebf107962260e80
bin="$HOME/.local/bin"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$bin"
curl --fail --silent --show-error --location --retry 3 --output "$work/archive.tar.gz" \
  "https://github.com/cargo-generate/cargo-generate/releases/download/v$version/cargo-generate-v$version-x86_64-unknown-linux-gnu.tar.gz"
echo "$sum  $work/archive.tar.gz" | sha256sum --check --quiet
tar -xzf "$work/archive.tar.gz" -C "$work"
install "$(find "$work" -type f -name cargo-generate | head -n 1)" "$bin/cargo-generate"
echo "$bin" >> "${GITHUB_PATH:?}"
