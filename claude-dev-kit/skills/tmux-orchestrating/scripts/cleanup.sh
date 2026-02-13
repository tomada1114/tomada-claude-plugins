#!/usr/bin/env bash
set -euo pipefail

# tmux-orchestrating: Cleanup script
# Exits Claude in all panes, kills session, optionally removes queue
#
# Usage: bash cleanup.sh [SESSION_NAME] [--keep-queue]
#   SESSION_NAME: tmux session name (default: orchestration)
#   --keep-queue: keep queue/ directory for debugging

SESSION_NAME="${1:-orchestration}"
KEEP_QUEUE=false

for arg in "$@"; do
    if [[ "$arg" == "--keep-queue" ]]; then
        KEEP_QUEUE=true
    fi
done

echo "=== tmux-orchestrating cleanup ==="

# Detect mode
if [[ -f "queue/plan.md" ]]; then
    echo "Mode: Orchestrated"
else
    echo "Mode: Quick"
fi

# Check if session exists
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Session '$SESSION_NAME' does not exist. Nothing to clean."
    exit 0
fi

# Step 1: Exit Claude in all panes (2-call protocol)
PANE_COUNT=$(tmux list-panes -t "$SESSION_NAME" | wc -l | tr -d ' ')
echo "[1/3] Exiting Claude in $PANE_COUNT panes..."

for i in $(seq 0 $((PANE_COUNT - 1))); do
    tmux send-keys -t "${SESSION_NAME}:0.${i}" "/exit"
    tmux send-keys -t "${SESSION_NAME}:0.${i}" C-m
done

sleep 2

# Step 2: Kill session
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
echo "[2/3] Session '$SESSION_NAME' killed"

# Step 3: Clean queue directory
if [[ "$KEEP_QUEUE" == true ]]; then
    echo "[3/3] Queue directory preserved (--keep-queue)"
else
    rm -rf queue/
    echo "[3/3] Queue directory removed"
fi

echo "=== Cleanup complete ==="
