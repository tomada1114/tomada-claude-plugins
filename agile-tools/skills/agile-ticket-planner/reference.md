# Agile Ticket Planner Reference

Detailed patterns, examples, and advanced strategies for ticket planning.

## Dependency Graph Patterns

### Pattern 1: Diamond Dependency
```
       [A] Foundation
      /   \
    [B]   [C]  ← Parallel
      \   /
       [D] Integration
```

Ticket strategy:
- A: 【基盤】
- B, C: 【並列可】
- D: 【依存あり】depends on B, C

### Pattern 2: Parallel Streams
```
[A] ────────────────────
 ├── [A1] → [A2] → [A3]  Stream A
 ├── [B1] → [B2] → [B3]  Stream B
 └── [C1] → [C2] → [C3]  Stream C
        ↓
      [Integration]
```

Ticket strategy:
- A: 【基盤】
- A1, B1, C1: 【並列可】start together
- A2, B2, C2: 【順次】within stream, 【並列可】across streams
- Integration: 【依存あり】waits for all streams

### Pattern 3: Feature Slices
```
Feature 1: [Schema] → [Repo] → [Hook] → [UI]
Feature 2: [Schema] → [Repo] → [Hook] → [UI]
Feature 3: [Schema] → [Repo] → [Hook] → [UI]
```

Ticket strategy:
- Combine all schemas into one 【基盤】ticket
- Each feature's Repo+Hook+UI can be【並列可】with worktree

## Worktree Advanced Patterns

### Multi-Developer Setup
```bash
# Developer A works on UI stream
git worktree add ../project-ui-stream feature/ui-home-screen

# Developer B works on Data stream
git worktree add ../project-data-stream feature/data-repositories

# Developer C works on Logic stream
git worktree add ../project-logic-stream feature/business-logic
```

### Worktree with Shared Dependencies
```bash
# When parallel tickets share foundation
# 1. Merge foundation to main first
git checkout main && git merge feature/foundation

# 2. Create worktrees from updated main
git worktree add ../project-feature-a -b feature/feature-a

# 3. In worktree, start from main
cd ../project-feature-a
git log --oneline -3  # Verify foundation is included
```

### Worktree Conflict Prevention
```bash
# Before starting parallel work, define file ownership
# Stream A owns: app/(tabs)/index.tsx, components/home/*
# Stream B owns: database/*, features/*/core/*
# Stream C owns: lib/*, services/*

# Document in each ticket's "Files to Modify" section
```

## Ticket Sizing Guidelines

### Too Small (Combine These)
- "Add TypeScript type for DrinkType" (10 min)
- "Add TypeScript type for Settings" (10 min)
- "Add TypeScript type for DrinkLog" (10 min)

**Better**: One ticket "Type definitions for drink tracking" (30 min)

### Too Large (Split These)
- "Implement entire home screen" (8+ hours)

**Better**: Split into:
1. "Home screen - Progress bars component" (2h)
2. "Home screen - Quick add buttons" (2h)
3. "Home screen - Today's log list" (2h)
4. "Home screen - Integration" (2h)

### Just Right
- Clear single responsibility
- 1-3 hours of work
- 2-5 files modified
- 3-5 acceptance criteria
- Independently testable

## Label System

### Standard Labels
```bash
# Create these labels in your repo
gh label create "parallel" --color "0E8A16" --description "Can work in parallel with other tickets"
gh label create "foundation" --color "5319E7" --description "Must complete before parallel work"
gh label create "blocked" --color "B60205" --description "Waiting on dependency completion"
gh label create "integration" --color "FBCA04" --description "Connects multiple components"
gh label create "sequential" --color "1D76DB" --description "Must follow specific order"
```

### Domain Labels
```bash
gh label create "ui" --color "C5DEF5" --description "User interface work"
gh label create "data" --color "BFD4F2" --description "Data layer work"
gh label create "logic" --color "D4C5F9" --description "Business logic"
gh label create "infra" --color "FEF2C0" --description "Infrastructure/config"
```

### Priority Labels
```bash
gh label create "p0-critical" --color "B60205" --description "Must do first"
gh label create "p1-high" --color "D93F0B" --description "Important"
gh label create "p2-medium" --color "FBCA04" --description "Normal priority"
gh label create "p3-low" --color "0E8A16" --description "Nice to have"
```

## Acceptance Criteria Patterns

### UI Component Ticket
```markdown
## Acceptance Criteria
- [ ] Component renders correctly with default props
- [ ] Component responds to user interaction
- [ ] Component handles edge cases (empty state, loading, error)
- [ ] Accessibility: proper labels and touch targets
- [ ] Component matches design specifications
```

### Data Layer Ticket
```markdown
## Acceptance Criteria
- [ ] CRUD operations work correctly
- [ ] Error handling returns Result type
- [ ] TypeScript types are correctly inferred
- [ ] Database migrations run successfully
- [ ] Unit tests pass
```

### Integration Ticket
```markdown
## Acceptance Criteria
- [ ] Data flows from source to destination
- [ ] Loading states display correctly
- [ ] Error states are handled and displayed
- [ ] Manual end-to-end test passes
- [ ] No TypeScript errors
```

## Real-World Example: HydroCaffeine

### Requirements Analysis
From PROJECT_IDEA.md:
- Water tracking
- Caffeine tracking
- Cutoff time feature
- History view
- Settings
- Onboarding
- Pro features (RevenueCat)

### Identified Streams
1. **Foundation** - Schema, types, constants
2. **UI Stream** - Components, screens
3. **Data Stream** - Repositories, stores
4. **Logic Stream** - Calculations, validations
5. **Integration** - Connect everything

### Complete Ticket Plan

```
=== Phase 1: Foundation 【基盤】===

#1 【基盤】Database schema - Drizzle ORM setup
    Files: database/schema.ts, database/client.ts
    Blocks: #4, #5, #6, #7, #8

#2 【基盤】Type definitions - Domain types
    Files: features/tracking/core/types.ts
    Blocks: #4, #5, #6, #7, #8, #9, #10, #11

#3 【基盤】Theme constants - iOS System Colors
    Files: constants/theme.ts
    Blocks: All UI tickets

=== Phase 2: Parallel Work 【並列可】===

--- UI Stream (worktree: hydro-ui) ---

#4 【並列可/worktree:hydro-ui】Progress bar component
    Depends: #3
    Files: components/ui/progress-bar.tsx

#5 【並列可/worktree:hydro-ui】Quick add buttons
    Depends: #3
    Files: components/quick-add-buttons.tsx

#6 【並列可/worktree:hydro-ui】Today's log list
    Depends: #3
    Files: components/today-log-list.tsx

#7 【並列可/worktree:hydro-ui】Size selection bottom sheet
    Depends: #3
    Files: components/size-selector.tsx

--- Data Stream (worktree: hydro-data) ---

#8 【並列可/worktree:hydro-data】Drink log repository
    Depends: #1, #2
    Files: features/tracking/core/repository.ts

#9 【並列可/worktree:hydro-data】Settings repository
    Depends: #1, #2
    Files: features/settings/core/repository.ts

#10 【並列可/worktree:hydro-data】Zustand store - tracking slice
    Depends: #2
    Files: store/slices/tracking-slice.ts

--- Logic Stream (worktree: hydro-logic) ---

#11 【並列可/worktree:hydro-logic】Caffeine calculation service
    Depends: #2
    Files: features/tracking/core/service.ts

#12 【並列可/worktree:hydro-logic】Cutoff time logic
    Depends: #2
    Files: features/tracking/core/cutoff.ts

#13 【並列可/worktree:hydro-logic】Daily reset logic
    Depends: #2
    Files: features/tracking/core/reset.ts

=== Phase 3: Integration 【依存あり】===

#14 【依存あり】Home screen integration
    Depends: #4, #5, #6, #7, #8, #10, #11, #12
    Files: app/(tabs)/index.tsx

#15 【依存あり】History screen integration
    Depends: #6, #8
    Files: app/(tabs)/history.tsx

#16 【依存あり】Settings screen integration
    Depends: #9
    Files: app/settings.tsx

=== Phase 4: Features 【並列可】===

#17 【並列可】Onboarding flow
    Depends: #9, #14
    Files: app/onboarding/*.tsx

#18 【並列可】Toast notifications
    Depends: #14
    Files: components/toast.tsx

#19 【並列可】Cutoff warning alert
    Depends: #12, #14
    Files: components/cutoff-alert.tsx

=== Phase 5: Pro Features 【順次】===

#20 【基盤】RevenueCat integration setup
    Files: features/subscription/core/*

#21 【依存あり】Paywall UI
    Depends: #20
    Files: components/paywall.tsx

#22 【依存あり】Custom drink feature
    Depends: #20, #21
    Files: features/custom-drinks/*
```

### Worktree Summary
```
Main repo: hydro-caffeine/
├── worktree: hydro-caffeine-ui/      → Issues #4-7
├── worktree: hydro-caffeine-data/    → Issues #8-10
└── worktree: hydro-caffeine-logic/   → Issues #11-13
```

## Milestone Organization

### Sprint-Based Milestones
```bash
# Create milestones
gh api repos/{owner}/{repo}/milestones -f title="Sprint 1: Foundation" -f description="Core infrastructure"
gh api repos/{owner}/{repo}/milestones -f title="Sprint 2: Core Features" -f description="Main functionality"
gh api repos/{owner}/{repo}/milestones -f title="Sprint 3: Polish" -f description="UX and edge cases"
```

### Phase-Based Milestones
```bash
gh api repos/{owner}/{repo}/milestones -f title="Phase 1: MVP Core"
gh api repos/{owner}/{repo}/milestones -f title="Phase 2: Pro Features"
gh api repos/{owner}/{repo}/milestones -f title="Phase 3: Launch Prep"
```

## Tracking Progress

### Project Board Columns
1. **Backlog** - All created tickets
2. **Ready** - Dependencies complete, can start
3. **In Progress** - Currently working
4. **Review** - PR submitted
5. **Done** - Merged to main

### Daily Check
```bash
# See what's ready to work on
gh issue list --label "parallel" --state open

# See what's blocked
gh issue list --label "blocked" --state open

# See completed today
gh issue list --state closed --limit 10
```

## Anti-Patterns to Avoid

### 1. The Monolith Ticket
❌ "Implement home screen with all features"
✅ Split into component-level tickets

### 2. The Micro-Ticket
❌ "Add import statement for X"
✅ Combine related small changes

### 3. The Hidden Dependency
❌ Ticket says "parallel" but needs another ticket's types
✅ Explicitly list all dependencies

### 4. The Vague Acceptance
❌ "Component works correctly"
✅ "Component renders with props X, Y, Z and handles click events"

### 5. The Missing Integration
❌ Create parallel tickets but forget to connect them
✅ Always create integration tickets for parallel streams
