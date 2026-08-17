#!/usr/bin/env bash
# preflight.sh — Verify the repo is in a state where issues can be shipped.
#
# Usage: preflight.sh
#
# Prints a compact key: value report and exits non-zero if a hard blocker
# is present. Soft warnings are reported but do not fail.
#
# Exit codes:
#   0 = ready
#   1 = hard blocker (not a repo, gh missing/unauthenticated, no origin)

set -uo pipefail

fail=0
warn=0

emit() { printf '%s: %s\n' "$1" "$2"; }

# --- gh availability -------------------------------------------------------
if ! command -v gh >/dev/null 2>&1; then
  emit gh_cli "MISSING (install: brew install gh)"
  fail=1
else
  emit gh_cli "ok"
  if gh auth status >/dev/null 2>&1; then
    emit gh_auth "ok"
  else
    emit gh_auth "NOT_AUTHENTICATED (run: gh auth login)"
    fail=1
  fi
fi

# --- git repo --------------------------------------------------------------
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  emit git_repo "NOT_A_REPO"
  echo "verdict: BLOCKED"
  exit 1
fi
emit git_repo "ok"
emit repo_root "$(git rev-parse --show-toplevel)"

if ! git remote get-url origin >/dev/null 2>&1; then
  emit origin "MISSING"
  fail=1
else
  emit origin "$(git remote get-url origin)"
fi

emit current_branch "$(git rev-parse --abbrev-ref HEAD)"

dirty="$(git status --porcelain 2>/dev/null | head -20)"
if [[ -n "$dirty" ]]; then
  emit working_tree "DIRTY"
  emit dirty_files "$(git status --porcelain | wc -l | tr -d ' ')"
  printf '%s\n' "$dirty" | sed 's/^/  /'
  warn=1
else
  emit working_tree "clean"
fi

# --- repo metadata via gh --------------------------------------------------
if [[ $fail -eq 0 ]]; then
  meta="$(gh repo view --json nameWithOwner,defaultBranchRef,squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed,deleteBranchOnMerge 2>/dev/null)" || meta=""
  if [[ -n "$meta" ]]; then
    emit repo "$(printf '%s' "$meta" | grep -o '"nameWithOwner":"[^"]*"' | cut -d'"' -f4)"
    emit default_branch "$(printf '%s' "$meta" | grep -o '"defaultBranchRef":{"name":"[^"]*"' | cut -d'"' -f6)"
    methods=""
    printf '%s' "$meta" | grep -q '"squashMergeAllowed":true' && methods="$methods squash"
    printf '%s' "$meta" | grep -q '"mergeCommitAllowed":true'  && methods="$methods merge"
    printf '%s' "$meta" | grep -q '"rebaseMergeAllowed":true'  && methods="$methods rebase"
    emit merge_methods "${methods:-unknown}"
    printf '%s' "$meta" | grep -q '"deleteBranchOnMerge":true' \
      && emit delete_branch_on_merge "true" || emit delete_branch_on_merge "false"
  else
    emit repo "UNKNOWN (gh repo view failed)"
    fail=1
  fi

  # Branch protection on the default branch (best effort; needs admin scope).
  db="$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name 2>/dev/null || echo main)"
  prot="$(gh api "repos/{owner}/{repo}/branches/${db}/protection" 2>/dev/null)" || prot=""
  if [[ -z "$prot" ]]; then
    emit branch_protection "unknown_or_none"
  elif printf '%s' "$prot" | grep -q '"required_pull_request_reviews"'; then
    emit branch_protection "REVIEWS_REQUIRED (auto-merge will need --auto)"
  else
    emit branch_protection "present_no_review_requirement"
  fi
fi

# --- existing worktrees ----------------------------------------------------
wt="$(git worktree list 2>/dev/null | tail -n +2)"
[[ -n "$wt" ]] && { emit existing_worktrees "$(printf '%s\n' "$wt" | wc -l | tr -d ' ')"; printf '%s\n' "$wt" | sed 's/^/  /'; }

if [[ $fail -ne 0 ]]; then
  echo "verdict: BLOCKED"
  exit 1
fi
[[ $warn -ne 0 ]] && echo "verdict: READY_WITH_WARNINGS" || echo "verdict: READY"
exit 0
