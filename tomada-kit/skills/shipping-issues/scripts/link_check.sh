#!/usr/bin/env bash
# link_check.sh — Verify a PR will auto-close its issue when it merges.
#
# GitHub only closes an issue automatically when BOTH hold:
#   1. the PR body (or a commit message) carries a closing keyword —
#      "Closes #N" / "Fixes #N" / "Resolves #N" — and
#   2. the PR merges into the repository's DEFAULT branch.
# A PR that merely says "see #N", or one targeting a non-default base, leaves
# the issue open. This script checks both and can repair case 1.
#
# Usage: link_check.sh <pr-number> [--issue N] [--fix]
#
#   --issue N   require that issue #N specifically is in the closing set
#   --fix       if it is not, append "Closes #N" to the PR body and re-check
#
# Prints:
#   verdict: LINKED | NOT_LINKED | WRONG_BASE | ERROR
#   closes: #N,#M | none
#   base: <branch> (default: <branch>)
#
# Exit codes: 0 = LINKED, 1 = NOT_LINKED, 2 = WRONG_BASE, 3 = usage/lookup error

set -uo pipefail

PR="${1:-}"
ISSUE=""
FIX=0
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue) ISSUE="${2:?}"; ISSUE="${ISSUE#\#}"; shift 2 ;;
    --fix) FIX=1; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 3 ;;
  esac
done

if [[ -z "$PR" ]]; then
  echo "Usage: link_check.sh <pr-number> [--issue N] [--fix]" >&2
  exit 3
fi

closing_numbers() {
  gh pr view "$PR" --json closingIssuesReferences \
    -q '[.closingIssuesReferences[].number] | join(",")' 2>/dev/null
}

base_ref="$(gh pr view "$PR" --json baseRefName -q .baseRefName 2>/dev/null)" || base_ref=""
if [[ -z "$base_ref" ]]; then
  echo "verdict: ERROR"
  echo "detail: could not read PR #$PR"
  exit 3
fi
default_branch="$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name 2>/dev/null)"
default_branch="${default_branch:-main}"

closes="$(closing_numbers)"

# --- repair a missing closing keyword --------------------------------------
if [[ -n "$ISSUE" && $FIX -eq 1 ]] && ! printf ',%s,' "$closes" | grep -q ",$ISSUE,"; then
  tmp="$(mktemp -t link_check_body)" || { echo "verdict: ERROR"; echo "detail: mktemp failed"; exit 3; }
  gh pr view "$PR" --json body -q .body > "$tmp" 2>/dev/null
  printf '\n\nCloses #%s\n' "$ISSUE" >> "$tmp"
  if gh pr edit "$PR" --body-file "$tmp" >/dev/null 2>&1; then
    echo "fix: appended 'Closes #$ISSUE' to the PR body"
    # GitHub recomputes the link asynchronously; one short retry is enough.
    sleep 3
    closes="$(closing_numbers)"
  else
    echo "fix: FAILED (could not edit PR body)"
  fi
  rm -f "$tmp"
fi

echo "base: $base_ref (default: $default_branch)"
echo "closes: ${closes:-none}"

if [[ "$base_ref" != "$default_branch" ]]; then
  echo "verdict: WRONG_BASE"
  echo "detail: auto-close only fires when the PR merges into $default_branch"
  exit 2
fi

if [[ -z "$closes" ]]; then
  echo "verdict: NOT_LINKED"
  echo "detail: the PR body has no Closes/Fixes/Resolves keyword"
  exit 1
fi

if [[ -n "$ISSUE" ]] && ! printf ',%s,' "$closes" | grep -q ",$ISSUE,"; then
  echo "verdict: NOT_LINKED"
  echo "detail: PR closes #$closes but not the target issue #$ISSUE"
  exit 1
fi

echo "verdict: LINKED"
exit 0
