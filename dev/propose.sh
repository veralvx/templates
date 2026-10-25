#!/usr/bin/env bash
# propose.sh <handover> <list> <branch> <title>: the change an update job handed over, proposed as
# a pull request against the branch the run is on (GITHUB_REF_NAME), on <branch>, which the next
# run rebuilds from it (made anew, a new pull request, if GitHub refuses the force-push) -- unless
# the branch holds a person's commit, left as it is, the step failing, until its pull request is
# merged or closed. locks.yml's and dprint-plugins.yml's `propose` jobs run it, from their own
# checkout: git and gh alone, nothing the change holds.
#   <handover>  a folder: `status` (`ok` once the update finished), `changes.patch` (`git diff
#               --cached --binary`; empty, nothing moved) and `summary.md` (the commit's body, the
#               pull request's)
#   <list>      the paths the change may touch (dev/unlisted.sh's patterns), read as this checkout
#               holds it, as is the matcher, before the change is applied: the change can widen
#               neither, nor run its own; and it may only change their content, files tracked here
#   <title>     the commit's subject, its scopes `shared` added when the change touches shared/
#               (AGENTS.md's): `build(typst): ...` becomes `build(typst,shared): ...`
# Env: BOT, the committer's email (github-actions[bot]'s); GH_TOKEN, GITHUB_REF_NAME and
# GITHUB_REPOSITORY, the job's.
set -euo pipefail

if [ "$#" -ne 4 ]; then
  echo "usage: propose.sh <handover> <list> <branch> <title>" >&2
  exit 2
fi
handover="$1" list="$2" branch="$3" title="$4"
patch="$handover/changes.patch" summary="$handover/summary.md"
: "${BOT:?}" "${GITHUB_REF_NAME:?}" "${GITHUB_REPOSITORY:?}"
if [ "$(cat "$handover/status")" != ok ]; then
  echo "The update failed (its job says why): nothing to propose."
  exit 0
fi
if [ ! -s "$patch" ]; then
  echo "Nothing moved: no pull request."
  exit 0
fi

# the matcher and the list as committed, set aside before the change touches the tree: what it may
# write is the update's (its inputs' code ran there), never run nor trusted here
held="$(mktemp -d)"
trap 'rm -rf "$held"' EXIT
git show HEAD:dev/unlisted.sh > "$held/unlisted.sh"
git show "HEAD:$list" > "$held/list"
git apply --index "$patch"
# what <list> lets through alone: anything else the update wrote is refused, not proposed -- a
# rename as both its paths, a path git quotes as no pattern's
outside="$(git diff --cached --name-only --no-renames | bash "$held/unlisted.sh" "$held/list")"
if [ -n "$outside" ]; then
  echo "::error::the update changed what $list does not list: ${outside//$'\n'/, }" >&2
  exit 1
fi
# and its content alone, of files this checkout tracks: an update formats or rewrites what is
# there, so a file added, deleted, made a link or given another mode is refused, listed or not
# (git's answer taken first: a git failure, grep reading nothing, would pass for "none")
statuses="$(git diff --cached --name-status --no-renames)"
other="$(grep --invert-match '^M' <<< "$statuses" || [ $? -eq 1 ])"
modes="$(git diff --cached --summary | sed -n 's/^ *\(mode change .*\)$/\1/p')"
if [ -n "$other$modes" ]; then
  echo "::error::the update did more than change tracked files' content: ${other//$'\n'/, }${other:+${modes:+, }}${modes//$'\n'/, }" >&2
  exit 1
fi
if ! git diff --cached --quiet -- shared/; then title="${title/)/,shared)}"; fi
# the branch's tip now (none: empty), before its authors are read: the push is leased on it, so a
# commit pushed since is never overwritten
lease="$(git ls-remote origin "refs/heads/$branch" | cut --fields=1)"
# its open pull request from this repository, if any (gh failing fails the step: a lost answer is
# no "none"), and each of its commits' authors
open="$(gh pr list --head "$branch" --state open --json number,isCrossRepository \
  --jq 'map(select(.isCrossRepository | not)) | .[0].number // empty')"
if [ -n "$open" ]; then
  authors="$(gh pr view "$open" --json commits --jq '.commits[].authors[].email')"
  # and the committer of the tip the push would replace (the lease), which gh does not give: one
  # who amended the bot's commit is a person too. No branch, nothing to keep; a fetch failing, or a
  # tip moved since the lease, fails the step: a lost answer is no "none"
  tip=""
  if [ -n "$lease" ]; then
    git fetch --quiet --no-tags --depth=1 origin "refs/heads/$branch"
    tip="$(git rev-parse FETCH_HEAD)"
    if [ "$tip" != "$lease" ]; then
      echo "::error::$branch moved while it was read: run again" >&2
      exit 1
    fi
    authors="${authors:+$authors$'\n'}$(git log -1 --format=%ce "$tip")"
  fi
  if grep --quiet --invert-match --line-regexp --fixed-strings "$BOT" <<< "$authors"; then
    # red, so a scheduled run is seen
    echo "::error::$branch holds a person's commit: left as it is -- merge or close #$open, and the next run proposes again"
    exit 1
  fi
  if [ -n "$tip" ] && [ "$(git rev-parse "$tip^{tree}")" = "$(git write-tree)" ]; then
    echo "#$open already holds this change: nothing pushed."
    exit 0
  fi
fi
git switch --force-create "$branch"
{
  printf '%s\n\n' "$title"
  cat "$summary"
} |
  git -c user.name="github-actions[bot]" -c user.email="$BOT" commit --quiet --file=-
# GitHub may refuse moving the branch across workflow changes on the default branch (a
# GITHUB_TOKEN push has no `workflows` permission): then, and only then -- any other failure stops
# here -- it is made anew, which closes its pull request, and a new one is opened
pushed=0
git push --force-with-lease="refs/heads/$branch:$lease" origin "$branch" 2>&1 | tee "$held/push.log" || pushed=$?
if [ "$pushed" -ne 0 ]; then
  if ! grep --quiet "to create or update workflow" "$held/push.log"; then exit "$pushed"; fi
  echo "::warning::$branch: the force-push was refused (the workflows); deleted and pushed anew"
  git push --force-with-lease="refs/heads/$branch:$lease" origin --delete "$branch"
  git push origin "$branch"
  open=""
fi
if [ -n "$open" ]; then
  gh api --method PATCH "repos/$GITHUB_REPOSITORY/pulls/$open" -f title="$title" -F body=@"$summary" > /dev/null
  echo "Pull request #$open updated."
else
  gh pr create --base "$GITHUB_REF_NAME" --head "$branch" --title "$title" --body-file "$summary"
fi
