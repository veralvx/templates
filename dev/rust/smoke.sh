#!/usr/bin/env bash
# `just smoke rust <kind>`, in the generated project once its justfile's format is checked: the
# smoke test's generate job, its releases aside (.github/workflows/smoke-rust.yml) -- in the
# generated flake's dev shell (the toolchain rust-toolchain.toml pins, Miri's nightly its own
# shell), `just checks`, the flake's checks built last, and `just fmt`, which must change nothing.
# It needs Nix.
set -euo pipefail
# with the lock the template ships, which no command may change (the diff below)
nix develop --command just checks
nix develop --command just fmt
git diff --exit-code
