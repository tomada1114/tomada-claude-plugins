#!/usr/bin/env bash
set -euo pipefail

# tmux-orchestrating: Queue directory initialization
# Creates queue/tasks/ and queue/reports/ structure
#
# Usage: bash init-queue.sh [PANE_COUNT] [WORK_DIR] [--orchestrated]
#   PANE_COUNT:     number of workers (default: 2)
#   WORK_DIR:       directory to create queue/ in (default: current dir)
#   --orchestrated: use worker{N} naming and create plan.md

PANE_COUNT="${1:-2}"
WORK_DIR="${2:-$(pwd)}"

# Parse --orchestrated flag
ORCHESTRATED=false
for arg in "$@"; do
    if [[ "$arg" == "--orchestrated" ]]; then
        ORCHESTRATED=true
    fi
done

QUEUE_DIR="${WORK_DIR}/queue"

# Create directory structure
mkdir -p "${QUEUE_DIR}/tasks" "${QUEUE_DIR}/reports"

# Clear task and report files (per-run ephemeral files)
rm -f "${QUEUE_DIR}/tasks/"*.md "${QUEUE_DIR}/reports/"*.md

# Preserve plan.md if it already has content (callers may pre-write it)
if [[ ! -f "${QUEUE_DIR}/plan.md" ]] || [[ ! -s "${QUEUE_DIR}/plan.md" ]]; then
    rm -f "${QUEUE_DIR}/plan.md"
fi

# Add .gitignore if not present
if [[ ! -f "${QUEUE_DIR}/.gitignore" ]]; then
    echo "*" > "${QUEUE_DIR}/.gitignore"
fi

if [[ "$ORCHESTRATED" == true ]]; then
    # Create plan.md placeholder only if not already present
    if [[ ! -f "${QUEUE_DIR}/plan.md" ]]; then
        touch "${QUEUE_DIR}/plan.md"
    fi
    echo "Queue initialized: ${QUEUE_DIR}/ (orchestrated, ${PANE_COUNT} workers)"
    echo "  plan.md  - master plan (write goal here)"
    echo "  tasks/   - worker task files (worker{N}.md)"
    echo "  reports/ - completion reports (worker{N}_report.md + orchestrator_report.md)"
else
    echo "Queue initialized: ${QUEUE_DIR}/ (quick, ${PANE_COUNT} panes)"
    echo "  tasks/   - task files per pane (pane{N}.md)"
    echo "  reports/ - completion reports (pane{N}_report.md)"
fi
