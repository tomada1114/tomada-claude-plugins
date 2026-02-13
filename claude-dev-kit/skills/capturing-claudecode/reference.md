# capturing-claudecode Reference

Detailed technical reference for the capturing-claudecode skill.
For the main workflow, see [SKILL.md](SKILL.md).

## send-keys 2-Call Protocol

`tmux send-keys` for text input must be split into 2 separate bash calls.

### Why

When text and `Enter`/`C-m` are combined in a single call, Enter can be misinterpreted
by tmux, especially with multi-line text or special characters.

### Correct Pattern

```bash
# Call 1: Send text
tmux send-keys -t claude-capture:0.0 'Hello'
# Call 2: Press Enter (separate bash call)
tmux send-keys -t claude-capture:0.0 C-m
```

### Wrong Patterns

```bash
# NG: Combined in one call
tmux send-keys -t claude-capture:0.0 'Hello' Enter

# NG: Chained with &&
tmux send-keys -t claude-capture:0.0 'Hello' && tmux send-keys -t claude-capture:0.0 Enter
```

## Special Key Reference

Keys for navigating interactive UI elements. These are single send-keys calls (no C-m needed).

| Key | tmux send-keys | Use Case |
|-----|---------------|----------|
| Right arrow | `Right` | Navigate menu right |
| Left arrow | `Left` | Navigate menu left |
| Up arrow | `Up` | Navigate menu up |
| Down arrow | `Down` | Navigate menu down |
| Tab | `Tab` | Cycle forward through options |
| Shift-Tab | `BTab` | Cycle backward through options |
| Enter | `C-m` | Confirm selection |
| Escape | `Escape` | Cancel / go back |
| Ctrl-C | `C-c` | Interrupt |
| Space | `Space` | Toggle checkbox / select |
| Page Up | `PageUp` | Scroll up in scrollable area |
| Page Down | `PageDown` | Scroll down in scrollable area |

### Multi-key Navigation Example

Navigating Claude's `/permissions` menu:

```bash
# Open permissions menu
tmux send-keys -t claude-capture:0.0 '/permissions'
tmux send-keys -t claude-capture:0.0 C-m
sleep 2
tmux capture-pane -t claude-capture:0.0 -p  # Capture Allow tab

tmux send-keys -t claude-capture:0.0 Right   # Move to Ask tab
sleep 1
tmux capture-pane -t claude-capture:0.0 -p  # Capture Ask tab

tmux send-keys -t claude-capture:0.0 Right   # Move to Deny tab
sleep 1
tmux capture-pane -t claude-capture:0.0 -p  # Capture Deny tab

tmux send-keys -t claude-capture:0.0 Escape  # Close menu
```

## Busy/Idle Detection

Before sending commands or capturing output, verify the pane state.

### Indicators

| Type | Patterns | Meaning |
|------|----------|---------|
| **Busy (verbs)** | `Thinking`, `Effecting`, `Boondoggling`, `Puzzling`, `Calculating`, `Fermenting`, `Crunching`, `Boogieing`, `Mulling`, `Churning`, `Implementing`, `Writing`, `Reading`, `Searching`, `Running` | Claude is processing. Do NOT send or capture. |
| **Busy (UI)** | `Esc to interrupt`, `✽`, `✶`, `✢`, `✳`, `✻` | Unicode spinners visible. |
| **Busy (status)** | `Worked for`, `Cooked for`, `Churned for` | Completion message (prompt may appear shortly). |
| **Idle** | `❯ ` (prompt + space), `bypass permissions on`, `to cycle)` | Claude is waiting for input. Safe to send/capture. |

**Important**: Always check Busy patterns BEFORE Idle patterns. A pane can display both
a prompt and a spinner simultaneously. Busy takes priority.

### Idle Wait with Retry

```bash
BUSY_RE="Thinking|Esc to interrupt|Boogieing|Mulling|Churning|Implementing|Writing|Reading|Searching|Running|✽|✶|✢|✳|✻"
IDLE_RE="❯ |bypass permissions on|to cycle\)"

MAX_RETRIES=12
for attempt in $(seq 1 $MAX_RETRIES); do
    OUTPUT=$(tmux capture-pane -t claude-capture:0.0 -p | tail -15)
    if echo "$OUTPUT" | grep -qE "$IDLE_RE" && ! echo "$OUTPUT" | grep -qE "$BUSY_RE"; then
        break
    fi
    sleep 10
done
```

## capture-pane Options

| Flag | Meaning | When to Use |
|------|---------|-------------|
| `-p` | Print to stdout (required) | Always |
| `-S -` | Start from beginning of scrollback | Full capture |
| `-S -50` | Start from 50 lines before current | Recent output |
| `\| tail -N` | Last N lines of visible output | Quick peek |
| `-e` | Include escape sequences (colors) | When formatting matters |

### Examples

```bash
# Full scrollback
tmux capture-pane -t claude-capture:0.0 -p -S -

# Last 30 lines
tmux capture-pane -t claude-capture:0.0 -p | tail -30

# Specific range (lines 0-100)
tmux capture-pane -t claude-capture:0.0 -p -S 0 -E 100
```

For markdown output, default (no `-e`) is preferred for clean text.

## Output Markdown Formats

### Simple Capture

```markdown
# Claude Code Capture: [Description]

Captured: [timestamp]

## Command Sent

`[command text]`

## Output

\```
[captured terminal output]
\```
```

### Interactive UI Capture (Multi-Step)

```markdown
# Claude Code Capture: [Description]

Captured: [timestamp]

## Step 1: [Action]

### Command/Key
`[command or key name]`

### Screen
\```
[captured screen]
\```

## Step 2: [Action]
...
```

## Troubleshooting

### Session Already Exists

`setup.sh` handles this automatically by killing existing sessions first.
Manual fix: `tmux kill-session -t claude-capture`

### Claude Not Starting

Ensure Claude CLI is installed and in PATH. `setup.sh` validates this at startup.

### Capture Returns Empty

The pane may not have rendered yet.
**Fix:** Add `sleep 1-2` after idle detection before capturing.

### Interactive UI Not Rendering

Some UI elements need extra time after key press.
**Fix:** Increase sleep between key send and capture (`sleep 2`).

### Multi-line Input Not Confirming

Claude Code may be waiting for confirmation.
**Fix:** Send extra `C-m` after a brief sleep.

```bash
tmux send-keys -t claude-capture:0.0 'multi-line text'
tmux send-keys -t claude-capture:0.0 C-m
sleep 1
tmux send-keys -t claude-capture:0.0 C-m
```

### Pane Unresponsive

```bash
tmux send-keys -t claude-capture:0.0 C-c
sleep 2
tmux capture-pane -t claude-capture:0.0 -p | tail -10
```

### Claude Code Operations Behave Unexpectedly

If a slash command, menu, or UI interaction does not work as expected
(unknown command, changed menu structure, unexpected behavior):

Use the `claude-code-guide` sub-agent to look up official documentation:

```
Task tool → subagent_type: claude-code-guide
Prompt: "How does /permissions work in Claude Code?" (example)
```

Official docs may not cover every edge case, but often clarify correct
command syntax, available options, and current UI behavior.
