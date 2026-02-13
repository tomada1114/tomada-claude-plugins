#!/usr/bin/env bash
set -euo pipefail

# tmux-orchestrating: Automated monitoring loop
# Wraps check-status.sh with polling, auto-select, nudge, and stall detection.
#
# Usage: bash monitor.sh [OPTIONS] SESSION_NAME PANE_COUNT [WORK_DIR]
#
# Options:
#   --interval N        Polling interval in seconds (default: 180)
#   --timeout N         Total timeout in seconds (default: 1200)
#   --initial-wait N    Wait before first check in seconds (default: 60)
#   --auto-select       Auto-send Enter when WaitingInput detected
#   --nudge-prompt TEXT  Prompt to send when IdleNoReport detected
#                        Use {N} as placeholder for pane number
#   --stall-threshold N  Consecutive identical checks before stall (default: 3)
#
# Exit codes:
#   0  All panes complete
#   1  Timeout
#   2  Stall detected

# --- Defaults ---
INTERVAL=180
TIMEOUT=1200
INITIAL_WAIT=60
AUTO_SELECT=false
NUDGE_PROMPT="You went idle without writing the report file. Please write queue/reports/pane{N}_report.md now with your results."
STALL_THRESHOLD=3

# --- Parse arguments ---
POSITIONAL=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --interval)     INTERVAL="$2"; shift 2 ;;
        --timeout)      TIMEOUT="$2"; shift 2 ;;
        --initial-wait) INITIAL_WAIT="$2"; shift 2 ;;
        --auto-select)  AUTO_SELECT=true; shift ;;
        --nudge-prompt) NUDGE_PROMPT="$2"; shift 2 ;;
        --stall-threshold) STALL_THRESHOLD="$2"; shift 2 ;;
        --*)            echo "Unknown option: $1"; exit 1 ;;
        *)              POSITIONAL+=("$1"); shift ;;
    esac
done

SESSION_NAME="${POSITIONAL[0]:-orchestration}"
PANE_COUNT="${POSITIONAL[1]:-2}"
WORK_DIR="${POSITIONAL[2]:-$(pwd)}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK_STATUS="${SCRIPT_DIR}/check-status.sh"

# --- State tracking arrays (bash 3.2+ compatible) ---
# Using eval for dynamic variable names (macOS ships bash 3.2, no declare -A)
for i in $(seq 0 $((PANE_COUNT - 1))); do
    eval "PREV_STATUS_${i}="
    eval "STALL_COUNT_${i}=0"
    eval "NUDGE_SENT_${i}=0"
    eval "AUTO_SELECT_SENT_${i}=0"
done

# --- Helper: extract field from JSON ---
json_field() {
    local field="$1"
    local json="$2"
    echo "$json" | grep -o "\"${field}\":[0-9]*" | head -1 | cut -d: -f2
}

# --- Helper: extract pane status from JSON workers array ---
pane_status() {
    local pane_id="$1"
    local json="$2"
    echo "$json" | grep -o "\"id\":${pane_id}[^}]*" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4
}

echo "[monitor] Session: $SESSION_NAME | Panes: $PANE_COUNT | Dir: $WORK_DIR"
echo "[monitor] Interval: ${INTERVAL}s | Timeout: ${TIMEOUT}s | Stall threshold: $STALL_THRESHOLD"
[[ "$AUTO_SELECT" == true ]] && echo "[monitor] Auto-select: enabled"
echo ""

# --- Initial wait (with countdown) ---
if [[ $INITIAL_WAIT -gt 0 ]]; then
    echo "[monitor] Waiting ${INITIAL_WAIT}s for workers to start..."
    WAIT_ELAPSED=0
    WAIT_INTERVAL=30
    while [[ $WAIT_ELAPSED -lt $INITIAL_WAIT ]]; do
        SLEEP_TIME=$WAIT_INTERVAL
        REMAINING=$((INITIAL_WAIT - WAIT_ELAPSED))
        if [[ $REMAINING -lt $WAIT_INTERVAL ]]; then
            SLEEP_TIME=$REMAINING
        fi
        sleep "$SLEEP_TIME"
        WAIT_ELAPSED=$((WAIT_ELAPSED + SLEEP_TIME))
        if [[ $WAIT_ELAPSED -lt $INITIAL_WAIT ]]; then
            echo "[monitor]   ...${WAIT_ELAPSED}s / ${INITIAL_WAIT}s"
        fi
    done
    echo "[monitor] Initial wait complete. Starting checks."
fi

# --- Main loop ---
ELAPSED=0
CHECK_NUM=0

while [[ $ELAPSED -lt $TIMEOUT ]]; do
    CHECK_NUM=$((CHECK_NUM + 1))

    # Change to work dir for check-status.sh (it reads queue/ relative to cwd)
    # Capture stderr separately for debugging
    CHECK_STDERR=$(mktemp)
    STATUS_JSON=$(cd "$WORK_DIR" && bash "$CHECK_STATUS" "$SESSION_NAME" "$PANE_COUNT" --json 2>"$CHECK_STDERR") || true

    # Debug: show errors if any
    if [[ -s "$CHECK_STDERR" ]]; then
        echo "[monitor] check-status.sh stderr: $(cat "$CHECK_STDERR" | head -c 200)"
    fi
    rm -f "$CHECK_STDERR"

    # Debug: show JSON preview if empty or malformed
    if [[ -z "$STATUS_JSON" ]]; then
        echo "[monitor] WARNING: STATUS_JSON is empty"
    elif ! echo "$STATUS_JSON" | grep -q '"completed"'; then
        echo "[monitor] WARNING: STATUS_JSON malformed: ${STATUS_JSON:0:100}..."
    fi

    COMPLETED=$(json_field "completed" "$STATUS_JSON")
    TOTAL=$(json_field "worker_count" "$STATUS_JSON")
    COMPLETED=${COMPLETED:-0}
    TOTAL=${TOTAL:-$PANE_COUNT}

    echo "[monitor] Check #${CHECK_NUM} | ${COMPLETED}/${TOTAL} complete | Elapsed: ${ELAPSED}s / ${TIMEOUT}s"

    # --- Per-pane analysis ---
    ALL_STALLED=true

    for i in $(seq 0 $((PANE_COUNT - 1))); do
        STATUS=$(pane_status "$i" "$STATUS_JSON")
        STATUS=${STATUS:-Unknown}

        eval "PREV=\${PREV_STATUS_${i}}"
        eval "STALL=\${STALL_COUNT_${i}}"
        eval "NUDGED=\${NUDGE_SENT_${i}}"
        eval "AUTO_SELECTED=\${AUTO_SELECT_SENT_${i}}"

        case "$STATUS" in
            Complete)
                echo "[monitor]   Pane $i: Complete"
                ;;
            WaitingInput)
                echo "[monitor]   Pane $i: WaitingInput (interactive selection UI)"
                if [[ "$AUTO_SELECT" == true && "$AUTO_SELECTED" -eq 0 ]]; then
                    echo "[monitor]   Pane $i: → Sending Enter (auto-select)"
                    tmux send-keys -t "${SESSION_NAME}:0.${i}" C-m 2>/dev/null || true
                    eval "AUTO_SELECT_SENT_${i}=1"
                fi
                ;;
            IdleNoReport)
                echo "[monitor]   Pane $i: IdleNoReport (idle but no report file)"
                if [[ "$NUDGED" -eq 0 ]]; then
                    NUDGE=$(echo "$NUDGE_PROMPT" | sed "s/{N}/$i/g")
                    echo "[monitor]   Pane $i: → Sending nudge prompt"
                    tmux send-keys -t "${SESSION_NAME}:0.${i}" "$NUDGE" 2>/dev/null || true
                    sleep 0.5
                    tmux send-keys -t "${SESSION_NAME}:0.${i}" C-m 2>/dev/null || true
                    sleep 1
                    tmux send-keys -t "${SESSION_NAME}:0.${i}" C-m 2>/dev/null || true
                    eval "NUDGE_SENT_${i}=1"
                fi
                ;;
            Error)
                echo "[monitor]   Pane $i: ERROR detected"
                ;;
            Running)
                echo "[monitor]   Pane $i: Running"
                ;;
            Idle)
                echo "[monitor]   Pane $i: Idle"
                ;;
            *)
                echo "[monitor]   Pane $i: $STATUS"
                ;;
        esac

        # Stall detection (per-pane)
        if [[ "$PREV" == "$STATUS" && "$STATUS" != "Complete" && "$STATUS" != "Running" ]]; then
            STALL=$((STALL + 1))
        else
            STALL=0
        fi
        eval "PREV_STATUS_${i}=$STATUS"
        eval "STALL_COUNT_${i}=$STALL"

        # If any non-complete pane is not stalled, we're not all-stalled
        if [[ "$STATUS" != "Complete" && $STALL -lt $STALL_THRESHOLD ]]; then
            ALL_STALLED=false
        fi
    done

    echo ""

    # --- Completion check ---
    if [[ "$COMPLETED" -eq "$TOTAL" ]]; then
        echo "[monitor] All $TOTAL panes complete."
        exit 0
    fi

    # --- Stall check (only if no panes are running or complete) ---
    REMAINING=$((TOTAL - COMPLETED))
    if [[ $REMAINING -gt 0 && "$ALL_STALLED" == true ]]; then
        echo "[monitor] STALL DETECTED: All remaining panes stalled for $STALL_THRESHOLD consecutive checks."
        echo "[monitor] Stalled panes may need manual intervention."
        exit 2
    fi

    sleep "$INTERVAL"
    ELAPSED=$((ELAPSED + INTERVAL))
done

echo "[monitor] TIMEOUT: ${TIMEOUT}s elapsed. ${COMPLETED:-0}/${TOTAL:-$PANE_COUNT} complete."
exit 1
