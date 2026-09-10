#!/usr/bin/env bash
# ci_watch.sh — Wait for a PR's checks to settle and report a compact verdict.
#
# Usage: ci_watch.sh <pr-number> [--timeout SECONDS] [--log-bytes N]
#
# Prints:
#   verdict: PASS | FAIL | TIMEOUT | NO_CHECKS | ERROR
#   check_source: checks | actions+statuses  (which API the verdict came from)
#   mergeable / merge_state / review_decision
#   on FAIL: the failing check names plus the tail of each failing run's log
#   ERROR means the check results could not be read at all — never a green
#
# Two ways to read a PR's CI, because one of them needs a permission not every
# token can hold. GitHub's fine-grained PATs have no Checks permission at all —
# it is absent from the permission list and from the token-creation UI — so for
# such a token `gh pr checks` and `gh pr view --json statusCheckRollup` both
# fail with "Resource not accessible by personal access token". This script
# probes the check-runs API once and, when it is unreadable, falls back to what
# a fine-grained PAT can read: the Actions runs for the PR's head commit
# (Actions permission) plus that commit's statuses (Commit statuses
# permission). `check_source` always says which one answered.
#
# Exit codes: 0 = PASS, 1 = FAIL, 2 = TIMEOUT, 3 = NO_CHECKS,
#             4 = usage/lookup error or ERROR

set -uo pipefail

# print_help — the script's own usage, derived straight from this header
# comment so the text lives in exactly one place. Must run BEFORE the
# positional PR argument below is consumed, or `ci_watch.sh --help` sets
# PR="--help" and forwards it straight to `gh` instead of showing this.
print_help() {
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}"
}
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  print_help
  exit 0
fi

PR="${1:-}"
TIMEOUT=1800
LOG_BYTES=6000
POLL_INTERVAL=20
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --timeout) [[ $# -ge 2 ]] || { echo "--timeout needs a value" >&2; exit 4; }; TIMEOUT="$2"; shift 2 ;;
    --log-bytes) [[ $# -ge 2 ]] || { echo "--log-bytes needs a value" >&2; exit 4; }; LOG_BYTES="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 4 ;;
  esac
done

if [[ -z "$PR" ]]; then
  echo "Usage: ci_watch.sh <pr-number> [--timeout SECONDS] [--log-bytes N]" >&2
  exit 4
fi

CHECK_SOURCE="checks"
HEAD_SHA=""

report_source() {
  echo "check_source: $CHECK_SOURCE"
  [[ -n "$HEAD_SHA" ]] && echo "head_sha: $HEAD_SHA"
  return 0
}

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

GH_ERR="$(mktemp)"
trap 'rm -f "$GH_ERR"' EXIT

# --- can this token read check runs at all? --------------------------------
rollup="$(gh pr view "$PR" --json statusCheckRollup -q '.statusCheckRollup | length' 2>"$GH_ERR")"
rollup_rc=$?
if [[ $rollup_rc -ne 0 ]]; then
  rollup_err="$(tr '\n' ' ' <"$GH_ERR" | sed 's/  */ /g; s/ *$//')"
  # Two very different failures land here, and conflating them sends the
  # reader after the wrong problem: the PR may not be readable at all, or
  # (the fine-grained PAT case) the PR reads fine and only its check runs
  # are forbidden. Reading the head commit tells them apart, and it is the
  # value the fallback needs anyway. It has to be a field `gh` cannot answer
  # locally — `--json number` just echoes the number back without ever
  # reaching GitHub, so it succeeds even for a PR that does not exist.
  HEAD_SHA="$(gh pr view "$PR" --json headRefOid -q '.headRefOid' 2>/dev/null)"
  if [[ -z "$HEAD_SHA" ]]; then
    echo "verdict: ERROR"
    echo "detail: could not read PR #$PR: ${rollup_err:-gh exited $rollup_rc}"
    exit 4
  fi
  CHECK_SOURCE="actions+statuses"
  echo "note: check runs are not readable by this token, using Actions runs" \
       "+ commit statuses instead: ${rollup_err:-gh exited $rollup_rc}" >&2
fi

if [[ "$CHECK_SOURCE" == "checks" ]]; then
  # --- does this PR have any checks at all? --------------------------------
  if [[ "$rollup" == "0" || -z "$rollup" ]]; then
    # Give GitHub a moment to register freshly-triggered workflows.
    sleep 20
    rollup="$(gh pr view "$PR" --json statusCheckRollup -q '.statusCheckRollup | length' 2>/dev/null)"
  fi
  if [[ "$rollup" == "0" || -z "$rollup" ]]; then
    echo "verdict: NO_CHECKS"
    report_source
    report_pr_state
    exit 3
  fi

  # --- wait for checks to settle -------------------------------------------
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
    echo "timeout_enforced: no (no timeout/gtimeout on PATH — install coreutils for gtimeout)" >&2
    gh pr checks "$PR" --watch --interval 20 >/dev/null 2>&1
    rc=$?
  fi
  if [[ $rc -eq 124 ]]; then
    echo "verdict: TIMEOUT"
    report_source
    echo "waited_seconds: $TIMEOUT"
    gh pr checks "$PR" 2>/dev/null | sed 's/^/  /'
    report_pr_state
    exit 2
  fi

  # --- final verdict --------------------------------------------------------
  FAIL_STATES='["FAILURE","TIMED_OUT","CANCELLED","ACTION_REQUIRED","ERROR","STARTUP_FAILURE"]'
  failed_names="$(gh pr checks "$PR" --json name,state,link \
    -q "map(select(.state as \$s | $FAIL_STATES | index(\$s)))[] | [.name, .state, .link] | @tsv" \
    2>/dev/null)" || {
    echo "verdict: ERROR"
    report_source
    echo "detail: could not read check results for PR #$PR"
    report_pr_state
    exit 4
  }

  if [[ -z "$failed_names" ]]; then
    echo "verdict: PASS"
    report_source
    report_pr_state
    exit 0
  fi

  echo "verdict: FAIL"
  report_source
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
        log="$(gh run view "$run_id" --log-failed 2>/dev/null | tail -c "$LOG_BYTES")"
        if [[ -n "$log" ]]; then
          printf '%s\n' "$log" | sed 's/^/  /'
        else
          echo "  (no log available for run $run_id — gh run view --log-failed failed)"
        fi
      done
  exit 1
fi

# ---------------------------------------------------------------------------
# Fallback: Actions runs + commit statuses for the PR's head commit, which the
# probe above has already resolved into HEAD_SHA.
#
# Everything below reads only what a fine-grained PAT can hold. The head SHA
# rather than the head branch is the key, because it is what both APIs agree
# on and it stays correct for a PR opened from a fork.
# ---------------------------------------------------------------------------

# Each poll returns TSV so the settle test and the verdict can both read it
# without a second round trip.
#   runs:     databaseId  workflowName  status  conclusion  url
#   statuses: context     state         target_url
poll_runs() {
  gh run list --commit "$HEAD_SHA" --limit 100 \
    --json databaseId,workflowName,status,conclusion,url \
    -q '.[] | [.databaseId, .workflowName, .status, .conclusion, .url] | @tsv' 2>/dev/null
}

poll_statuses() {
  # The combined-status endpoint already collapses each context to its latest
  # status, so these rows need no further deduplication.
  gh api "repos/{owner}/{repo}/commits/$HEAD_SHA/status" \
    -q '.statuses[] | [.context, .state, .target_url] | @tsv' 2>/dev/null
}

# A run is unsettled until GitHub calls it "completed"; a commit status is
# unsettled while it is "pending".
has_pending() {
  local runs="$1" statuses="$2"
  # `exit` inside an awk rule still runs END, so the match has to be recorded
  # in a flag and turned into the exit status there — an `exit 0` in the rule
  # would be overwritten by END's own exit.
  if [[ -n "$runs" ]] && printf '%s\n' "$runs" \
      | awk -F'\t' '$3 != "completed" { found = 1; exit } END { exit !found }'; then
    return 0
  fi
  if [[ -n "$statuses" ]] && printf '%s\n' "$statuses" \
      | awk -F'\t' '$2 == "pending" { found = 1; exit } END { exit !found }'; then
    return 0
  fi
  return 1
}

print_check_table() {
  local runs="$1" statuses="$2"
  [[ -n "$runs" ]] && printf '%s\n' "$runs" \
    | awk -F'\t' '{print "  - " $2 " [" $3 ($4 == "" ? "" : "/" $4) "] " $5}'
  [[ -n "$statuses" ]] && printf '%s\n' "$statuses" \
    | awk -F'\t' '{print "  - " $1 " [" $2 "] " $3}'
  return 0
}

deadline=$(( $(date +%s) + TIMEOUT ))
empty_polls=0
runs=""
statuses=""
while :; do
  runs="$(poll_runs)"
  statuses="$(poll_statuses)"

  if [[ -z "$runs" && -z "$statuses" ]]; then
    # Nothing registered yet. One re-poll covers a freshly-triggered workflow
    # that GitHub has not surfaced; a second empty answer means there is
    # genuinely no CI on this commit.
    empty_polls=$(( empty_polls + 1 ))
    if (( empty_polls >= 2 )); then
      echo "verdict: NO_CHECKS"
      report_source
      report_pr_state
      exit 3
    fi
  else
    empty_polls=0
    has_pending "$runs" "$statuses" || break
  fi

  if (( $(date +%s) >= deadline )); then
    echo "verdict: TIMEOUT"
    report_source
    echo "waited_seconds: $TIMEOUT"
    print_check_table "$runs" "$statuses"
    report_pr_state
    exit 2
  fi
  sleep "$POLL_INTERVAL"
done

failed_runs=""
if [[ -n "$runs" ]]; then
  # "neutral", "skipped" and "stale" are completions that do not fail a PR.
  failed_runs="$(printf '%s\n' "$runs" | awk -F'\t' '
    $4 == "failure" || $4 == "timed_out" || $4 == "cancelled" ||
    $4 == "action_required" || $4 == "startup_failure" { print }')"
fi
failed_statuses=""
if [[ -n "$statuses" ]]; then
  failed_statuses="$(printf '%s\n' "$statuses" | awk -F'\t' '
    $2 == "failure" || $2 == "error" { print }')"
fi

if [[ -z "$failed_runs" && -z "$failed_statuses" ]]; then
  echo "verdict: PASS"
  report_source
  report_pr_state
  exit 0
fi

echo "verdict: FAIL"
report_source
echo "failed_checks:"
print_check_table "$failed_runs" "$failed_statuses"
report_pr_state
echo ""
echo "failed_logs:"
# Only Actions runs have logs `gh run view` can fetch; a failing commit status
# points at whatever external system produced it, so it is listed above but
# not dumped here.
if [[ -n "$failed_runs" ]]; then
  printf '%s\n' "$failed_runs" | awk -F'\t' '{print $1}' | sort -u | head -5 \
    | while read -r run_id; do
        echo "--- run $run_id ---"
        log="$(gh run view "$run_id" --log-failed 2>/dev/null | tail -c "$LOG_BYTES")"
        if [[ -n "$log" ]]; then
          printf '%s\n' "$log" | sed 's/^/  /'
        else
          echo "  (no log available for run $run_id — gh run view --log-failed failed)"
        fi
      done
fi
exit 1
