---
name: capturing-claudecode
description: Capture Claude Code terminal output and interactive UI screens via tmux. Launch a single Claude Code pane, send commands or keystrokes, capture screen output, and save to markdown files. Use PROACTIVELY when capturing Claude Code output, recording terminal sessions, screen capture, UI navigation capture, tmux capture, recording Claude responses, キャプチャ, 画面記録, 出力記録. Examples: <example>Context: User wants to capture Claude output user: 'Helloの出力を記録して' assistant: 'I will use capturing-claudecode skill' <commentary>Triggered by capture request</commentary></example>
argument-hint: [capture task description]
---

# Capturing Claude Code

Capture Claude Code terminal output and interactive UI screens via tmux.
Launches a single Claude Code pane, sends commands/keystrokes, captures screen output,
and saves results to markdown files.

## Goal

$ARGUMENTS

## Skill Structure

```
capturing-claudecode/
├── SKILL.md          # This file (workflow)
├── reference.md      # Troubleshooting, special keys, idle detection
└── scripts/
    ├── setup.sh      # Session + pane + Claude launch + idle wait
    └── cleanup.sh    # Exit Claude + kill session
```

## Capture Types

| Type | Description | Example |
|------|-------------|---------|
| **Simple output** | Send text command, wait, capture | "Hello" -> capture greeting |
| **Interactive UI** | Navigate menus with arrow/Tab keys | /permissions menu tabs |
| **Multi-step** | Sequential send-capture cycles | Record a conversation flow |

## Execution Workflow

### Step 1: Setup

```bash
bash ~/.claude/skills/capturing-claudecode/scripts/setup.sh
```

Creates tmux session `claude-capture`, launches Claude Code, waits for idle.

### Step 2: Send Command (2-call protocol)

```bash
# Call 1: Send text
tmux send-keys -t claude-capture:0.0 'Hello'
```

```bash
# Call 2: Press Enter (SEPARATE bash call)
tmux send-keys -t claude-capture:0.0 C-m
```

### Step 3: Wait for Idle

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

### Step 4: Capture Output

```bash
tmux capture-pane -t claude-capture:0.0 -p
```

### Step 5: Save to Markdown

Default save location: `~/Desktop/` with descriptive filename.
If a path is specified in the task arguments, use that instead.

### Step 6: (Optional) Repeat Steps 2-5

For multi-step captures, repeat the send/wait/capture cycle.

### Step 7: Cleanup

```bash
bash ~/.claude/skills/capturing-claudecode/scripts/cleanup.sh
```

## Sending Special Keys (Interactive UI)

Special keys are single send-keys calls. No C-m needed.

```bash
# Arrow keys
tmux send-keys -t claude-capture:0.0 Right
tmux send-keys -t claude-capture:0.0 Left
tmux send-keys -t claude-capture:0.0 Up
tmux send-keys -t claude-capture:0.0 Down

# Tab / Shift-Tab
tmux send-keys -t claude-capture:0.0 Tab
tmux send-keys -t claude-capture:0.0 BTab

# Escape (cancel / go back)
tmux send-keys -t claude-capture:0.0 Escape

# Ctrl-C (interrupt)
tmux send-keys -t claude-capture:0.0 C-c
```

## Important Rules

| Rule | Description |
|------|-------------|
| **2-call protocol** | Text and C-m must be separate bash calls |
| **Idle before capture** | Always wait for idle before running capture-pane |
| **Idle before send** | Verify pane is idle before sending next command |
| **Special keys: single call** | Arrow, Tab, Escape are sent as single calls (no C-m) |
| **Capture timing** | Wait 1-2s after idle/key before capture for UI to stabilize |
| **No silent decisions** | If unclear what to capture or where to save, ask the user |

For detailed reference: [reference.md](reference.md)

## AI Instructions

When this skill is invoked:

1. **Analyze $ARGUMENTS** to understand what needs to be captured
   - What command(s) or keys to send
   - Whether this is simple output or interactive UI capture
   - Where to save (default: `~/Desktop/` with descriptive filename)

2. **Run setup.sh** to create the tmux session and launch Claude

3. **Execute the capture sequence**:
   - **Simple output**: send command -> wait idle -> capture -> save
   - **Interactive UI**: send command -> wait idle -> send navigation keys -> sleep 1-2s -> capture -> save
   - **Multi-step**: repeat send/wait/capture cycle

4. **Save output** to markdown file
   - Use descriptive filename based on content
   - Include raw terminal output in code blocks
   - If user specified a save path, use that exactly

5. **Report** the capture results and file location to the user

6. **Cleanup** (ask user first if they want to keep the session)

### Always

- Use full script paths: `~/.claude/skills/capturing-claudecode/scripts/setup.sh`
- Use 2-call protocol for text + Enter
- Wait for idle before capturing
- Add sleep 1-2s after idle detection / key press before capture
- Use descriptive filenames based on captured content

### When Claude Code Operations Fail

If a Claude Code command, slash command, or UI interaction does not behave as expected
(e.g., unknown command, unexpected menu structure, changed key bindings):

- Use the `claude-code-guide` sub-agent (Task tool, subagent_type=claude-code-guide) to look up official documentation
- Official docs may not cover every edge case, but often clarify correct command syntax, available options, and UI behavior

### Never

- Capture while pane is busy (output will be incomplete)
- Combine text and C-m in a single send-keys call
- Forget to wait for idle between sequential commands
- Overwrite existing capture files without asking
- Skip cleanup without user confirmation
