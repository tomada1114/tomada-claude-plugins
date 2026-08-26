#!/usr/bin/env bash
# End-of-run cleanup for shipping-issues. The ONLY deletion entry point the
# skill uses — the main loop and sub-agents never call rm / git branch -D
# ad hoc (raw rm trips the permission prompt and stalls runs).
#
# Deletes, strictly and only:
#   1. Local branches: harness-internal worktree-agent-* (a leftover
#      branch-naming convention from the Claude Code harness, unrelated to
#      this skill's own git worktree usage — it doesn't create any), and
#      branches whose PR is MERGED (per gh) with no other open PR on the
#      same ref
#   2. With --remote: the same merged refs on origin (never the default branch)
#
# Usage: cleanup_run.sh [--dry-run] [--remote]
set -euo pipefail

remote=0 dry=0
for a in "$@"; do
  case "$a" in
    --remote) remote=1 ;;
    --dry-run) dry=1 ;;
    *) echo "unknown flag: $a" >&2; exit 2 ;;
  esac
done

run() { if [ "$dry" -eq 1 ]; then echo "DRY: $*"; else "$@"; fi; }

# --path-format=absolute --git-common-dir always points at the main .git,
# regardless of which directory this script is invoked from.
repo_root=$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")
default_branch=$(git -C "$repo_root" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')
default_branch=${default_branch:-main}

merged_refs=$(gh pr list --state merged --limit 200 --json headRefName -q '.[].headRefName' | sort -u)
open_refs=$(gh pr list --state open --limit 200 --json headRefName -q '.[].headRefName' | sort -u)

deletable() {  # ref is merged-PR-backed and not reused by an open PR
  printf '%s\n' "$merged_refs" | grep -qxF "$1" &&
    ! printf '%s\n' "$open_refs" | grep -qxF "$1"
}

# --- branches ----------------------------------------------------------------
current_branch=$(git -C "$repo_root" symbolic-ref --short HEAD 2>/dev/null || true)
git -C "$repo_root" branch --format='%(refname:short)' |
while IFS= read -r br; do
  [ "$br" = "$default_branch" ] && continue
  if [ "$br" = "$current_branch" ]; then
    echo "SKIPPED (checked out in the main checkout — switch to $default_branch and rerun): $br"
    continue
  fi
  case "$br" in
    worktree-agent-*) run git -C "$repo_root" branch -D "$br" || true; continue ;;
  esac
  if deletable "$br"; then
    run git -C "$repo_root" branch -D "$br" ||
      { echo "SKIPPED (branch -D failed): $br"; continue; }
    echo "deleted local branch: $br"
  fi
done

# --- remote branches (opt-in) --------------------------------------------
if [ "$remote" -eq 1 ]; then
  # Prune first: with delete_branch_on_merge, origin refs vanish at merge time
  # while the local remote-tracking refs linger; pushing a delete for one of
  # those fails ("remote ref does not exist") and would abort the whole script.
  run git -C "$repo_root" fetch --prune --quiet
  git -C "$repo_root" branch -r --format='%(refname:short)' |
  sed -n 's|^origin/||p' |
  while IFS= read -r br; do
    [ "$br" = "$default_branch" ] || [ "$br" = "HEAD" ] && continue
    if deletable "$br"; then
      run git -C "$repo_root" push origin --delete "$br" ||
        { echo "SKIPPED (push --delete failed — likely already gone on origin): $br"; continue; }
      echo "deleted remote branch: origin/$br"
    fi
  done
fi

run git -C "$repo_root" fetch --prune --quiet
echo "cleanup: done"
