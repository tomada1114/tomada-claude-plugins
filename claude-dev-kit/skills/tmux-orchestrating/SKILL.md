---
name: tmux-orchestrating
description: "Orchestrate multiple Claude Code sessions via tmux. Self-contained with setup/cleanup scripts, queue-based task tracking, and report-based completion detection. Use PROACTIVELY when running parallel tasks, multi-agent workflows, orchestrating Claude instances, tmux automation, or when user mentions orchestration, parallel execution, multi-agent, オーケストレーション, 並列実行, マルチエージェント. Examples: <example>Context: User wants parallel execution user: '2つのタスクを並列で実行して' assistant: 'I will use tmux-orchestrating skill' <commentary>Triggered by parallel execution request</commentary></example>"
argument-hint: [goal or task description]
allowed-tools: Bash, Write, Read
---

# tmux Orchestrating

Orchestrate multiple Claude Code sessions in parallel via tmux.
Self-contained skill with scripts, templates, and queue-based communication.

Two modes available:
- **Quick Mode**: Flat management, user's Claude directly manages worker panes
- **Orchestrated Mode**: Pane 0 = orchestrator (middle management), Pane 1+ = workers

## Goal

$ARGUMENTS

## Skill Structure

```
tmux-orchestrating/
├── SKILL.md          # This file (workflow)
├── reference.md      # Troubleshooting, protocols, recovery
├── examples.md       # Extended examples
├── scripts/
│   ├── setup.sh      # Session + panes + Claude launch + idle wait
│   ├── cleanup.sh    # Exit Claude + kill session + clean queue
│   ├── init-queue.sh # Create queue/ directory structure
│   ├── check-status.sh  # Check all panes' status (--json for machine-readable)
│   └── monitor.py    # Live TUI dashboard (run in separate terminal)
└── templates/
    ├── task.md       # Task file template
    ├── report.md     # Report file template
    ├── orchestrator-instructions.md  # Instructions for orchestrator pane
    └── plan.md       # Master plan template
```

## Mode Selection

### Decision Flow

```
Does the invoking Claude already have full task context?
├─ YES: Are tasks pre-decomposed?
│   ├─ YES: Can tasks run in parallel (no dependencies)?
│   │   ├─ YES → Quick Mode (Parallel)
│   │   └─ NO  → Quick Mode (Sequential)
│   └─ NO: → Quick Mode (decompose first, then distribute)
└─ NO: Does the goal need intelligent decomposition by a separate agent?
    ├─ YES → Orchestrated Mode
    └─ NO  → Quick Mode (read context first, then distribute)
```

### Summary

| Mode | When | Overhead |
|------|------|----------|
| **Quick Parallel** | Independent tasks, no dependencies | Low (no orchestrator) |
| **Quick Sequential** | Tasks with A→B→C dependencies, invoker has context | Low (no orchestrator) |
| **Orchestrated** | Invoker lacks context, goal needs delegation + intelligent decomposition | High (extra Claude instance) |

**Key Insight**: If the invoking Claude already read docs/specs and decomposed tasks, **Quick Mode is always preferred**. Orchestrated Mode only adds value when the invoker wants to hand off an unanalyzed goal and return immediately.

## Quick Mode Execution

### Step 1: Setup

```bash
bash ~/.claude/skills/tmux-orchestrating/scripts/setup.sh 2
```

This creates session, panes, initializes queue, launches Claude, waits for idle.

### Step 2: Task Distribution

#### Simple tasks (no queue)

```bash
# 2-call protocol: text and Enter are separate bash calls
tmux send-keys -t orchestration:0.0 "/create-file morning"
tmux send-keys -t orchestration:0.0 C-m

tmux send-keys -t orchestration:0.1 "/create-file evening"
tmux send-keys -t orchestration:0.1 C-m
```

#### Structured tasks (with queue)

```bash
cat > queue/tasks/pane0.md << 'EOF'
# Task: Create add function
## Instructions
Create src/calculator/add.ts with add(a, b) function.
## Completion
When done, write results to `queue/reports/pane0_report.md`:
- status: done | failed
- summary: 1-line summary
- files_modified: list of changed files
EOF

tmux send-keys -t orchestration:0.0 "$(cat queue/tasks/pane0.md)"
tmux send-keys -t orchestration:0.0 C-m
sleep 1
tmux send-keys -t orchestration:0.0 C-m
```

### Step 3: Monitor & Collect

```bash
bash ~/.claude/skills/tmux-orchestrating/scripts/check-status.sh orchestration 2
```

### Step 4: Cleanup

```bash
bash ~/.claude/skills/tmux-orchestrating/scripts/cleanup.sh
```

## Quick Mode Sequential Execution

For tasks with dependencies (A → B → C) where the invoking Claude manages sequencing directly.
**No orchestrator pane needed.** The invoking Claude assigns one worker at a time, waits for report, then assigns the next.

### Step 1: Setup

```bash
# Only the number of workers needed (often 1-2 is enough for sequential)
bash ~/.claude/skills/tmux-orchestrating/scripts/setup.sh 2
```

### Step 2: Write All Task Files Upfront

```bash
# Write all tasks at once (only send them sequentially)
cat > queue/tasks/pane0.md << 'EOF'
# Task: Phase 1 - Data Layer
...
EOF

cat > queue/tasks/pane1.md << 'EOF'
# Task: Phase 2 - UI Components (depends on Phase 1)
...
EOF
```

### Step 3: Send Phase 1 Task

```bash
tmux send-keys -t orchestration:0.0 "$(cat queue/tasks/pane0.md)"
tmux send-keys -t orchestration:0.0 C-m
sleep 1
tmux send-keys -t orchestration:0.0 C-m
```

### Step 4: Wait for Phase 1 Report

```bash
# Check for report file (invoking Claude monitors)
ls queue/reports/pane0_report.md 2>/dev/null
```

### Step 5: Send Phase 2 Task (after Phase 1 completes)

```bash
tmux send-keys -t orchestration:0.1 "$(cat queue/tasks/pane1.md)"
tmux send-keys -t orchestration:0.1 C-m
sleep 1
tmux send-keys -t orchestration:0.1 C-m
```

### Step 6: Cleanup

```bash
bash ~/.claude/skills/tmux-orchestrating/scripts/cleanup.sh
```

**Tip**: For sequential work, you can reuse the same pane. Send `/clear` first to reset context, then send Phase 2 to the same pane.

### Context Reset Between Phases

When reusing a pane for a new task, always send `/clear` first to reset the context window. This prevents previous task context from consuming space and causing earlier compaction.

```bash
# After Phase 1 report confirmed, reset context before Phase 2
tmux send-keys -t orchestration:0.0 "/clear"
tmux send-keys -t orchestration:0.0 C-m

# Wait for clear to complete (prompt reappears)
sleep 3

# Now send Phase 2 task
tmux send-keys -t orchestration:0.0 "$(cat queue/tasks/pane1.md)"
tmux send-keys -t orchestration:0.0 C-m
sleep 1
tmux send-keys -t orchestration:0.0 C-m
```

---

## Orchestrated Mode Execution

### Step 1: Setup with --orchestrated

```bash
# 2 workers + 1 orchestrator = 3 total panes
bash ~/.claude/skills/tmux-orchestrating/scripts/setup.sh 2 orchestration $(pwd) --orchestrated
```

### Step 2: Write Master Plan

```bash
cat > queue/plan.md << 'EOF'
# Master Plan
## Goal
Create a calculator module with add, subtract, multiply, divide.
Each function with full test coverage using TDD.
## Context
- Working directory: /path/to/project
- Worker count: 2
## Additional Notes
Use TypeScript. Follow project coding standards.
EOF
```

### Step 3: Send Orchestrator Instructions

```bash
# Build instruction message
INSTRUCTIONS="Read the master plan at queue/plan.md and the orchestrator instructions at ~/.claude/skills/tmux-orchestrating/templates/orchestrator-instructions.md. You have 2 workers at orchestration:0.1 and orchestration:0.2. Decompose the goal, assign tasks, monitor completion, and write the final report."

tmux send-keys -t orchestration:0.0 "$INSTRUCTIONS"
tmux send-keys -t orchestration:0.0 C-m
```

### Step 4: Return to User

The user's Claude session is now **free**. The orchestrator handles everything.

### Step 5: Check Results (later)

```bash
# Check if orchestration is complete
bash ~/.claude/skills/tmux-orchestrating/scripts/check-status.sh orchestration 2

# Read final report
cat queue/reports/orchestrator_report.md
```

### Step 6: Cleanup

```bash
bash ~/.claude/skills/tmux-orchestrating/scripts/cleanup.sh
```

## Live Monitor (Separate Terminal)

Run in a **separate terminal** for real-time progress tracking:

```bash
python3 ~/.claude/skills/tmux-orchestrating/scripts/monitor.py [SESSION] [WORKERS] [WORK_DIR]

# Examples:
python3 ~/.claude/skills/tmux-orchestrating/scripts/monitor.py
python3 ~/.claude/skills/tmux-orchestrating/scripts/monitor.py orchestration 3 /path/to/project
```

Uses Python Rich (pre-installed). Auto-refreshes every 3 seconds. Press `Ctrl+C` to exit.

## Important Rules

| Rule | Description |
|------|-------------|
| **2-call protocol** | send-keys text and C-m must be separate bash calls |
| **Clean input first** | Send `C-u` before commands to clear any leftover partial input |
| **Idle check** | Verify pane is idle before sending tasks |
| **Queue per pane** | Each pane/worker gets dedicated task/report files |
| **No file sharing** | Multiple panes must not write to the same file (RACE-001) |
| **Context reset** | Send `/clear` before assigning a new task to a pane that already completed a previous task |
| **All-scan** | When checking completion, scan ALL report files |
| **Shell expansion** | Use `"$(cat file)"` not `"\$(cat file)"` for multi-line |
| **Extra Enter** | Multi-line text needs additional C-m after brief sleep |
| **No silent abort** | Never choose to skip/abort follow-up actions without asking the user |
| **Include follow-up** | Task files must include instructions for interactive prompts when user intent is clear |

For detailed reference: [reference.md](reference.md)
For extended examples: [examples.md](examples.md)

## AI Instructions

When this skill is invoked:

1. **Analyze $ARGUMENTS** and decide the execution mode

2. **Mode Decision** (use the Decision Flow in Mode Selection):
   - **Quick Parallel**: Tasks are independent, no dependencies → distribute all at once
   - **Quick Sequential**: Tasks have dependencies (A→B→C), invoker has context → assign one at a time
   - **Orchestrated**: Invoker lacks context, goal needs delegation → hand off to orchestrator

### Quick Mode Parallel Steps

1. **Decide pane count** (1-4) based on task count and independence
2. **Run setup.sh** to create session, panes, and launch Claude
3. **Choose**: Simple commands (direct send-keys) or Queue (structured task files)
4. **Distribute tasks** using 2-call send-keys protocol
5. **Monitor progress** with check-status.sh
6. **Collect results** from report files when all complete
7. **Report to user** with summary
8. **Run cleanup.sh** (ask user first)

### Quick Mode Sequential Steps

1. **Decide pane count** (1-4; often 1 pane suffices for sequential)
2. **Run setup.sh** to create session and launch Claude
3. **Write all task files upfront** to queue/tasks/
4. **Send Phase 1 task** to a worker pane
5. **Monitor**: check report file for Phase 1 completion
6. **Context reset**: Send `/clear` to the pane before assigning the next task
7. **Send Phase 2 task** after `/clear` completes (same or different pane)
8. **Repeat** steps 5-7 for remaining phases
9. **Report to user** with aggregated results
10. **Run cleanup.sh** (ask user first)

### Orchestrated Mode Steps

1. **Decide worker count** (1-4) based on goal complexity
2. **Run setup.sh --orchestrated** to create orchestrator + worker panes
3. **Write queue/plan.md** with the goal and context
4. **Send orchestrator instructions** to Pane 0 (reference the template + plan)
5. **Return to user immediately** -- the user's session is free
6. **Check results later**: read `queue/reports/orchestrator_report.md`
7. **Report to user** with final summary
8. **Run cleanup.sh** (ask user first)

### Interactive Decision Handling (CRITICAL)

Workers may encounter interactive prompts during execution (e.g., review skills asking whether to proceed with fixes, confirmation dialogs, option menus). The invoking Claude MUST follow these rules:

1. **If follow-up instructions were given by the user** → Include them in the task file upfront so workers proceed autonomously. Example: user says "レビューして修正もして" → task file should say "レビュー後、提示された修正方針で修正を実行してください（選択肢が出たら「この方針で修正」を選択）"
2. **If NO follow-up instructions were given** → When a worker hits an interactive prompt and goes Idle, the invoking Claude MUST use AskUserQuestion to ask the user what to do. NEVER choose an option on behalf of the user silently.
3. **"Review only" is never the default** → Do not assume the user wants to stop at review results. A review is always a means to an end (improvement, fixing, rewriting). If the user's intent is unclear, ask.

**Task file template for skills with interactive flows:**

```markdown
## Interactive Decisions
If presented with options after the main task:
- [Option to proceed]: Select this (e.g., "この方針で修正")
- Report file should include both the review results AND the modification results
```

### Always

- Use full script paths: `~/.claude/skills/tmux-orchestrating/scripts/setup.sh`
- Use 2-call protocol for all send-keys
- Check pane idle state before sending tasks
- Send `/clear` before assigning a new task to a pane that already completed a previous task
- Scan ALL report files when checking completion
- Include follow-up action instructions in task files when user intent is clear
- Ask the user via AskUserQuestion when workers hit interactive prompts and no prior instructions exist

### Never

- Send tasks to busy panes
- Assign same file to multiple panes/workers
- Reuse a pane for a new task without sending `/clear` first
- Use escaped shell expansion `"\$(cat ...)"`
- Skip the extra C-m after multi-line text
- Poll in a loop (use event-driven in orchestrated mode)
- Choose interactive options (abort, skip, cancel) on behalf of the user without asking
