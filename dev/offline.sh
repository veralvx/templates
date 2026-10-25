#!/usr/bin/env bash
# offline.sh [--] <command>...: the command run with no network -- in a network namespace of its
# own (`unshare --net`: a loopback alone, down; no route, no DNS) -- as the user who ran this (its
# supplementary groups dropped), with its umask and environment: the smoke tests' generation, which
# needs none. root makes the namespace (sudo, passwordless on GitHub's runners): an unprivileged
# user would need a user namespace, which Ubuntu 24.04's AppArmor refuses it; root runs nothing
# else, unshare taken from sudo's secure_path. sudo keeps the environment (-E) but for what it
# sets, put back as the caller had it -- PATH, HOME, USER, LOGNAME, the umask -- and its SUDO_*,
# dropped; for what it deems unsafe, lost (LD_*, PYTHONPATH, TMPDIR, BASH_ENV and the like); and
# for what it adds where the caller had none (TERM, LANG, SHELL).
set -euo pipefail

if [ "${1-}" = -- ]; then shift; fi
if [ "$#" -eq 0 ]; then
  echo "usage: offline.sh [--] <command>..." >&2
  exit 2
fi
unset_=(-u SUDO_COMMAND -u SUDO_USER -u SUDO_UID -u SUDO_GID -u SUDO_HOME) set_=()
for name in PATH HOME USER LOGNAME; do
  if [ -n "${!name+set}" ]; then set_+=("$name=${!name}"); else unset_+=(-u "$name"); fi
done
# shellcheck disable=SC2016 # the inner script's own parameters
exec sudo --preserve-env -- unshare --net --setgid "$(id -g)" --setuid "$(id -u)" -- \
  env "${unset_[@]}" "${set_[@]}" \
  bash -c 'umask "$1" && shift && exec -- "$@"' offline.sh "$(umask)" "$@"
