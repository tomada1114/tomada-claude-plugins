# tmux-orchestrating Examples

For the main workflow, see [SKILL.md](SKILL.md).
For detailed reference, see [reference.md](reference.md).

## Example 1: Simple 2-Pane Parallel (No Queue)

Quick mode for simple, short tasks.

```bash
# Setup
bash scripts/setup.sh 2

# Send simple tasks (2-call protocol)
tmux send-keys -t orchestration:0.0 "/create-file morning"
tmux send-keys -t orchestration:0.0 C-m
tmux send-keys -t orchestration:0.1 "/create-file evening"
tmux send-keys -t orchestration:0.1 C-m

# Monitor
tmux capture-pane -t orchestration:0.0 -p | tail -10
tmux capture-pane -t orchestration:0.1 -p | tail -10

# Cleanup
bash scripts/cleanup.sh
```

## Example 2: 2-Pane Parallel with Queue

For tasks requiring structured tracking and reporting.

```bash
# Setup with queue
bash scripts/setup.sh 2

# Write task files
cat > queue/tasks/pane0.md << 'EOF'
# Task: Create add function

## Instructions
Create src/calculator/add.ts:
- Export function add(a: number, b: number): number
- Include input validation
- Create matching test file

## Completion
When done, write results to `queue/reports/pane0_report.md`:
- status: done | failed
- summary: 1-line summary
- files_modified: list of changed files
EOF

cat > queue/tasks/pane1.md << 'EOF'
# Task: Create subtract function

## Instructions
Create src/calculator/subtract.ts:
- Export function subtract(a: number, b: number): number
- Include input validation
- Create matching test file

## Completion
When done, write results to `queue/reports/pane1_report.md`:
- status: done | failed
- summary: 1-line summary
- files_modified: list of changed files
EOF

# Send tasks via shell expansion
tmux send-keys -t orchestration:0.0 "$(cat queue/tasks/pane0.md)"
tmux send-keys -t orchestration:0.0 C-m
sleep 1
tmux send-keys -t orchestration:0.0 C-m

tmux send-keys -t orchestration:0.1 "$(cat queue/tasks/pane1.md)"
tmux send-keys -t orchestration:0.1 C-m
sleep 1
tmux send-keys -t orchestration:0.1 C-m

# Check status
bash scripts/check-status.sh orchestration 2

# Cleanup
bash scripts/cleanup.sh
```

## Example 3: 4-Pane Grid with Queue

For larger parallel workloads (max 4 panes).

```
+--------+--------+
|   0    |   1    |
+--------+--------+
|   2    |   3    |
+--------+--------+
```

```bash
# Setup 4-pane grid
bash scripts/setup.sh 4

# Verify pane layout
tmux list-panes -t orchestration -F "#{pane_index}: #{pane_title}"

# Write 4 task files
for i in 0 1 2 3; do
    FUNC_NAMES=("add" "subtract" "multiply" "divide")
    cat > "queue/tasks/pane${i}.md" << EOF
# Task: Create ${FUNC_NAMES[$i]} function

## Instructions
Create src/calculator/${FUNC_NAMES[$i]}.ts:
- Export function ${FUNC_NAMES[$i]}(a: number, b: number): number
- Include error handling
- Create matching test file

## Completion
When done, write results to queue/reports/pane${i}_report.md:
- status: done | failed
- summary: 1-line summary
- files_modified: list of changed files
EOF
done

# Distribute tasks to all panes
for i in 0 1 2 3; do
    tmux send-keys -t "orchestration:0.${i}" "$(cat queue/tasks/pane${i}.md)"
    tmux send-keys -t "orchestration:0.${i}" C-m
    sleep 1
    tmux send-keys -t "orchestration:0.${i}" C-m
done

# Monitor progress
bash scripts/check-status.sh orchestration 4

# View individual reports
cat queue/reports/pane0_report.md
cat queue/reports/pane1_report.md

# Cleanup
bash scripts/cleanup.sh
```

## Example 4: Git Worktree Parallel

For branch-isolated work to avoid file conflicts.

```bash
# Create worktrees
git worktree add ../feature-a feature-a
git worktree add ../feature-b feature-b

# Setup session
bash scripts/setup.sh 2 worktree-work

# Note: don't use setup.sh's Claude launch for custom dirs
# Launch manually with directory change
tmux send-keys -t worktree-work:0.0 "cd ../feature-a && claude --dangerously-skip-permissions"
tmux send-keys -t worktree-work:0.0 C-m
tmux send-keys -t worktree-work:0.1 "cd ../feature-b && claude --dangerously-skip-permissions"
tmux send-keys -t worktree-work:0.1 C-m

# Wait for startup
sleep 8

# Assign tasks
tmux send-keys -t worktree-work:0.0 "Implement user authentication feature"
tmux send-keys -t worktree-work:0.0 C-m
tmux send-keys -t worktree-work:0.1 "Implement notification system"
tmux send-keys -t worktree-work:0.1 C-m

# Cleanup
bash scripts/cleanup.sh worktree-work
git worktree remove ../feature-a
git worktree remove ../feature-b
```

## Example 5: Monorepo Multi-Package

For monorepo projects with independent packages.

```bash
# Setup
bash scripts/setup.sh 3 monorepo

# Launch Claude in different package directories
tmux send-keys -t monorepo:0.0 "cd packages/frontend && claude --dangerously-skip-permissions"
tmux send-keys -t monorepo:0.0 C-m
tmux send-keys -t monorepo:0.1 "cd packages/backend && claude --dangerously-skip-permissions"
tmux send-keys -t monorepo:0.1 C-m
tmux send-keys -t monorepo:0.2 "cd packages/shared && claude --dangerously-skip-permissions"
tmux send-keys -t monorepo:0.2 C-m

sleep 8

# Assign tasks
tmux send-keys -t monorepo:0.0 "Add form validation to the login page"
tmux send-keys -t monorepo:0.0 C-m
tmux send-keys -t monorepo:0.1 "Add rate limiting to the auth endpoint"
tmux send-keys -t monorepo:0.1 C-m
tmux send-keys -t monorepo:0.2 "Add email validation utility function"
tmux send-keys -t monorepo:0.2 C-m

# Cleanup
bash scripts/cleanup.sh monorepo
```

## Example 6: Test + Lint Parallel

Common pattern: run tests and lint in parallel.

```bash
# Setup
bash scripts/setup.sh 2

# Send tasks
tmux send-keys -t orchestration:0.0 "Run all unit tests and fix any failures"
tmux send-keys -t orchestration:0.0 C-m
tmux send-keys -t orchestration:0.1 "Run eslint and fix all warnings and errors"
tmux send-keys -t orchestration:0.1 C-m

# Monitor
bash scripts/check-status.sh orchestration 2

# Cleanup
bash scripts/cleanup.sh
```

## Example 7: Orchestrated Mode (Delegated Decomposition)

Use when the goal requires intelligent decomposition. The orchestrator (Pane 0)
handles everything -- user's Claude is free immediately.

```bash
# Setup: 2 workers + 1 orchestrator = 3 total panes
bash ~/.claude/skills/tmux-orchestrating/scripts/setup.sh 2 orchestration $(pwd) --orchestrated

# Write master plan
cat > queue/plan.md << 'EOF'
# Master Plan

## Goal
Create a calculator module with add, subtract, multiply, and divide functions.
Each function should have full test coverage using TDD approach.

## Context
- Working directory: /path/to/project
- Worker count: 2
- Project: TypeScript project

## Additional Notes
Use TypeScript. Follow TDD (write tests first). Each function in its own file.
Worker 1 handles add + subtract, Worker 2 handles multiply + divide.
EOF

# Send orchestrator instructions to Pane 0
INSTRUCTIONS="Read the master plan at queue/plan.md and the orchestrator instructions at ~/.claude/skills/tmux-orchestrating/templates/orchestrator-instructions.md. You have 2 workers at orchestration:0.1 and orchestration:0.2. Decompose the goal, assign tasks, monitor completion, and write the final report to queue/reports/orchestrator_report.md."

tmux send-keys -t orchestration:0.0 "$INSTRUCTIONS"
tmux send-keys -t orchestration:0.0 C-m

# User's Claude is now FREE -- can do other work

# Check later if orchestration is complete
bash ~/.claude/skills/tmux-orchestrating/scripts/check-status.sh orchestration 2

# Read final aggregated report
cat queue/reports/orchestrator_report.md

# Cleanup
bash ~/.claude/skills/tmux-orchestrating/scripts/cleanup.sh
```

### What happens internally:

1. Orchestrator reads plan, applies 5-question analysis
2. Orchestrator writes `queue/tasks/worker1.md` and `queue/tasks/worker2.md`
3. Orchestrator sends tasks to workers via send-keys, then **stops**
4. Workers execute tasks, write reports, notify orchestrator via send-keys
5. Orchestrator wakes up, scans all reports, writes `orchestrator_report.md`

## Example 8: Orchestrated Mode with 3 Workers

Larger orchestrated workload with more workers.

```bash
# Setup: 3 workers + 1 orchestrator = 4 total panes
bash ~/.claude/skills/tmux-orchestrating/scripts/setup.sh 3 orchestration $(pwd) --orchestrated

# Write plan
cat > queue/plan.md << 'EOF'
# Master Plan

## Goal
Implement a user authentication system with:
1. Login form component
2. Registration form component
3. Authentication API middleware

## Context
- Working directory: /path/to/project
- Worker count: 3
- Project: Next.js + TypeScript

## Additional Notes
Worker 1: Login form + validation
Worker 2: Registration form + validation
Worker 3: Auth middleware + JWT handling
EOF

# Send orchestrator instructions
tmux send-keys -t orchestration:0.0 "Read queue/plan.md and ~/.claude/skills/tmux-orchestrating/templates/orchestrator-instructions.md. You have 3 workers at orchestration:0.1, orchestration:0.2, orchestration:0.3. Execute the plan."
tmux send-keys -t orchestration:0.0 C-m

# Monitor progress
bash ~/.claude/skills/tmux-orchestrating/scripts/check-status.sh orchestration 3

# Cleanup when done
bash ~/.claude/skills/tmux-orchestrating/scripts/cleanup.sh
```

## Example 9: Quick Mode - Sequential with Dependencies

For tasks with A→B→C dependency chains. The invoking Claude manages sequencing
directly -- no orchestrator needed. Each phase builds on the previous phase's output.

This pattern is ideal for layered architecture (domain → components → page integration)
or any workflow where later tasks depend on files created by earlier tasks.

```bash
# Setup: 1 pane is enough for sequential (reuse same pane)
bash ~/.claude/skills/tmux-orchestrating/scripts/setup.sh 1

# Write all task files upfront
cat > queue/tasks/pane0_phase1.md << 'EOF'
# Task: Phase 1 - Domain Layer

## Instructions
Create the domain layer with TDD:
1. Create src/domain/types.ts (interfaces, type guards)
2. Create src/domain/data.ts (static data)
3. Create src/domain/helpers.ts (query functions)
4. Write tests for all modules

## Completion
When done, write results to `queue/reports/pane0_phase1_report.md`:
- status: done | failed
- summary: 1-line summary
- files_modified: list of changed files
- test_count: number of passing tests
EOF

cat > queue/tasks/pane0_phase2.md << 'EOF'
# Task: Phase 2 - UI Components

## Instructions
Create UI components that import from the domain layer (created in Phase 1):
1. Create src/components/TabBar.tsx (navigation)
2. Create src/components/Card.tsx (display card)
3. Create src/components/DetailView.tsx (expanded view)
4. Write tests for all components

## Completion
When done, write results to `queue/reports/pane0_phase2_report.md`:
- status: done | failed
- summary: 1-line summary
- files_modified: list of changed files
- test_count: number of passing tests
EOF

cat > queue/tasks/pane0_phase3.md << 'EOF'
# Task: Phase 3 - Page Integration

## Instructions
Create the main page that composes domain + components (from Phases 1-2):
1. Update app/globals.css (design tokens)
2. Update app/layout.tsx (fonts, metadata)
3. Create app/page.tsx (state management, composition)
4. Write integration tests

## Completion
When done, write results to `queue/reports/pane0_phase3_report.md`:
- status: done | failed
- summary: 1-line summary
- files_modified: list of changed files
- test_count: number of passing tests
EOF

# --- Phase 1: Send and wait ---
tmux send-keys -t orchestration:0.0 "$(cat queue/tasks/pane0_phase1.md)"
tmux send-keys -t orchestration:0.0 C-m
sleep 1
tmux send-keys -t orchestration:0.0 C-m

# Poll for Phase 1 completion (check report file)
# Claude Code tasks take significant time (development/writing: 5-30+ min)
# Poll every 180s, max 20 retries = ~60 min timeout
MAX_RETRIES=20
for attempt in $(seq 1 $MAX_RETRIES); do
    if [ -f "queue/reports/pane0_phase1_report.md" ]; then
        echo "Phase 1 complete!"
        break
    fi
    echo "Waiting for Phase 1... ($attempt/$MAX_RETRIES)"
    sleep 180
done

# --- Phase 2: Send after Phase 1 completes ---
# Verify pane is idle before sending
BUSY_RE="Thinking|Esc to interrupt|Boogieing|Mulling|Churning|Implementing|Writing|Reading|Searching|Running|✽|✶|✢|✳|✻"
IDLE_RE="❯ |bypass permissions on|to cycle\)"
for attempt in $(seq 1 12); do
    OUTPUT=$(tmux capture-pane -t orchestration:0.0 -p | tail -15)
    if echo "$OUTPUT" | grep -qE "$IDLE_RE" && ! echo "$OUTPUT" | grep -qE "$BUSY_RE"; then
        break
    fi
    sleep 30
done

# Context reset: clear previous phase context before sending new task
tmux send-keys -t orchestration:0.0 "/clear"
tmux send-keys -t orchestration:0.0 C-m
sleep 3

tmux send-keys -t orchestration:0.0 "$(cat queue/tasks/pane0_phase2.md)"
tmux send-keys -t orchestration:0.0 C-m
sleep 1
tmux send-keys -t orchestration:0.0 C-m

# Poll for Phase 2 completion
for attempt in $(seq 1 $MAX_RETRIES); do
    if [ -f "queue/reports/pane0_phase2_report.md" ]; then
        echo "Phase 2 complete!"
        break
    fi
    sleep 180
done

# --- Phase 3: Send after Phase 2 completes ---
for attempt in $(seq 1 12); do
    OUTPUT=$(tmux capture-pane -t orchestration:0.0 -p | tail -15)
    if echo "$OUTPUT" | grep -qE "$IDLE_RE" && ! echo "$OUTPUT" | grep -qE "$BUSY_RE"; then
        break
    fi
    sleep 30
done

# Context reset before Phase 3
tmux send-keys -t orchestration:0.0 "/clear"
tmux send-keys -t orchestration:0.0 C-m
sleep 3

tmux send-keys -t orchestration:0.0 "$(cat queue/tasks/pane0_phase3.md)"
tmux send-keys -t orchestration:0.0 C-m
sleep 1
tmux send-keys -t orchestration:0.0 C-m

# Wait for final phase
for attempt in $(seq 1 $MAX_RETRIES); do
    if [ -f "queue/reports/pane0_phase3_report.md" ]; then
        echo "Phase 3 complete! All phases done."
        break
    fi
    sleep 180
done

# Collect all results
echo "=== Sequential Results ==="
for phase in 1 2 3; do
    echo "--- Phase $phase ---"
    cat "queue/reports/pane0_phase${phase}_report.md"
    echo ""
done

# Cleanup
bash ~/.claude/skills/tmux-orchestrating/scripts/cleanup.sh
```

### Key differences from parallel mode:

1. **Single pane reuse**: Same pane executes all phases sequentially
2. **Report-gated progression**: Phase N+1 only starts after Phase N's report file exists
3. **Context reset between phases**: Always send `/clear` before assigning the next phase
4. **Idle check between phases**: Always verify the pane is idle before sending the next task
5. **All task files written upfront**: Tasks are prepared ahead of time, only sent sequentially
6. **Layered dependencies**: Each phase imports from the previous phase's output files
