# tmux-orchestrating Reference

Detailed technical reference for the tmux-orchestrating skill.
For the main workflow, see [SKILL.md](SKILL.md).
For examples, see [examples.md](examples.md).

## send-keys 2-Call Protocol

`tmux send-keys` must be split into 2 separate bash calls: text and Enter.

### Why

When text and `Enter`/`C-m` are combined in a single call, Enter can be misinterpreted
by tmux, especially with multi-line text or special characters. The 2-call pattern is
consistently reliable.

### Pre-Send Input Cleanup

Before sending any text, ensure the Claude Code input field is empty. Leftover partial input
will corrupt the command. Use `C-u` (clear line) or repeated `BSpace` to clean up:

```bash
# Clear any leftover input before sending (C-u clears the entire line)
tmux send-keys -t orchestration:0.0 C-u
```

If `C-u` is unreliable, use `Escape` to cancel partial input (when Claude is idle, Escape clears the input field):

```bash
tmux send-keys -t orchestration:0.0 Escape
sleep 1
```

### Correct Pattern

```bash
# Call 0 (if needed): Clear leftover input
tmux send-keys -t orchestration:0.0 C-u
# Call 1: Send text
tmux send-keys -t orchestration:0.0 '/create-file morning'
# Call 2: Press Enter (separate bash call)
tmux send-keys -t orchestration:0.0 C-m
```

### Wrong Patterns

```bash
# NG: Combined in one call (Enter may not register)
tmux send-keys -t orchestration:0.0 '/create-file morning' Enter

# NG: Chained with && (still one shell context)
tmux send-keys -t orchestration:0.0 'message' && tmux send-keys -t orchestration:0.0 Enter

# NG: Escaped shell expansion (becomes literal string)
tmux send-keys -t orchestration:0.0 "\$(cat /tmp/task.txt)" C-m
```

### Multi-line Text

For multi-line instructions, use a temporary file with shell expansion:

```bash
# Write task to file
cat > queue/tasks/pane0.md << 'EOF'
Create src/add.ts with an add(a, b) function.
Export the function. Include error handling.
EOF

# Call 1: Send content via shell expansion
tmux send-keys -t orchestration:0.0 "$(cat queue/tasks/pane0.md)"
# Call 2: Enter
sleep 1
tmux send-keys -t orchestration:0.0 C-m
# Call 3: Extra Enter (sometimes needed for multi-line)
sleep 1
tmux send-keys -t orchestration:0.0 C-m
```

## Task Duration Expectations

Claude Code tasks take significant time. Set polling intervals accordingly.

| Task Type | Typical Duration | Examples |
|-----------|-----------------|----------|
| **Slash commands** | 5-30s | `/clear`, `/help`, simple commands |
| **Read-only analysis** | 30s-3min | Code review, search, explain |
| **Small writes** | 3-10min | Single file fix, add function, config change |
| **Development tasks** | 10-30min | Feature implementation, TDD cycle, multi-file refactoring |
| **Large writing** | 15-60min | Article writing, comprehensive documentation, full module creation |

### Recommended Polling Intervals

| Polling purpose | Interval | Max retries | Total timeout |
|-----------------|----------|-------------|---------------|
| **Report completion** (waiting for task result) | 180s | 20 | ~60 min |
| **monitor.sh** (automated monitoring loop) | 30-180s | configurable | up to 20 min |
| **Idle check** (pane busy → idle transition) | 30s | 12 | ~6 min |
| **Quick command** (`/clear`, startup) | 3s | 10 | ~30s |

## Automated Monitoring (monitor.sh)

`monitor.sh` wraps `check-status.sh` with a polling loop, automatic interventions, and stall detection.
It replaces manual `sleep` + `check-status.sh` loops.

### Usage

```bash
bash ~/.claude/skills/tmux-orchestrating/scripts/monitor.sh [OPTIONS] SESSION_NAME PANE_COUNT [WORK_DIR]
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--interval N` | 180 | Polling interval in seconds |
| `--timeout N` | 1200 | Total timeout in seconds |
| `--initial-wait N` | 60 | Wait before first check |
| `--auto-select` | off | Send Enter when WaitingInput detected |
| `--nudge-prompt TEXT` | (built-in) | Prompt to send for IdleNoReport. Use `{N}` for pane number |
| `--stall-threshold N` | 3 | Consecutive identical checks before stall exit |

### Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| `0` | All panes complete | Proceed to results |
| `1` | Timeout | Ask user to continue/abort |
| `2` | Stall detected | Manual intervention needed |

### Example: Book Orchestration

```bash
bash ~/.claude/skills/tmux-orchestrating/scripts/monitor.sh \
  --interval 30 --timeout 1200 --initial-wait 60 \
  --auto-select \
  --nudge-prompt "レポート未作成です。queue/reports/pane{N}_report.md を作成してください。" \
  orchestration 4 "$(pwd)"
```

### Automatic Interventions

- **WaitingInput**: Sends Enter once per pane (auto-selects first option in AskUserQuestion UI)
- **IdleNoReport**: Sends nudge prompt once per pane (reminds worker to write report)
- **Stall**: Exits with code 2 after N consecutive identical status checks on all remaining panes

### Bash 3.2 Compatibility

monitor.sh uses `eval` for per-pane state tracking instead of associative arrays,
ensuring compatibility with macOS's default bash 3.2.

## Claude Code Control Commands

Reference for controlling Claude Code instances in tmux panes via send-keys.

### Commands

| Action | send-keys | Effect |
|--------|-----------|--------|
| **Clear context** | `/clear` + `C-m` | Resets conversation context. Claude stays running. |
| **Exit Claude** | `/exit` + `C-m` | Cleanly exits Claude Code. Returns to shell. |
| **Exit Claude (alt)** | `C-c` then `C-c` | Two consecutive Ctrl+C exits Claude Code. |
| **Interrupt task** | `Escape` or `C-c` | Interrupts current processing. Claude stays idle. Does not exit. |

### tmux send-keys Patterns

```bash
# Clear context (reset for new task)
tmux send-keys -t orchestration:0.0 "/clear"
tmux send-keys -t orchestration:0.0 C-m

# Exit Claude Code
tmux send-keys -t orchestration:0.0 "/exit"
tmux send-keys -t orchestration:0.0 C-m

# Exit via Ctrl+C x2
tmux send-keys -t orchestration:0.0 C-c
sleep 1
tmux send-keys -t orchestration:0.0 C-c

# Interrupt current task (does not exit)
tmux send-keys -t orchestration:0.0 Escape
```

### When to Use

| Scenario | Command |
|----------|---------|
| Pane finished task, assigning new unrelated task | `/clear` |
| Sequential phase transition (Phase 1 done, start Phase 2) | `/clear` |
| Worker stuck or unresponsive, need to stop current work | `Escape` or `C-c` |
| Cleanup: terminating all Claude instances | `/exit` or `C-c` x2 |
| Worker in bad state, need full restart | `C-c` x2, then relaunch `claude` |

## Busy/Idle Detection

Before sending tasks, verify the target pane is ready to receive input.

### Indicators

| Type | Patterns | Meaning |
|------|----------|---------|
| **Busy (verbs)** | `Thinking`, `Effecting`, `Boondoggling`, `Puzzling`, `Calculating`, `Fermenting`, `Crunching`, `Boogieing`, `Mulling`, `Churning`, `Implementing`, `Writing`, `Reading`, `Searching`, `Running` | Claude is processing. Do NOT send tasks. |
| **Busy (UI)** | `Esc to interrupt`, `✽`, `✶`, `✢`, `✳`, `✻` | Unicode spinners or interrupt hint visible. |
| **Busy (status)** | `Worked for`, `Cooked for`, `Churned for` | Completion message (Claude just finished, prompt may appear shortly). |
| **Idle** | `❯ ` (prompt char + space), `bypass permissions on`, `to cycle)` | Claude is waiting for input. Safe to send. |

### Extended States (check-status.sh)

| State | Detection | Priority | Meaning |
|-------|-----------|----------|---------|
| **WaitingInput** | `Enter to select` in capture-pane | Highest (before Busy) | AskUserQuestion selection UI is blocking. Send Enter to auto-select. |
| **IdleNoReport** | Idle AND task file exists AND report file missing | After Idle | Worker finished but forgot to write report. Send nudge prompt. |
| **Error** | Idle AND `Error:\|APIError\|Permission denied\|EACCES\|panic:\|Traceback\|FATAL` | After Idle, before IdleNoReport | Worker hit an error. May need manual intervention. |

**Detection priority order**: WaitingInput > Busy > Idle(Error/IdleNoReport/Idle) > Unknown

**Important**: Always check Busy patterns BEFORE Idle patterns. A pane can display both
a prompt `❯` and a spinner `✽` simultaneously during certain states. Busy takes priority.

### Pre-Send Check

```bash
OUTPUT=$(tmux capture-pane -t orchestration:0.0 -p | tail -15)

BUSY_RE="Thinking|Esc to interrupt|Boogieing|Mulling|Churning|Implementing|Writing|Reading|Searching|Running|✽|✶|✢|✳|✻"
IDLE_RE="❯ |bypass permissions on|to cycle\)"

# Check busy first (takes priority)
if echo "$OUTPUT" | grep -qE "$BUSY_RE"; then
    echo "Pane 0 is busy. Waiting..."
    sleep 30
# Then check idle
elif echo "$OUTPUT" | grep -qE "$IDLE_RE"; then
    # Clean input field before sending (clear any leftover partial input)
    tmux send-keys -t orchestration:0.0 C-u
    echo "Pane 0 is idle. Ready to send."
fi
```

### Retry Protocol

When a pane is busy, retry with 30-second intervals. Claude Code tasks can take significant time --
read-only commands may finish in under a minute, but writing tasks (development, article writing,
refactoring) often run 5-30+ minutes.

```bash
MAX_RETRIES=12
BUSY_RE="Thinking|Esc to interrupt|Boogieing|Mulling|Churning|Implementing|Writing|Reading|Searching|Running|✽|✶|✢|✳|✻"
IDLE_RE="❯ |bypass permissions on"
for attempt in $(seq 1 $MAX_RETRIES); do
    OUTPUT=$(tmux capture-pane -t orchestration:0.0 -p | tail -15)
    if echo "$OUTPUT" | grep -qE "$IDLE_RE" && ! echo "$OUTPUT" | grep -qE "$BUSY_RE"; then
        break
    fi
    echo "Attempt $attempt/$MAX_RETRIES: Pane busy, waiting 30s..."
    sleep 30
done
```

## Context Reset Between Tasks

When a pane completes a task and will be reused for a different task or ticket, send `/clear` to reset the context window before assigning the new task.

### Why

Claude Code accumulates context from file reads, tool calls, and reasoning during a task. Without clearing, the next task starts with a partially filled context window, which:
- Wastes context capacity on irrelevant previous task data
- Causes earlier context compaction, degrading quality
- Risks previous task context bleeding into the new task's reasoning

### When to Clear

| Scenario | Clear needed? |
|----------|---------------|
| Same pane, new unrelated task | **Yes** - always `/clear` |
| Same pane, follow-up phase in a sequential chain | **Yes** - previous phase files are on disk, not needed in context |
| Pane finished batch, reusing for next batch | **Yes** - always `/clear` |
| Worker getting a continuation of the same interrupted task | **No** - context is useful for resuming |

### Clear Protocol

```bash
# 1. Verify pane is idle
OUTPUT=$(tmux capture-pane -t orchestration:0.0 -p | tail -15)

# 2. Send /clear (2-call protocol)
tmux send-keys -t orchestration:0.0 "/clear"
tmux send-keys -t orchestration:0.0 C-m

# 3. Wait for clear to complete and prompt to reappear
sleep 3

# 4. Verify pane is idle again before sending new task
OUTPUT=$(tmux capture-pane -t orchestration:0.0 -p | tail -15)
IDLE_RE="❯ |bypass permissions on|to cycle\)"
if echo "$OUTPUT" | grep -qE "$IDLE_RE"; then
    echo "Pane ready for new task"
fi
```

### Idle Detection After Clear

After `/clear`, Claude Code briefly processes then returns to idle. The prompt `❯` reappears. Use the standard Busy/Idle detection (see below) to confirm readiness before sending the next task.

## Worker Interruption Recovery

When a worker is interrupted mid-task (user presses Escape or Ctrl-C in the tmux pane),
the pane output will show:

```
⏺ Write(app/some-file.tsx)
  ⎿  Error: Interrupted by user
```

### Detection

```bash
OUTPUT=$(tmux capture-pane -t orchestration:0.1 -p -S -50)
if echo "$OUTPUT" | grep -q "Error: Interrupted by user"; then
    echo "Worker was interrupted!"
fi
```

### Recovery Steps

1. **Check what was completed**: Look at which files exist vs. the task file
2. **Send a resume command** to the worker:

```bash
tmux send-keys -t orchestration:0.1 "Continue where you left off. You were interrupted. Complete the remaining work from your original task, then write your report to queue/reports/workerN_report.md."
tmux send-keys -t orchestration:0.1 C-m
sleep 1
tmux send-keys -t orchestration:0.1 C-m
```

3. **If worker context is lost** (compaction), re-send the full task:

```bash
tmux send-keys -t orchestration:0.1 "$(cat queue/tasks/worker1.md)"
tmux send-keys -t orchestration:0.1 C-m
sleep 1
tmux send-keys -t orchestration:0.1 C-m
```

### Prevention

- Warn users not to interact with tmux panes during orchestration
- Use `tmux set-option -t orchestration remain-on-exit on` to prevent accidental pane closure

## Queue Directory Convention

### Structure

```
queue/
├── .gitignore    # Contains "*" (ignore all queue files in git)
├── tasks/
│   ├── pane0.md  # Task for pane 0
│   ├── pane1.md  # Task for pane 1
│   ├── pane2.md  # Task for pane 2
│   └── pane3.md  # Task for pane 3
└── reports/
    ├── pane0_report.md  # Completion report from pane 0
    ├── pane1_report.md  # Completion report from pane 1
    ├── pane2_report.md  # Completion report from pane 2
    └── pane3_report.md  # Completion report from pane 3
```

### Task File Format

```markdown
# Task: [Brief description]

## Instructions
[Detailed instructions for the worker Claude]

## Completion
When done, write results to `queue/reports/pane{N}_report.md`:
- status: done | failed
- summary: 1-line summary
- files_modified: list of changed files
- error: (if failed) error description
```

### Report File Format

```markdown
status: done
summary: Created add.ts with exported add function and error handling
files_modified:
  - src/add.ts
  - src/add.test.ts
```

Failed report:
```markdown
status: failed
summary: Could not create file due to permission error
error: EACCES: permission denied, open '/src/add.ts'
```

### All-Scan Protocol

When checking completion, always scan ALL report files, not just the one expected.
This catches cases where a faster worker finishes out of order or a notification was missed.

```bash
COMPLETED=0
TOTAL=2
for i in $(seq 0 $((TOTAL - 1))); do
    if [ -f "queue/reports/pane${i}_report.md" ]; then
        COMPLETED=$((COMPLETED + 1))
    fi
done
echo "Progress: ${COMPLETED}/${TOTAL}"
```

## Race Condition Prevention (RACE-001)

Multiple workers must NEVER write to the same file simultaneously.

### Rules

1. Each worker writes only to its own report file (`queue/reports/pane{N}_report.md`)
2. Assign tasks so workers modify different files
3. For shared resources, use sequential execution (not parallel)

### Strategies

| Scenario | Strategy |
|----------|----------|
| Different source files | Parallel (safe) |
| Same source file | Sequential (one worker at a time) |
| Shared output file | Split into per-worker output files |
| Git operations | Use git worktree for separate branches |

### Git Worktree Pattern

```bash
git worktree add ../feature-a feature-a
git worktree add ../feature-b feature-b

# Pane 0 works in ../feature-a
# Pane 1 works in ../feature-b
# No file conflicts possible
```

## Context Compaction Recovery

When Claude's context is compacted (long session), state can be recovered from queue files.

### Source of Truth

| Source | Contains | Priority |
|--------|----------|----------|
| `queue/tasks/pane{N}.md` | What was assigned to each worker | Primary |
| `queue/reports/pane{N}_report.md` | What each worker completed | Primary |
| `tmux capture-pane` output | Current terminal state | Secondary |

### Recovery Steps

1. Check `queue/tasks/` for assigned tasks
2. Check `queue/reports/` for completed tasks
3. Identify which tasks are still in progress (task exists, no report)
4. Resume monitoring for in-progress tasks
5. Report completed results to user

```bash
# Quick recovery check
echo "=== Task Status ==="
for i in 0 1 2 3; do
    TASK_EXISTS=$([ -f "queue/tasks/pane${i}.md" ] && echo "yes" || echo "no")
    REPORT_EXISTS=$([ -f "queue/reports/pane${i}_report.md" ] && echo "yes" || echo "no")

    if [[ "$TASK_EXISTS" == "yes" && "$REPORT_EXISTS" == "yes" ]]; then
        echo "Pane $i: COMPLETE"
    elif [[ "$TASK_EXISTS" == "yes" && "$REPORT_EXISTS" == "no" ]]; then
        echo "Pane $i: IN PROGRESS"
    elif [[ "$TASK_EXISTS" == "no" ]]; then
        echo "Pane $i: NO TASK"
    fi
done
```

## Troubleshooting

### Session Name Duplication

```
duplicate session: orchestration
```

**Fix:** `setup.sh` handles this automatically. Manual fix:
```bash
tmux kill-session -t orchestration 2>/dev/null
tmux new-session -d -s orchestration
```

### Pane Numbers Shift

Pane numbers can change after splitting. Always verify:

```bash
tmux list-panes -t orchestration -F "#{pane_index}: #{pane_current_command} #{pane_title}"
```

### Claude Code Startup Failure

```
claude: command not found
```

**Fix:** Use full path:
```bash
tmux send-keys -t orchestration:0.0 "$(which claude) --dangerously-skip-permissions"
tmux send-keys -t orchestration:0.0 C-m
```

### Pane Unresponsive

```bash
# Try C-c to interrupt
tmux send-keys -t orchestration:0.0 C-c
sleep 2

# Check state
tmux capture-pane -t orchestration:0.0 -p | tail -10

# If still stuck, restart Claude in that pane
tmux send-keys -t orchestration:0.0 "exit" C-m
sleep 1
tmux send-keys -t orchestration:0.0 "claude --dangerously-skip-permissions"
tmux send-keys -t orchestration:0.0 C-m
```

### Multi-line Text Not Confirming

Claude Code may be waiting for input confirmation:
```bash
# Send extra Enter
tmux send-keys -t orchestration:0.0 C-m
```

### send-keys Lost (Busy Pane)

If a pane was busy when send-keys was sent, the text may be lost or garbled.

**Fix:** Use the Busy/Idle detection (above) before sending.
If already sent to a busy pane, wait for idle then re-send the task.

## Pane Layout Reference

### 2-Pane (Horizontal Split)

```
+--------+--------+
|   0    |   1    |
+--------+--------+
```

```bash
tmux split-window -h -t orchestration
```

### 3-Pane (1 + 2 Layout)

```
+--------+--------+
|        |   1    |
|   0    +--------+
|        |   2    |
+--------+--------+
```

```bash
tmux split-window -h -t orchestration:0.0
tmux split-window -v -t orchestration:0.1
```

### 4-Pane (2x2 Tiled Grid)

```
+--------+--------+
|   0    |   1    |
+--------+--------+
|   2    |   3    |
+--------+--------+
```

```bash
tmux split-window -h -t orchestration:0
tmux split-window -v -t orchestration:0.0
tmux split-window -v -t orchestration:0.2
tmux select-layout -t orchestration tiled
```

## Orchestrated Mode Protocol

### Architecture

```
User's Claude (Invoker)
  |-- writes queue/plan.md
  |-- send-keys to Pane 0 (orchestrator instructions)
  |-- RETURNS to user immediately

Orchestrator (Pane 0)
  |-- reads queue/plan.md
  |-- 5-question analysis (goal, decomposition, worker count, perspective, risk)
  |-- writes queue/tasks/worker{N}.md
  |-- send-keys to Pane 1..N (workers)
  |-- STOPS (event-driven, no polling)

Workers (Pane 1+)
  |-- reads queue/tasks/worker{N}.md
  |-- executes task
  |-- writes queue/reports/worker{N}_report.md
  |-- send-keys to Pane 0 (notifies orchestrator)

Orchestrator (woken by worker)
  |-- all-scan: reads ALL queue/reports/worker{N}_report.md
  |-- if all done -> writes queue/reports/orchestrator_report.md
  |-- if not all done -> STOPS again
```

### Event-Driven vs Polling

The orchestrator **never polls**. After assigning tasks, it stops and waits.
Workers notify the orchestrator via `send-keys` when they finish.

On each wake-up, the orchestrator scans ALL report files (all-scan protocol).
This handles missed notifications -- if a worker's send-keys was lost because the
orchestrator was briefly busy, the next worker's notification triggers a full scan
that catches the missed report.

### Queue Directory (Orchestrated Mode)

```
queue/
├── .gitignore                       # Contains "*"
├── plan.md                          # Master plan (mode marker)
├── tasks/
│   ├── worker1.md                   # Task for worker 1
│   ├── worker2.md                   # Task for worker 2
│   └── worker3.md                   # Task for worker 3
└── reports/
    ├── worker1_report.md            # Report from worker 1
    ├── worker2_report.md            # Report from worker 2
    ├── worker3_report.md            # Report from worker 3
    └── orchestrator_report.md       # Final aggregated report
```

**Mode detection**: `queue/plan.md` existence indicates orchestrated mode.
Scripts auto-detect this.

### Orchestrator Compaction Recovery

If the orchestrator's context is compacted mid-orchestration:

1. Read `queue/plan.md` for the original goal
2. Read `queue/tasks/worker{N}.md` for assigned tasks
3. Read `queue/reports/worker{N}_report.md` for completed tasks
4. If all done: write `queue/reports/orchestrator_report.md`
5. If not all done: STOP and wait for remaining workers

```bash
echo "=== Orchestrator Recovery ==="
for i in 1 2 3 4; do
    TASK=$([ -f "queue/tasks/worker${i}.md" ] && echo "assigned" || echo "none")
    REPORT=$([ -f "queue/reports/worker${i}_report.md" ] && echo "done" || echo "pending")
    [[ "$TASK" == "assigned" ]] && echo "Worker $i: task=$TASK report=$REPORT"
done
[[ -f "queue/reports/orchestrator_report.md" ]] && echo "Final report: EXISTS" || echo "Final report: NOT YET"
```

### 5-Pane Layout (Orchestrated, 4 Workers)

```
+------------+------------+
| Orchestr.  |  Worker 1  |
|   (0)      |   (1)      |
+------------+------------+
|  Worker 2  |  Worker 3  |
|   (2)      |   (3)      |
+------+-----+------------+
|      Worker 4 (4)       |
+-------------------------+
```

## Working Directory Management

### Same Directory (Default)

`setup.sh` creates all panes with the same working directory.

### Different Directories

Launch Claude with `cd` prefix:

```bash
tmux send-keys -t orchestration:0.0 "cd packages/frontend && claude --dangerously-skip-permissions"
tmux send-keys -t orchestration:0.0 C-m
tmux send-keys -t orchestration:0.1 "cd packages/backend && claude --dangerously-skip-permissions"
tmux send-keys -t orchestration:0.1 C-m
```

### Monorepo Pattern

Use git worktree for branch isolation:

```bash
git worktree add ../feature-a feature-a
git worktree add ../feature-b feature-b

tmux send-keys -t orchestration:0.0 "cd ../feature-a && claude --dangerously-skip-permissions"
tmux send-keys -t orchestration:0.0 C-m
tmux send-keys -t orchestration:0.1 "cd ../feature-b && claude --dangerously-skip-permissions"
tmux send-keys -t orchestration:0.1 C-m
```
