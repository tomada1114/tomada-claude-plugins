#!/usr/bin/env bash
# End-of-run cleanup for shipping-issues. The ONLY deletion entry point the
# skill uses — the main loop and sub-agents never call rm / git worktree
# remove / git branch -D ad hoc (raw rm trips the permission prompt and
# stalls runs).
#
# Deletes, strictly and only:
#   1. With --worktree-root <root>: linked worktrees under <root>/ (see the
#      worktree pass below). Gitignored files inside a worktree (node_modules,
#      caches, ...) do NOT block removal and are LOST with it — anything worth
#      keeping must be copied to the main checkout before cleanup.
#   2. Local branches: harness-internal worktree-agent-* (a leftover
#      branch-naming convention from the Claude Code harness — unrelated to
#      this skill's own git worktree usage, added above), and branches whose
#      PR is MERGED (per gh) with no other open PR on the same ref
#   3. With --remote: the same merged refs that actually exist on origin, read
#      via `git ls-remote --heads origin` rather than local remote-tracking
#      refs — a ref delete-on-merge already removed on origin can still
#      linger as a local remote-tracking ref between fetches, and reading
#      those would list a deletion that would not actually happen, especially
#      under --dry-run where the fetch --prune below is only echoed, never run
#      (never the default branch)
#
# With one or more --branch <name>: the local-branch pass and the remote pass
# (with --remote) consider ONLY the named branches — each still subject to
# every guard above (merged PR, no open PR on the ref, not the default
# branch, not checked out in the main checkout or a surviving worktree) — and
# the automatic worktree-agent-* local pass is skipped, so a named
# worktree-agent-* branch is deleted only if it independently clears the
# merged-PR guard. Without --branch, behavior is unchanged. The worktree pass
# (item 1) is unaffected either way — it is already scoped by --worktree-root.
#
# Usage: cleanup_run.sh [--dry-run] [--remote] [--worktree-root <path>]
#                        [--merged-only] [--force] [--branch <name> ...]
set -euo pipefail

# print_help — the script's own usage, derived straight from this header
# comment so the text lives in exactly one place.
print_help() {
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}"
}

remote=0 dry=0 merged_only=0 force=0
worktree_root=""
wanted_branches=()
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) print_help; exit 0 ;;
    --remote) remote=1; shift ;;
    --dry-run) dry=1; shift ;;
    --merged-only) merged_only=1; shift ;;
    --force) force=1; shift ;;
    --worktree-root)
      [ $# -ge 2 ] || { echo "--worktree-root requires a value" >&2; exit 2; }
      worktree_root=$2
      shift 2
      ;;
    --branch)
      [ $# -ge 2 ] || { echo "--branch requires a value" >&2; exit 2; }
      wanted_branches+=("$2")
      shift 2
      ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
done

run() { if [ "$dry" -eq 1 ]; then echo "DRY: $*"; else "$@"; fi; }

# --path-format=absolute --git-common-dir always points at the main .git,
# regardless of which directory this script is invoked from.
repo_root=$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")
# `|| true`: origin/HEAD is set by `git clone`, but NOT by `git remote add` +
# fetch, so plenty of real repos lack it. Under `set -e` with `pipefail` the
# failing `symbolic-ref` would take the whole substitution's exit status with
# it and abort the script here — silently, before printing a single line, and
# leaving the `:-main` fallback below unreachable.
default_branch=$(git -C "$repo_root" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||' || true)
default_branch=${default_branch:-main}

merged_refs=$(gh pr list --state merged --limit 200 --json headRefName -q '.[].headRefName' | sort -u)
open_refs=$(gh pr list --state open --limit 200 --json headRefName -q '.[].headRefName' | sort -u)

deletable() {  # ref is merged-PR-backed and not reused by an open PR
  printf '%s\n' "$merged_refs" | grep -qxF "$1" &&
    ! printf '%s\n' "$open_refs" | grep -qxF "$1"
}

# --- worktrees (must run BEFORE the branch pass) -----------------------------
# A branch checked out in a worktree cannot be `git branch -D`'d, so removing
# worktrees first is what lets the branch pass below actually delete them.
surviving_worktrees=""
if [ -z "$worktree_root" ]; then
  echo "worktree pass: skipped (no --worktree-root given — single-issue mode does not use worktrees)"
else
  # Resolve to an absolute, symlink-free, trailing-slash-free root for prefix
  # matching: `git worktree list --porcelain` reports canonicalized (physical)
  # paths, so a logical (non -P) resolution here would silently never match
  # on a system where the root sits behind a symlink (e.g. macOS /var ->
  # /private/var).
  worktree_root=$(cd "$worktree_root" 2>/dev/null && pwd -P || echo "$worktree_root")
  wt_path="" wt_branch="" wt_detached=0
  process_worktree() {
    [ -n "$wt_path" ] || return 0
    case "$wt_path" in
      "$repo_root") return 0 ;;  # never touch the main checkout
      "$worktree_root"/*) ;;
      *) return 0 ;;  # outside the given root — never touch it
    esac
    if [ "$merged_only" -eq 1 ]; then
      if [ "$wt_detached" -eq 1 ]; then
        echo "SKIPPED (detached HEAD): $wt_path"
        surviving_worktrees="$surviving_worktrees $wt_path"
        return 0
      fi
      if ! deletable "$wt_branch"; then
        echo "SKIPPED (no merged PR / open PR on $wt_branch): $wt_path"
        surviving_worktrees="$surviving_worktrees $wt_path"
        return 0
      fi
    fi
    if [ "$force" -ne 1 ] && [ -n "$(git -C "$wt_path" status --porcelain 2>/dev/null)" ]; then
      echo "SKIPPED (dirty — salvage, then rerun with --force): $wt_path"
      surviving_worktrees="$surviving_worktrees $wt_path"
      return 0
    fi
    # The script's own --force (above) governs the dirty check; the --force on
    # the `git worktree remove` command below is a separate, unconditional
    # thing — it's required even for a CLEAN worktree because gitignored files
    # (node_modules, caches, ...) make plain `git worktree remove` refuse.
    # Do not "simplify" this to one flag.
    run git -C "$repo_root" worktree remove --force "$wt_path" ||
      { echo "SKIPPED (worktree remove failed): $wt_path"; surviving_worktrees="$surviving_worktrees $wt_path"; return 0; }
    echo "removed worktree: $wt_path"
  }
  while IFS= read -r line; do
    case "$line" in
      "worktree "*) process_worktree; wt_path=${line#worktree }; wt_branch=""; wt_detached=0 ;;
      "branch "*) wt_branch=${line#branch refs/heads/} ;;
      "detached") wt_detached=1 ;;
      "") : ;;
    esac
  done < <(git -C "$repo_root" worktree list --porcelain)
  process_worktree  # flush the last entry
  run git -C "$repo_root" worktree prune
fi

# --- branches ----------------------------------------------------------------
current_branch=$(git -C "$repo_root" symbolic-ref --short HEAD 2>/dev/null || true)
if [ ${#wanted_branches[@]} -gt 0 ]; then
  branch_list=$(printf '%s\n' "${wanted_branches[@]}")
else
  branch_list=$(git -C "$repo_root" branch --format='%(refname:short)')
fi
printf '%s\n' "$branch_list" |
while IFS= read -r br; do
  [ -n "$br" ] || continue
  [ "$br" = "$default_branch" ] && continue
  # A named branch may already be gone locally (the merge deleted it); without
  # this, a dry run proposes a deletion that would only fail.
  git -C "$repo_root" show-ref --verify --quiet "refs/heads/$br" || continue
  if [ "$br" = "$current_branch" ]; then
    echo "SKIPPED (checked out in the main checkout — switch to $default_branch and rerun): $br"
    continue
  fi
  checked_out_in=""
  for wt in $surviving_worktrees; do
    wt_br=$(git -C "$wt" symbolic-ref --short HEAD 2>/dev/null || true)
    if [ "$wt_br" = "$br" ]; then
      checked_out_in="$wt"
      break
    fi
  done
  if [ -n "$checked_out_in" ]; then
    echo "SKIPPED (checked out in worktree $checked_out_in): $br"
    continue
  fi
  # The automatic worktree-agent-* pass bypasses the merged-PR guard below —
  # fine for an unscoped run, but a --branch run means the caller named
  # exactly what this run's own branches were, so even a worktree-agent-*
  # name must still clear the same guard as everything else.
  if [ ${#wanted_branches[@]} -eq 0 ]; then
    case "$br" in
      worktree-agent-*) run git -C "$repo_root" branch -D "$br" || true; continue ;;
    esac
  fi
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
  # Under --dry-run this is only echoed, never actually run — which is exactly
  # why the enumeration below reads origin directly rather than trusting the
  # (possibly stale) local remote-tracking refs this prune would have cleaned.
  run git -C "$repo_root" fetch --prune --quiet
  # What actually exists on origin right now, not local remote-tracking refs:
  # a ref already deleted on origin (delete-on-merge, or someone else's
  # cleanup) can still linger locally between fetches, and listing from the
  # local refs would report a deletion that would not actually happen.
  remote_heads=$(git -C "$repo_root" ls-remote --heads origin | sed -n 's|^.*\trefs/heads/||p')
  if [ ${#wanted_branches[@]} -gt 0 ]; then
    remote_source=$(printf '%s\n' "${wanted_branches[@]}")
  else
    remote_source="$remote_heads"
  fi
  printf '%s\n' "$remote_source" |
  while IFS= read -r br; do
    [ -n "$br" ] || continue
    [ "$br" = "$default_branch" ] && continue
    # Only ever act on a ref ls-remote actually reported — this is what keeps
    # a --branch name absent from origin, or a stale local remote-tracking
    # ref, out of the list entirely.
    printf '%s\n' "$remote_heads" | grep -qxF "$br" || continue
    if deletable "$br"; then
      run git -C "$repo_root" push origin --delete "$br" ||
        { echo "SKIPPED (push --delete failed — likely already gone on origin): $br"; continue; }
      echo "deleted remote branch: origin/$br"
    fi
  done
fi

run git -C "$repo_root" fetch --prune --quiet
echo "cleanup: done"
