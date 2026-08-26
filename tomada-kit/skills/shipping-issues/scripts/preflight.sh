#!/usr/bin/env bash
# preflight.sh — Verify the local repo is in a state where issues can be shipped.
#
# Usage: preflight.sh
#
# Prints a compact key: value report and exits non-zero if a hard blocker
# is present. Soft warnings are reported but do not fail.
#
# This checks only the local git state. It makes no GitHub calls and does not
# check for `gh`, its login state, or any other way of reaching GitHub — later
# steps that actually need GitHub surface a problem on their own, at the point
# they hit it.
#
# Exit codes:
#   0 = ready
#   1 = hard blocker (not a repo, no origin)

set -uo pipefail

fail=0
warn=0

emit() { printf '%s: %s\n' "$1" "$2"; }

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

if [[ $fail -ne 0 ]]; then
  echo "verdict: BLOCKED"
  exit 1
fi
[[ $warn -ne 0 ]] && echo "verdict: READY_WITH_WARNINGS" || echo "verdict: READY"
exit 0
