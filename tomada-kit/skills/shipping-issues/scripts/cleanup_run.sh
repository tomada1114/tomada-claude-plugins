#!/usr/bin/env bash
# End-of-run cleanup for shipping-issues. The ONLY deletion entry point the
# skill uses — the main loop and sub-agents never call rm / git worktree remove
# / git branch -D ad hoc (raw rm trips the permission prompt and stalls runs).
#
# Deletes, strictly and only:
#   1. Agent worktrees under <repo>/.claude/worktrees/  (git worktree remove)
#      - a worktree with modified/untracked files is SKIPPED and listed unless
#        --force is given (salvage wanted files first, then rerun with --force)
#      - by default EVERY worktree under that root is removed, including one a
#        concurrent session is still working in. Pass --merged-only to remove
#        just the worktrees whose branch's PR is merged (with no open PR on the
#        same ref) — the safe mode when other sessions may be running.
#      - NOTE: gitignored files inside a worktree do not block removal and are
#        lost — agents must copy such artifacts to the main checkout first
#   2. Local branches: harness-internal worktree-agent-*, and branches whose
#      PR is MERGED (per gh) with no other open PR on the same ref
#   3. With --remote: the same merged refs on origin (never the default branch)
#
# Usage: cleanup_run.sh [--dry-run] [--force] [--remote] [--merged-only]
set -euo pipefail

force=0 remote=0 dry=0 merged_only=0
for a in "$@"; do
  case "$a" in
    --force) force=1 ;;
    --remote) remote=1 ;;
    --dry-run) dry=1 ;;
    --merged-only) merged_only=1 ;;
    *) echo "unknown flag: $a" >&2; exit 2 ;;
  esac
done

run() { if [ "$dry" -eq 1 ]; then echo "DRY: $*"; else "$@"; fi; }

# --show-toplevel answers with the *current* worktree, so running this from
# inside one of the agent worktrees resolves wt_root to a path that does not
# exist: the worktree pass then finds nothing and silently skips, while the
# branch pass still runs against the shared refs. That combination deletes
# merged branches and leaves every worktree in place, which reads as success.
# --path-format=absolute --git-common-dir always points at the main .git.
repo_root=$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")
wt_root="$repo_root/.claude/worktrees"
default_branch=$(git -C "$repo_root" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')
default_branch=${default_branch:-main}

# Both the worktree pass and the branch pass need these, so resolve them once.
merged_refs=$(gh pr list --state merged --limit 200 --json headRefName -q '.[].headRefName' | sort -u)
open_refs=$(gh pr list --state open --limit 200 --json headRefName -q '.[].headRefName' | sort -u)

deletable() {  # ref is merged-PR-backed and not reused by an open PR
  printf '%s\n' "$merged_refs" | grep -qxF "$1" &&
    ! printf '%s\n' "$open_refs" | grep -qxF "$1"
}

# --- 1. agent worktrees -----------------------------------------------------
git -C "$repo_root" worktree list --porcelain | awk '/^worktree /{print $2}' |
while IFS= read -r wt; do
  case "$wt" in "$wt_root"/*) ;; *) continue ;; esac
  if [ "$merged_only" -eq 1 ]; then
    wt_branch=$(git -C "$wt" symbolic-ref --short HEAD 2>/dev/null || true)
    if [ -z "$wt_branch" ]; then
      echo "SKIPPED (--merged-only, detached HEAD): $wt"
      continue
    fi
    if ! deletable "$wt_branch"; then
      echo "SKIPPED (--merged-only, PR not merged): $wt [$wt_branch]"
      continue
    fi
  fi
  if [ "$force" -eq 0 ] && [ -n "$(git -C "$wt" status --porcelain)" ]; then
    echo "SKIPPED (dirty — salvage, then rerun with --force): $wt"
    continue
  fi
  run git -C "$repo_root" worktree remove --force "$wt"
  echo "removed worktree: $wt"
done
run git -C "$repo_root" worktree prune

# --- 2. branches ------------------------------------------------------------
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
