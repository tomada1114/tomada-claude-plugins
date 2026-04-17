#!/usr/bin/env bash
set -euo pipefail

# tmux-orchestrating: Status check script
# Checks all panes for Busy/Idle/Complete/WaitingInput/IdleNoReport/Error status
# using capture-pane + report files
# Auto-detects mode (quick vs orchestrated) via queue/plan.md existence
#
# Usage: bash check-status.sh [SESSION_NAME] [PANE_COUNT] [--json]
#   SESSION_NAME: tmux session name (default: orchestration)
#   PANE_COUNT:   number of workers (default: 2)
#   --json:       output machine-readable JSON (for monitor.py/monitor.sh)

SESSION_NAME="${1:-orchestration}"
PANE_COUNT="${2:-2}"

# Parse --json flag
JSON_OUTPUT=false
for arg in "$@"; do
    if [[ "$arg" == "--json" ]]; then
        JSON_OUTPUT=true
    fi
done

# Busy/Idle indicators
# Claude Code activity indicators include Unicode spinners (✽ ✶ ✢ ✳ ✻ ·) and
# various status verbs. "Esc to interrupt" also indicates active processing.
# Also matches the timer pattern "(Ns ·" or "(Nm Ns ·" unique to Claude's thinking mode.
BUSY_PATTERNS="Thinking|Esc to interrupt|Boogieing|Mulling|Churning|Implementing|Effecting|Boondoggling|Puzzling|Calculating|Fermenting|Crunching|Writing|Reading|Searching|Running|Cogitating|Pontificating|Gusting|Perambulating|Noodling|Pondering|Ruminating|Introspecting|Deliberating|Reticulating|✽|✶|✢|✳|✻|\([0-9]+s ·|\([0-9]+m [0-9]+s"
IDLE_PATTERNS="❯ |to cycle\)|bypass permissions on"

# Interactive selection UI (AskUserQuestion prompts)
WAITING_INPUT_PATTERNS="Enter to select"

# Error patterns (only meaningful when pane is also idle)
ERROR_PATTERNS="Error:|APIError|Permission denied|EACCES|panic:|Traceback|FATAL"

COMPLETED=0
RUNNING=0
IDLE=0
WAITING_INPUT=0
IDLE_NO_REPORT=0
ERROR_COUNT=0

# Auto-detect mode
if [[ -f "queue/plan.md" ]]; then
    MODE="orchestrated"
else
    MODE="quick"
fi

# Load handson mapping if exists (for cc-book-handson-orchestrate)
# Format: {"pane0":["3.3","3.4"],"pane1":["3.5"]}
HANDSON_MAPPING=""
HANDSON_REPORTS_DIR=""
if [[ -f "queue/mapping.json" ]]; then
    HANDSON_MAPPING=$(cat "queue/mapping.json")
    # Auto-detect reviews location (iObsidian project structure)
    if [[ -d "Content/Books/ClaudeCodeAppImpl/Planning/reviews" ]]; then
        HANDSON_REPORTS_DIR="Content/Books/ClaudeCodeAppImpl/Planning/reviews"
    fi
fi

# Helper: check if handson report exists for a pane (via mapping.json)
# Returns 0 (true) if any mapped section has a handson report
check_handson_report() {
    local pane_id="$1"
    if [[ -z "$HANDSON_MAPPING" || -z "$HANDSON_REPORTS_DIR" ]]; then
        return 1
    fi
    # Extract sections for this pane using grep/sed (bash 3.2 compatible)
    local sections
    sections=$(echo "$HANDSON_MAPPING" | grep -o "\"pane${pane_id}\":\[[^]]*\]" | sed 's/.*\[\([^]]*\)\].*/\1/' | tr -d '"' | tr ',' ' ')
    for section in $sections; do
        local x y
        x=$(echo "$section" | cut -d. -f1)
        y=$(echo "$section" | cut -d. -f2)
        if [[ -f "${HANDSON_REPORTS_DIR}/handson-${x}-${y}.md" ]]; then
            return 0
        fi
    done
    return 1
}

# Check if session exists
SESSION_EXISTS=true
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    SESSION_EXISTS=false
fi

# Helper: detect pane status from capture-pane output
# Priority: WaitingInput > Error(+Idle) > Busy > Idle/IdleNoReport > Unknown
# Optional args: task_file, report_file (for IdleNoReport detection)
detect_status() {
    local pane_target="$1"
    local task_file="${2:-}"
    local report_file="${3:-}"
    if [[ "$SESSION_EXISTS" == false ]]; then
        echo "NoSession"
        return
    fi
    local output
    # Use -S -50 to include scrollback buffer: Claude Code's activity (spinner/verb)
    # often scrolls above the visible pane area due to separator lines and blank space.
    # Without scrollback, all panes appear "Unknown" even when actively processing.
    output=$(tmux capture-pane -t "$pane_target" -p -S -50 2>/dev/null | grep -v "^[─═━┄┈ ]*$" | tail -30) || true

    # 1. Check WaitingInput first (interactive selection UI)
    if echo "$output" | grep -qE "$WAITING_INPUT_PATTERNS"; then
        echo "WaitingInput"
        return
    fi

    # 2. Check busy: Claude shows spinner/verb even when prompt char is visible
    if echo "$output" | grep -qE "$BUSY_PATTERNS"; then
        echo "Running"
        return
    fi

    # 3. Check idle (then refine to IdleNoReport or Error)
    if echo "$output" | grep -qE "$IDLE_PATTERNS"; then
        # 3a. Error: idle + error patterns in output
        if echo "$output" | grep -qE "$ERROR_PATTERNS"; then
            echo "Error"
            return
        fi
        # 3b. IdleNoReport: idle + task exists + no report
        if [[ -n "$task_file" && -f "$task_file" && -n "$report_file" && ! -f "$report_file" ]]; then
            echo "IdleNoReport"
            return
        fi
        echo "Idle"
        return
    fi

    echo "Unknown"
}

# Helper: get last N lines from capture-pane (for preview)
# Uses scrollback (-S -30) so activity above visible area is included.
capture_preview() {
    local pane_target="$1"
    local lines="${2:-5}"
    if [[ "$SESSION_EXISTS" == false ]]; then
        echo ""
        return
    fi
    tmux capture-pane -t "$pane_target" -p -S -30 2>/dev/null | grep -v "^[─═━┄┈ ]*$" | tail -"$lines" | sed 's/"/\\"/g' || echo ""
}

if [[ "$JSON_OUTPUT" == true ]]; then
    # === JSON output mode ===
    ORCH_STATUS=""
    ORCH_PREVIEW=""
    ORCH_COMPLETE=false

    if [[ "$MODE" == "orchestrated" ]]; then
        ORCH_STATUS=$(detect_status "${SESSION_NAME}:0.0")
        ORCH_PREVIEW=$(capture_preview "${SESSION_NAME}:0.0" 3)
        [[ -f "queue/reports/orchestrator_report.md" ]] && ORCH_COMPLETE=true
    fi

    # Build workers JSON array
    WORKERS_JSON="["
    FIRST=true

    if [[ "$MODE" == "orchestrated" ]]; then
        for i in $(seq 1 "$PANE_COUNT"); do
            TASK=""
            TASK_FILE="queue/tasks/worker${i}.md"
            REPORT_FILE="queue/reports/worker${i}_report.md"
            [[ -f "$TASK_FILE" ]] && TASK=$(head -1 "$TASK_FILE" 2>/dev/null | sed 's/^# Task: //' | sed 's/"/\\"/g' || echo "")

            if [[ -f "$REPORT_FILE" ]]; then
                STATUS="Complete"
                SUMMARY=$(head -1 "$REPORT_FILE" 2>/dev/null | sed 's/"/\\"/g' || echo "")
                COMPLETED=$((COMPLETED + 1))
            else
                STATUS=$(detect_status "${SESSION_NAME}:0.${i}" "$TASK_FILE" "$REPORT_FILE")
                SUMMARY=""
                case "$STATUS" in
                    Running)       RUNNING=$((RUNNING + 1)) ;;
                    Idle)          IDLE=$((IDLE + 1)) ;;
                    WaitingInput)  WAITING_INPUT=$((WAITING_INPUT + 1)) ;;
                    IdleNoReport)  IDLE_NO_REPORT=$((IDLE_NO_REPORT + 1)) ;;
                    Error)         ERROR_COUNT=$((ERROR_COUNT + 1)) ;;
                esac
            fi

            PREVIEW=$(capture_preview "${SESSION_NAME}:0.${i}" 3)

            [[ "$FIRST" == true ]] && FIRST=false || WORKERS_JSON+=","
            WORKERS_JSON+="{\"id\":$i,\"pane\":$i,\"name\":\"Worker $i\",\"status\":\"$STATUS\",\"task\":\"$TASK\",\"summary\":\"$SUMMARY\",\"preview\":\"$PREVIEW\"}"
        done
    else
        for i in $(seq 0 $((PANE_COUNT - 1))); do
            TASK=""
            TASK_FILE="queue/tasks/pane${i}.md"
            REPORT_FILE="queue/reports/pane${i}_report.md"
            [[ -f "$TASK_FILE" ]] && TASK=$(head -1 "$TASK_FILE" 2>/dev/null | sed 's/^# Task: //' | sed 's/"/\\"/g' || echo "")

            # Check completion: queue report OR handson report (via mapping.json)
            if [[ -f "$REPORT_FILE" ]] || check_handson_report "$i"; then
                STATUS="Complete"
                SUMMARY=$(head -1 "$REPORT_FILE" 2>/dev/null | sed 's/"/\\"/g' || echo "")
                COMPLETED=$((COMPLETED + 1))
            else
                STATUS=$(detect_status "${SESSION_NAME}:0.${i}" "$TASK_FILE" "$REPORT_FILE")
                SUMMARY=""
                case "$STATUS" in
                    Running)       RUNNING=$((RUNNING + 1)) ;;
                    Idle)          IDLE=$((IDLE + 1)) ;;
                    WaitingInput)  WAITING_INPUT=$((WAITING_INPUT + 1)) ;;
                    IdleNoReport)  IDLE_NO_REPORT=$((IDLE_NO_REPORT + 1)) ;;
                    Error)         ERROR_COUNT=$((ERROR_COUNT + 1)) ;;
                esac
            fi

            PREVIEW=$(capture_preview "${SESSION_NAME}:0.${i}" 3)

            [[ "$FIRST" == true ]] && FIRST=false || WORKERS_JSON+=","
            WORKERS_JSON+="{\"id\":$i,\"pane\":$i,\"name\":\"Pane $i\",\"status\":\"$STATUS\",\"task\":\"$TASK\",\"summary\":\"$SUMMARY\",\"preview\":\"$PREVIEW\"}"
        done
    fi

    WORKERS_JSON+="]"

    # Read plan goal if exists
    GOAL=""
    if [[ -f "queue/plan.md" ]]; then
        GOAL=$(grep -A1 "^## Goal" queue/plan.md 2>/dev/null | tail -1 | sed 's/"/\\"/g' || echo "")
    fi

    # Output JSON
    cat <<ENDJSON
{"mode":"$MODE","session":"$SESSION_NAME","session_exists":$SESSION_EXISTS,"worker_count":$PANE_COUNT,"completed":$COMPLETED,"running":$RUNNING,"idle":$IDLE,"waiting_input":$WAITING_INPUT,"idle_no_report":$IDLE_NO_REPORT,"error":$ERROR_COUNT,"orchestrator_status":"$ORCH_STATUS","orchestrator_complete":$ORCH_COMPLETE,"goal":"$GOAL","workers":$WORKERS_JSON}
ENDJSON
    exit 0
fi

# === Human-readable output mode (unchanged) ===

echo "=== Orchestration Status ==="
echo "Session: $SESSION_NAME | Workers: $PANE_COUNT | Mode: $MODE"
echo ""

if [[ "$MODE" == "orchestrated" ]]; then
    ORCH_STATUS=$(detect_status "${SESSION_NAME}:0.0")
    printf "  Orchestrator (Pane 0): %s\n" "$ORCH_STATUS"
    echo ""

    for i in $(seq 1 "$PANE_COUNT"); do
        TASK_FILE="queue/tasks/worker${i}.md"
        REPORT_FILE="queue/reports/worker${i}_report.md"
        if [[ -f "$REPORT_FILE" ]]; then
            STATUS="Complete"
            DETAIL=$(head -1 "$REPORT_FILE" 2>/dev/null || echo "")
            COMPLETED=$((COMPLETED + 1))
        else
            STATUS=$(detect_status "${SESSION_NAME}:0.${i}" "$TASK_FILE" "$REPORT_FILE")
            DETAIL=""
            case "$STATUS" in
                Running)       RUNNING=$((RUNNING + 1)) ;;
                Idle)          IDLE=$((IDLE + 1)) ;;
                WaitingInput)  WAITING_INPUT=$((WAITING_INPUT + 1)) ;;
                IdleNoReport)  IDLE_NO_REPORT=$((IDLE_NO_REPORT + 1)) ;;
                Error)         ERROR_COUNT=$((ERROR_COUNT + 1)) ;;
            esac
        fi

        TASK=""
        if [[ -f "$TASK_FILE" ]]; then
            TASK=$(head -1 "$TASK_FILE" 2>/dev/null | sed 's/^# Task: //' || echo "")
        fi

        printf "  Worker %d (Pane %d): %-14s" "$i" "$i" "$STATUS"
        [[ -n "$TASK" ]] && printf " | Task: %s" "$TASK"
        [[ -n "$DETAIL" ]] && printf " | %s" "$DETAIL"
        echo ""
    done

    echo ""
    printf "Workers: %d/%d complete | %d running | %d idle" "$COMPLETED" "$PANE_COUNT" "$RUNNING" "$IDLE"
    [[ $WAITING_INPUT -gt 0 ]] && printf " | %d waiting" "$WAITING_INPUT"
    [[ $IDLE_NO_REPORT -gt 0 ]] && printf " | %d idle(no report)" "$IDLE_NO_REPORT"
    [[ $ERROR_COUNT -gt 0 ]] && printf " | %d error" "$ERROR_COUNT"
    echo ""

    if [[ -f "queue/reports/orchestrator_report.md" ]]; then
        echo ""
        echo "=== ORCHESTRATION COMPLETE ==="
        echo "Final report: queue/reports/orchestrator_report.md"
    fi

    [[ -f "queue/reports/orchestrator_report.md" ]] && exit 0 || exit 1

else
    for i in $(seq 0 $((PANE_COUNT - 1))); do
        TASK_FILE="queue/tasks/pane${i}.md"
        REPORT_FILE="queue/reports/pane${i}_report.md"
        # Check completion: queue report OR handson report (via mapping.json)
        if [[ -f "$REPORT_FILE" ]] || check_handson_report "$i"; then
            STATUS="Complete"
            DETAIL=$(head -1 "$REPORT_FILE" 2>/dev/null || echo "")
            COMPLETED=$((COMPLETED + 1))
        else
            STATUS=$(detect_status "${SESSION_NAME}:0.${i}" "$TASK_FILE" "$REPORT_FILE")
            DETAIL=""
            case "$STATUS" in
                Running)       RUNNING=$((RUNNING + 1)) ;;
                Idle)          IDLE=$((IDLE + 1)) ;;
                WaitingInput)  WAITING_INPUT=$((WAITING_INPUT + 1)) ;;
                IdleNoReport)  IDLE_NO_REPORT=$((IDLE_NO_REPORT + 1)) ;;
                Error)         ERROR_COUNT=$((ERROR_COUNT + 1)) ;;
            esac
        fi

        TASK=""
        if [[ -f "$TASK_FILE" ]]; then
            TASK=$(head -1 "$TASK_FILE" 2>/dev/null | sed 's/^# Task: //' || echo "")
        fi

        printf "  Pane %d: %-14s" "$i" "$STATUS"
        [[ -n "$TASK" ]] && printf " | Task: %s" "$TASK"
        [[ -n "$DETAIL" ]] && printf " | %s" "$DETAIL"
        echo ""
    done

    echo ""
    printf "Progress: %d/%d complete | %d running | %d idle" "$COMPLETED" "$PANE_COUNT" "$RUNNING" "$IDLE"
    [[ $WAITING_INPUT -gt 0 ]] && printf " | %d waiting" "$WAITING_INPUT"
    [[ $IDLE_NO_REPORT -gt 0 ]] && printf " | %d idle(no report)" "$IDLE_NO_REPORT"
    [[ $ERROR_COUNT -gt 0 ]] && printf " | %d error" "$ERROR_COUNT"
    echo ""

    [[ $COMPLETED -eq $PANE_COUNT ]] && exit 0 || exit 1
fi
