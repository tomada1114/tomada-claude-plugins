#!/usr/bin/env bash
# End-of-run cleanup for shipping-issues. The ONLY deletion entry point the
# skill uses — the main loop and sub-agents never call rm / git worktree remove
# / git branch -D ad hoc (raw rm trips the permission prompt and stalls runs).
#
# Deletes, strictly and only:
#   1. Agent worktrees under <repo>/.claude/worktrees/  (git worktree remove)
#      - a worktree with modified/untracked files is SKIPPED and listed unless
#        --force is given (salvage wanted files first, then rerun with --force)
#      - NOTE: gitignored files inside a worktree do not block removal and are
#        lost — agents must copy such artifacts to the main checkout first
#   2. Local branches: harness-internal worktree-agent-*, and branches whose
#      PR is MERGED (per gh) with no other open PR on the same ref
#   3. With --remote: the same merged refs on origin (never the default branch)
#
# Usage: cleanup_run.sh [--dry-run] [--force] [--remote]
set -euo pipefail

force=0 remote=0 dry=0
for a in "$@"; do
  case "$a" in
    --force) force=1 ;;
    --remote) remote=1 ;;
    --dry-run) dry=1 ;;
    *) echo "unknown flag: $a" >&2; exit 2 ;;
  esac
done

run() { if [ "$dry" -eq 1 ]; then echo "DRY: $*"; else "$@"; fi; }

repo_root=$(git rev-parse --show-toplevel)
wt_root="$repo_root/.claude/worktrees"
default_branch=$(git -C "$repo_root" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')
default_branch=${default_branch:-main}

# --- 1. agent worktrees -----------------------------------------------------
git -C "$repo_root" worktree list --porcelain | awk '/^worktree /{print $2}' |
while IFS= read -r wt; do
  case "$wt" in "$wt_root"/*) ;; *) continue ;; esac
  if [ "$force" -eq 0 ] && [ -n "$(git -C "$wt" status --porcelain)" ]; then
    echo "SKIPPED (dirty — salvage, then rerun with --force): $wt"
    continue
  fi
  run git -C "$repo_root" worktree remove --force "$wt"
  echo "removed worktree: $wt"
done
run git -C "$repo_root" worktree prune

# --- 2. branches ------------------------------------------------------------
merged_refs=$(gh pr list --state merged --limit 200 --json headRefName -q '.[].headRefName' | sort -u)
open_refs=$(gh pr list --state open --limit 200 --json headRefName -q '.[].headRefName' | sort -u)

deletable() {  # ref is merged-PR-backed and not reused by an open PR
  printf '%s\n' "$merged_refs" | grep -qxF "$1" &&
    ! printf '%s\n' "$open_refs" | grep -qxF "$1"
}

current_branch=$(git -C "$repo_root" symbolic-ref --short HEAD 2>/dev/null || true)
git -C "$repo_root" branch --format='%(refname:short)' |
while IFS= read -r br; do
  [ "$br" = "$default_branch" ] && continue
  if [ "$br" = "$current_branch" ]; then
    echo "SKIPPED (checked out in the main worktree — switch to $default_branch and rerun): $br"
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

# --- 3. remote branches (opt-in) --------------------------------------------
if [ "$remote" -eq 1 ]; then
  git -C "$repo_root" branch -r --format='%(refname:short)' |
  sed -n 's|^origin/||p' |
  while IFS= read -r br; do
    [ "$br" = "$default_branch" ] || [ "$br" = "HEAD" ] && continue
    if deletable "$br"; then
      run git -C "$repo_root" push origin --delete "$br"
      echo "deleted remote branch: origin/$br"
    fi
  done
fi

run git -C "$repo_root" fetch --prune --quiet
echo "cleanup: done"
