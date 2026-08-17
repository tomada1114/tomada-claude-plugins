#!/usr/bin/env bash
# ci_watch.sh — Wait for a PR's checks to settle and report a compact verdict.
#
# Usage: ci_watch.sh <pr-number> [--timeout SECONDS] [--log-bytes N]
#
# Prints:
#   verdict: PASS | FAIL | TIMEOUT | NO_CHECKS
#   mergeable / merge_state / review_decision
#   on FAIL: the failing check names plus the tail of each failing run's log
#
# Exit codes: 0 = PASS, 1 = FAIL, 2 = TIMEOUT, 3 = NO_CHECKS, 4 = usage/lookup error

set -uo pipefail

PR="${1:-}"
TIMEOUT=1800
LOG_BYTES=6000
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --timeout) TIMEOUT="${2:?}"; shift 2 ;;
    --log-bytes) LOG_BYTES="${2:?}"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 4 ;;
  esac
done

if [[ -z "$PR" ]]; then
  echo "Usage: ci_watch.sh <pr-number> [--timeout SECONDS] [--log-bytes N]" >&2
  exit 4
fi

report_pr_state() {
  local v
  # GitHub computes mergeability lazily; the first read after a push is often
  # UNKNOWN. One retry is enough to get the real state.
  v="$(gh pr view "$PR" --json mergeable,mergeStateStatus,reviewDecision,isDraft,state 2>/dev/null)" || return
  if printf '%s' "$v" | grep -q '"mergeable":"UNKNOWN"'; then
    sleep 5
    v="$(gh pr view "$PR" --json mergeable,mergeStateStatus,reviewDecision,isDraft,state 2>/dev/null)" || return
  fi
  echo "pr_state: $(printf '%s' "$v" | grep -o '"state":"[^"]*"' | cut -d'"' -f4)"
  echo "draft: $(printf '%s' "$v" | grep -o '"isDraft":[a-z]*' | cut -d: -f2)"
  echo "mergeable: $(printf '%s' "$v" | grep -o '"mergeable":"[^"]*"' | cut -d'"' -f4)"
  echo "merge_state: $(printf '%s' "$v" | grep -o '"mergeStateStatus":"[^"]*"' | cut -d'"' -f4)"
  echo "review_decision: $(printf '%s' "$v" | grep -o '"reviewDecision":"[^"]*"' | cut -d'"' -f4)"
}

# --- does this PR have any checks at all? ---------------------------------
rollup="$(gh pr view "$PR" --json statusCheckRollup -q '.statusCheckRollup | length' 2>/dev/null)" || {
  echo "verdict: ERROR"
  echo "detail: could not read PR #$PR"
  exit 4
}
if [[ "$rollup" == "0" || -z "$rollup" ]]; then
  # Give GitHub a moment to register freshly-triggered workflows.
  sleep 20
  rollup="$(gh pr view "$PR" --json statusCheckRollup -q '.statusCheckRollup | length' 2>/dev/null)"
fi
if [[ "$rollup" == "0" || -z "$rollup" ]]; then
  echo "verdict: NO_CHECKS"
  report_pr_state
  exit 3
fi

# --- wait for checks to settle --------------------------------------------
# `gh pr checks --watch` blocks until all checks complete; wrap it in a hard
# timeout so a hung workflow cannot stall the run forever.
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_BIN=timeout
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_BIN=gtimeout
else
  TIMEOUT_BIN=""
fi

if [[ -n "$TIMEOUT_BIN" ]]; then
  "$TIMEOUT_BIN" "$TIMEOUT" gh pr checks "$PR" --watch --interval 20 >/dev/null 2>&1
  rc=$?
else
  gh pr checks "$PR" --watch --interval 20 >/dev/null 2>&1
  rc=$?
fi
if [[ $rc -eq 124 ]]; then
  echo "verdict: TIMEOUT"
  echo "waited_seconds: $TIMEOUT"
  gh pr checks "$PR" 2>/dev/null | sed 's/^/  /'
  report_pr_state
  exit 2
fi

# --- final verdict ---------------------------------------------------------
FAIL_STATES='["FAILURE","TIMED_OUT","CANCELLED","ACTION_REQUIRED","ERROR","STARTUP_FAILURE"]'
failed_names="$(gh pr checks "$PR" --json name,state,link \
  -q "map(select(.state as \$s | $FAIL_STATES | index(\$s)))[] | [.name, .state, .link] | @tsv" \
  2>/dev/null)"

if [[ -z "$failed_names" ]]; then
  echo "verdict: PASS"
  report_pr_state
  exit 0
fi

echo "verdict: FAIL"
echo "failed_checks:"
printf '%s\n' "$failed_names" | awk -F'\t' '{print "  - " $1 " [" $2 "] " $3}'
report_pr_state
echo ""
echo "failed_logs:"
# Collect the failing run IDs from the check links and dump only failed steps.
printf '%s\n' "$failed_names" | awk -F'\t' '{print $3}' \
  | grep -oE '/runs/[0-9]+' | grep -oE '[0-9]+' | sort -u | head -5 \
  | while read -r run_id; do
      echo "--- run $run_id ---"
      gh run view "$run_id" --log-failed 2>/dev/null | tail -c "$LOG_BYTES" | sed 's/^/  /'
    done
exit 1
