#!/usr/bin/env bash
# land_pr.sh — Merge a green PR using the repo's preferred method, then verify
# that the issue it was supposed to close actually closed.
#
# Usage: land_pr.sh <pr-number> [--issue N] [--method squash|merge|rebase]
#                   [--auto] [--dry-run] [--no-link-check] [--no-ready]
#
# Without --method the script picks the first method the repository allows,
# preferring squash. With --auto it enables GitHub auto-merge instead of
# merging now (the right choice when reviews or checks still gate the PR).
#
# With --issue N the script does the issue-closing bookkeeping the whole skill
# exists for:
#   * before merging, it runs link_check.sh --fix, so a PR that forgot its
#     "Closes #N" keyword gets one instead of merging and orphaning the issue;
#   * after merging, it confirms the issue really is CLOSED, and closes it with
#     a back-reference comment if GitHub did not (squash merges into a
#     non-default base, keyword lost in a body edit, …).
#
# A draft PR cannot be merged at all — GitHub refuses with "Pull Request is
# still a draft" — so by default the script marks it ready for review (`gh pr
# ready`) right before merging. Pass --no-ready to report `result: DRAFT`
# instead of ready-ing it (the caller decides when a PR should stay draft).
#
# Exit codes: 0 = merged (or auto-merge armed), 1 = merge refused, 2 = usage

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PR="${1:-}"
ISSUE=""
METHOD=""
AUTO=0
DRY=0
LINK_CHECK=1
READY=1
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue) ISSUE="${2:?}"; ISSUE="${ISSUE#\#}"; shift 2 ;;
    --method) METHOD="${2:?}"; shift 2 ;;
    --auto) AUTO=1; shift ;;
    --dry-run) DRY=1; shift ;;
    --no-link-check) LINK_CHECK=0; shift ;;
    --no-ready) READY=0; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$PR" ]]; then
  echo "Usage: land_pr.sh <pr-number> [--issue N] [--method squash|merge|rebase] [--auto] [--dry-run]" >&2
  exit 2
fi

state="$(gh pr view "$PR" --json state -q .state 2>/dev/null)" || {
  echo "result: ERROR"; echo "detail: cannot read PR #$PR"; exit 1; }
if [[ "$state" == "MERGED" ]]; then
  echo "result: ALREADY_MERGED"
  # With --issue, fall through to the post-merge issue check below.
  [[ -z "$ISSUE" ]] && exit 0
fi
if [[ "$state" != "OPEN" && "$state" != "MERGED" ]]; then
  echo "result: NOT_OPEN"; echo "state: $state"; exit 1
fi

# --- 1. issue link (auto-close precondition) --------------------------------
if [[ -n "$ISSUE" && $LINK_CHECK -eq 1 && "$state" == "OPEN" ]]; then
  # --dry-run inspects only: never edit the PR body on a dry run.
  # (Written as two calls rather than an optional-flag array: bash 3.2, still
  # the system bash on macOS, treats "${empty[@]}" as unbound under `set -u`.)
  if [[ $DRY -eq 1 ]]; then
    link_out="$("$SCRIPT_DIR/link_check.sh" "$PR" --issue "$ISSUE" 2>&1)"; link_rc=$?
  else
    link_out="$("$SCRIPT_DIR/link_check.sh" "$PR" --issue "$ISSUE" --fix 2>&1)"; link_rc=$?
  fi
  printf '%s\n' "$link_out" | sed 's/^/  link| /'
  if [[ $DRY -eq 1 ]]; then
    :  # report only; the dry-run summary below still prints
  elif [[ $link_rc -eq 2 ]]; then
    echo "result: WRONG_BASE"
    echo "detail: retarget the PR at the default branch (gh pr edit $PR --base <default>), or issue #$ISSUE stays open"
    exit 1
  elif [[ $link_rc -ne 0 ]]; then
    echo "result: NOT_LINKED"
    echo "detail: merging now would leave issue #$ISSUE open — fix the link (or pass --no-link-check) and retry"
    exit 1
  fi
fi

# --- 1.5 draft check (merge precondition) ------------------------------------
if [[ "$state" == "OPEN" ]]; then
  is_draft="$(gh pr view "$PR" --json isDraft -q .isDraft 2>/dev/null)" || {
    echo "result: ERROR"; echo "detail: cannot read draft status for PR #$PR"; exit 1; }
  if [[ "$is_draft" == "true" ]]; then
    echo "draft: true"
    if [[ $DRY -eq 1 ]]; then
      :  # report only; a dry run never mutates the PR
    elif [[ $READY -eq 0 ]]; then
      echo "result: DRAFT"
      echo "detail: PR #$PR is a draft — mark it ready (gh pr ready $PR) and retry, or omit --no-ready"
      exit 1
    elif gh pr ready "$PR" >/dev/null 2>&1; then
      echo "draft: MARKED_READY"
    else
      echo "result: DRAFT"
      echo "detail: gh pr ready $PR failed — mark it ready by hand and retry"
      exit 1
    fi
  fi
fi

if [[ "$state" == "OPEN" ]]; then
  if [[ -z "$METHOD" ]]; then
    meta="$(gh repo view --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed 2>/dev/null)"
    if printf '%s' "$meta" | grep -q '"squashMergeAllowed":true'; then METHOD=squash
    elif printf '%s' "$meta" | grep -q '"mergeCommitAllowed":true'; then METHOD=merge
    elif printf '%s' "$meta" | grep -q '"rebaseMergeAllowed":true'; then METHOD=rebase
    else METHOD=squash
    fi
  fi
  echo "method: $METHOD"

  if [[ $DRY -eq 1 ]]; then
    echo "result: DRY_RUN"
    gh pr view "$PR" --json mergeable,mergeStateStatus,reviewDecision 2>/dev/null
    exit 0
  fi
fi

# --- 2. merge ---------------------------------------------------------------
# confirm_issue <result-label> — post-merge, make sure the issue really closed.
confirm_issue() {
  [[ -z "$ISSUE" ]] && return 0
  local st
  st="$(gh issue view "$ISSUE" --json state -q .state 2>/dev/null)"
  if [[ "$st" == "CLOSED" ]]; then
    echo "issue: CLOSED (#$ISSUE)"
    return 0
  fi
  if [[ -z "$st" ]]; then
    echo "issue: UNKNOWN (#$ISSUE — could not read state)"
    return 0
  fi
  # GitHub did not auto-close it. Close it here rather than leaving a merged
  # change with an open issue behind it.
  if gh issue close "$ISSUE" \
       --comment "Closed by #$PR (merged). Auto-close did not fire, so closing explicitly." \
       >/dev/null 2>&1; then
    echo "issue: CLOSED_MANUALLY (#$ISSUE — auto-close did not fire)"
  else
    echo "issue: STILL_OPEN (#$ISSUE — close it by hand)"
  fi
}

if [[ "$state" == "MERGED" ]]; then
  confirm_issue
  exit 0
fi

flags=("--$METHOD" "--delete-branch")
[[ $AUTO -eq 1 ]] && flags+=("--auto")

if out="$(gh pr merge "$PR" "${flags[@]}" 2>&1)"; then
  if [[ $AUTO -eq 1 ]]; then
    echo "result: AUTO_MERGE_ARMED"
    [[ -n "$ISSUE" ]] && echo "issue: PENDING (#$ISSUE closes when auto-merge lands)"
    exit 0
  fi
  final="$(gh pr view "$PR" --json state -q .state 2>/dev/null)"
  if [[ "$final" == "MERGED" ]]; then
    echo "result: MERGED"
    confirm_issue
    exit 0
  fi
  echo "result: MERGE_UNCONFIRMED"
  echo "state: $final"
  echo "$out" | sed 's/^/  /'
  exit 1
fi

# `gh pr merge` exited non-zero, which does NOT by itself mean the merge was
# refused: `--delete-branch` also deletes the local branch, and that step fails
# whenever a worktree still holds it — long after GitHub has already merged.
# Reporting that as MERGE_REFUSED sends the caller chasing a merge that landed,
# so ask GitHub what actually happened before calling it a refusal.
final="$(gh pr view "$PR" --json state -q .state 2>/dev/null)"
if [[ "$final" == "MERGED" ]]; then
  echo "result: MERGED"
  echo "note: merged; only post-merge branch cleanup failed (cleanup_run.sh handles it)"
  echo "$out" | sed 's/^/  /'
  confirm_issue
  exit 0
fi
if [[ $AUTO -eq 1 ]] &&
   [[ "$(gh pr view "$PR" --json autoMergeRequest -q '.autoMergeRequest != null' 2>/dev/null)" == "true" ]]; then
  echo "result: AUTO_MERGE_ARMED"
  echo "note: auto-merge is armed; only branch cleanup failed (cleanup_run.sh handles it)"
  echo "$out" | sed 's/^/  /'
  [[ -n "$ISSUE" ]] && echo "issue: PENDING (#$ISSUE closes when auto-merge lands)"
  exit 0
fi

echo "result: MERGE_REFUSED"
echo "$out" | sed 's/^/  /'
gh pr view "$PR" --json mergeable,mergeStateStatus,reviewDecision 2>/dev/null | sed 's/^/  /'
exit 1
