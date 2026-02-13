#!/usr/bin/env bash
# capturing-claudecode: Delegates to tmux-orchestrating setup.sh (single-pane mode)
exec bash ~/.claude/skills/tmux-orchestrating/scripts/setup.sh 1 "${1:-claude-capture}" "${2:-$(pwd)}" --single-pane
