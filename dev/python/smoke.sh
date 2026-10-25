#!/usr/bin/env bash
# `just smoke python <kind>`, in the generated project once its justfile's format is checked: the
# smoke test's generate job, its releases aside (.github/workflows/smoke-python.yml) -- in the
# generated flake's dev shell, the lock written and committed, then `just checks` (the flake's
# checks built last), `just pins-update` -- idle, then with ruff (and packaging) planted stale and
# locked, and uv's required-version: all moved back, the lock with them -- and `just format`, which
# must leave the project as generated. It needs Nix. `pins`, alone: that last part, which the
# smoke test's step of that name runs (its lock already committed, its checks a step of their own).
set -euo pipefail
case "${1-}" in
  "")
    nix develop --command uv lock
    git add uv.lock
    git -c user.name=generate -c user.email=generate@localhost commit --quiet -m "chore: the lock"
    nix develop --command just checks
    ;;
  pins) ;;
  *)
    echo "usage: smoke.sh [pins]" >&2
    exit 2
    ;;
esac
nix develop --command just pins-update
# ruff, and (a workspace's) packaging in both its groups: one report line, both moved -- by GNU
# sed, the dev shell's (macOS's own takes -i's argument apart)
nix develop --command sed -i 's/"ruff==[^"]*"/"ruff==0.1.0"/; s/"packaging==[^"]*"/"packaging==24.0"/g' pyproject.toml
nix develop --command uv lock --quiet
# uv's own pin too, after the lock: a uv other than it refuses to run
nix develop --command sed -i 's/^required-version = "==[^"]*"/required-version = "==0.1.0"/' pyproject.toml
nix develop --command just pins-update
nix develop --command just format
git diff --exit-code
