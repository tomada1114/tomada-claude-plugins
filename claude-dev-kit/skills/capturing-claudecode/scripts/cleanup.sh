#!/usr/bin/env bash
# capturing-claudecode: Delegates to tmux-orchestrating cleanup.sh
exec bash ~/.claude/skills/tmux-orchestrating/scripts/cleanup.sh "${1:-claude-capture}"
