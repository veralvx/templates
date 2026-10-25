#!/usr/bin/env bash
# `just smoke typst <kind>`, in the generated project once its justfile's format is checked: the
# smoke test's Nix job (.github/workflows/smoke-typst.yml, which runs this) but the flake's checks
# -- `just checks` but `nix`, in the generated flake's dev shell, its tools at its lock's versions
# (the root's: one lock), then `just format`, which must leave the project as generated. It needs
# Nix. Its releases and `just floor` are CI's.
set -euo pipefail
nix develop --command just format-check lint shell-check actionlint test versions-check \
  readme-check template-check package-check dprint-check cog
nix develop --command just format
git diff --exit-code
