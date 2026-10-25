#!/usr/bin/env bash
# on-default-branch.sh: a run by hand (workflow_dispatch) of a workflow that proposes pull requests
# -- locks.yml's, dprint-plugins.yml's -- refused off the default branch, the one its pull requests
# go to (dev/propose.sh's base is the run's branch); a schedule runs on it. Env: REF (github.ref)
# and DEFAULT (the repository's default branch).
set -euo pipefail

if [ "${REF:?}" != "refs/heads/${DEFAULT:?}" ]; then
  echo "::error::run it on $DEFAULT, the branch its pull requests go to (not $REF)" >&2
  exit 1
fi
