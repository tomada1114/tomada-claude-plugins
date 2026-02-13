#!/usr/bin/env bash
set -euo pipefail

# tmux-orchestrating: Session setup script
# Creates tmux session, splits panes, launches Claude Code, waits for idle
#
# Usage: bash setup.sh [PANE_COUNT] [SESSION_NAME] [WORK_DIR] [--orchestrated] [--single-pane]
#   PANE_COUNT:     1-4 workers (default: 2)
#   SESSION_NAME:   tmux session name (default: orchestration)
#   WORK_DIR:       working directory for all panes (default: current dir)
#   --orchestrated: enable orchestrator mode (Pane 0 = orchestrator, Pane 1+ = workers)
#   --single-pane:  single pane mode (no queue init, for capture/factcheck use)

PANE_COUNT="${1:-2}"
SESSION_NAME="${2:-orchestration}"
WORK_DIR="${3:-$(pwd)}"

# Parse flags
ORCHESTRATED=false
SINGLE_PANE=false
for arg in "$@"; do
    case "$arg" in
        --orchestrated) ORCHESTRATED=true ;;
        --single-pane)  SINGLE_PANE=true ;;
    esac
done

# Validate mutually exclusive flags
if [[ "$ORCHESTRATED" == true && "$SINGLE_PANE" == true ]]; then
    echo "Error: --orchestrated and --single-pane are mutually exclusive"
    exit 1
fi

# Override pane count for single-pane mode
if [[ "$SINGLE_PANE" == true ]]; then
    PANE_COUNT=1
fi

# Calculate total panes
if [[ "$ORCHESTRATED" == true ]]; then
    TOTAL_PANES=$((PANE_COUNT + 1))  # +1 for orchestrator
else
    TOTAL_PANES=$PANE_COUNT
fi

# Validation
if [[ "$PANE_COUNT" -lt 1 || "$PANE_COUNT" -gt 4 ]]; then
    echo "Error: PANE_COUNT must be 1-4 (got: $PANE_COUNT)"
    exit 1
fi

if [[ "$TOTAL_PANES" -gt 5 ]]; then
    echo "Error: Max 5 total panes (1 orchestrator + 4 workers). Got: $TOTAL_PANES"
    exit 1
fi

if ! command -v tmux &>/dev/null; then
    echo "Error: tmux is not installed"
    exit 1
fi

if ! command -v claude &>/dev/null; then
    echo "Error: claude is not installed"
    exit 1
fi

if [[ "$SINGLE_PANE" == true ]]; then
    echo "=== tmux-orchestrating setup (Single Pane Mode) ==="
    echo "Session: $SESSION_NAME | Dir: $WORK_DIR"
elif [[ "$ORCHESTRATED" == true ]]; then
    echo "=== tmux-orchestrating setup (Orchestrated Mode) ==="
    echo "Orchestrator: Pane 0 | Workers: Pane 1-${PANE_COUNT} | Session: $SESSION_NAME | Dir: $WORK_DIR"
else
    echo "=== tmux-orchestrating setup (Quick Mode) ==="
    echo "Panes: $PANE_COUNT | Session: $SESSION_NAME | Dir: $WORK_DIR"
fi

# Step 1: Kill existing session (clean start)
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
echo "[1/4] Cleaned existing session"

# Step 2: Create session and split panes
tmux new-session -d -s "$SESSION_NAME" -c "$WORK_DIR"

case "$TOTAL_PANES" in
    1)
        # Single pane: no split needed (session already has one pane)
        ;;
    2)
        tmux split-window -h -t "$SESSION_NAME" -c "$WORK_DIR"
        ;;
    3)
        tmux split-window -h -t "${SESSION_NAME}:0.0" -c "$WORK_DIR"
        tmux split-window -v -t "${SESSION_NAME}:0.1" -c "$WORK_DIR"
        ;;
    4)
        tmux split-window -h -t "${SESSION_NAME}:0" -c "$WORK_DIR"
        tmux split-window -v -t "${SESSION_NAME}:0.0" -c "$WORK_DIR"
        tmux split-window -v -t "${SESSION_NAME}:0.2" -c "$WORK_DIR"
        tmux select-layout -t "$SESSION_NAME" tiled
        ;;
    5)
        tmux split-window -h -t "${SESSION_NAME}:0" -c "$WORK_DIR"
        tmux split-window -v -t "${SESSION_NAME}:0.0" -c "$WORK_DIR"
        tmux split-window -v -t "${SESSION_NAME}:0.2" -c "$WORK_DIR"
        tmux split-window -v -t "${SESSION_NAME}:0.3" -c "$WORK_DIR"
        tmux select-layout -t "$SESSION_NAME" tiled
        ;;
esac

# Set pane titles for identification
if [[ "$ORCHESTRATED" == true ]]; then
    tmux select-pane -t "${SESSION_NAME}:0.0" -T "orchestrator"
    for i in $(seq 1 "$PANE_COUNT"); do
        tmux select-pane -t "${SESSION_NAME}:0.${i}" -T "worker${i}"
    done
else
    for i in $(seq 0 $((TOTAL_PANES - 1))); do
        tmux select-pane -t "${SESSION_NAME}:0.${i}" -T "pane${i}"
    done
fi

echo "[2/4] Created $TOTAL_PANES panes"

# Step 3: Initialize queue directory (skip for single-pane mode)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$SINGLE_PANE" == true ]]; then
    echo "[3/4] Skipped queue init (single-pane mode)"
elif [[ -f "${SCRIPT_DIR}/init-queue.sh" ]]; then
    if [[ "$ORCHESTRATED" == true ]]; then
        bash "${SCRIPT_DIR}/init-queue.sh" "$PANE_COUNT" "$WORK_DIR" --orchestrated
    else
        bash "${SCRIPT_DIR}/init-queue.sh" "$PANE_COUNT" "$WORK_DIR"
    fi
    echo "[3/4] Initialized queue directory"
fi

# Step 4: Launch Claude Code in all panes and wait for idle
for i in $(seq 0 $((TOTAL_PANES - 1))); do
    tmux send-keys -t "${SESSION_NAME}:0.${i}" "claude --dangerously-skip-permissions" C-m
done

echo "[4/4] Launching Claude Code in $TOTAL_PANES panes..."

# Idle wait loop (indicator-based, not fixed sleep)
IDLE_PATTERNS="bypass permissions on"
MAX_WAIT=30
INTERVAL=3
ELAPSED=0
READY_COUNT=0

while [[ $ELAPSED -lt $MAX_WAIT && $READY_COUNT -lt $TOTAL_PANES ]]; do
    sleep "$INTERVAL"
    ELAPSED=$((ELAPSED + INTERVAL))
    READY_COUNT=0

    for i in $(seq 0 $((TOTAL_PANES - 1))); do
        OUTPUT=$(tmux capture-pane -t "${SESSION_NAME}:0.${i}" -p 2>/dev/null | tail -10)
        if echo "$OUTPUT" | grep -q "$IDLE_PATTERNS"; then
            READY_COUNT=$((READY_COUNT + 1))
        fi
    done

    echo "  Waiting... ${ELAPSED}s (${READY_COUNT}/${TOTAL_PANES} ready)"
done

if [[ $READY_COUNT -eq $TOTAL_PANES ]]; then
    echo "=== All $TOTAL_PANES panes ready ==="
else
    echo "=== Warning: ${READY_COUNT}/${TOTAL_PANES} panes ready (timeout ${MAX_WAIT}s) ==="
    echo "Some panes may still be starting. Check with: tmux capture-pane -t ${SESSION_NAME}:0.N -p | tail -5"
fi

# Output session info
echo ""
echo "Session: $SESSION_NAME"
if [[ "$ORCHESTRATED" == true ]]; then
    echo "Mode: Orchestrated (Pane 0 = orchestrator, Panes 1-${PANE_COUNT} = workers)"
else
    echo "Mode: Quick (all panes are workers)"
fi
echo "Panes: $(tmux list-panes -t "$SESSION_NAME" -F '#{pane_index}' | tr '\n' ' ')"
echo "Attach: tmux attach -t $SESSION_NAME"
echo "Queue:  $WORK_DIR/queue/"
