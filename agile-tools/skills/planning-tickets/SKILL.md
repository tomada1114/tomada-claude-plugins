---
name: planning-tickets
description: Plan and create GitHub Issues with agile/scrum methodology. Analyze requirements, identify parallel work, manage dependencies, and suggest git worktree strategies. Use PROACTIVELY when creating tickets, planning sprints, breaking down features, organizing issues, identifying parallel tasks, managing dependencies, or working with GitHub Issues, scrum, agile planning, ticket breakdown, worktree planning. Examples: <example>Context: User wants to plan implementation user: 'チケットを作っていこう' assistant: 'I will use planning-tickets skill' <commentary>Triggered by ticket creation request</commentary></example> <example>Context: User has requirements user: 'この要件をIssueに分割して' assistant: 'I will use planning-tickets skill' <commentary>Triggered by issue breakdown request</commentary></example>
---

# Agile Ticket Planner

Plan and create GitHub Issues with agile/scrum methodology, focusing on parallel work identification, dependency management, and git worktree optimization.

## When to Use This Skill

- Breaking down requirements into GitHub Issues
- Planning sprints with parallel workstreams
- Identifying which tasks can be done independently
- Setting up git worktree strategies for parallel development
- Creating tickets with clear dependency relationships
- Organizing work for multiple developers

## Core Principles

### 1. Small, Completable Units
Each ticket should be:
- Completable in 1-3 hours (ideal)
- Testable independently
- Deliverable as a shippable increment

### 2. Independence Over Granularity
- Prioritize independence over small size
- Merge related tasks if splitting creates dependencies
- A larger independent ticket > multiple dependent small tickets

### 3. Parallel Work First
- Identify what can be done simultaneously
- Design tickets to minimize blocking relationships
- Enable multiple developers to work concurrently

## Ticket Title Format

```
【並列可】Feature description - Specific scope
【依存あり】Feature description - Specific scope
【基盤】Infrastructure - Must complete first
【並列可/worktree:feature-xxx】Feature with worktree suggestion
```

### Title Prefixes

| Prefix | Meaning | When to Use |
|--------|---------|-------------|
| 【並列可】 | Parallel OK | Can work independently |
| 【依存あり】 | Has Dependencies | Must wait for other tickets |
| 【基盤】 | Foundation | Required before parallel work |
| 【並列可/worktree:name】 | Parallel + Worktree | Suggests worktree branch name |
| 【順次】 | Sequential | Must follow specific order |

## Ticket Body Principles

**Goal**: "誰が実装しても要件は絶対に満たせる" (Anyone can implement and definitely satisfy requirements)

### EARS (Easy Approach to Requirements Syntax)

Use EARS format for unambiguous, testable requirements:

| Pattern | Template | Example |
|---------|----------|---------|
| **Ubiquitous** | The [system] shall [action] | The button shall have 44pt minimum touch target. |
| **Event-driven** | **When** [trigger], the [system] shall [action] | **When** user taps "Coffee", the system shall display size selection sheet. |
| **State-driven** | **While** [state], the [system] shall [action] | **While** loading, the system shall display spinner. |
| **Unwanted** | **If** [condition], **then** the [system] shall [action] | **If** save fails, **then** the system shall show error toast. |
| **Optional** | **Where** [feature], the [system] shall [action] | **Where** Pro subscription is active, the system shall allow unlimited custom drinks. |
| **Complex** | Combine patterns | **While** after cutoff time, **when** user selects caffeine drink, the system shall show warning alert. |

### Key Sections for Requirement Clarity

1. **User Story** - Why this feature exists
   - As a [user type], I want [goal], So that [benefit]

2. **Functional Requirements (EARS Format)** - What exactly should happen
   - Core Requirements (Event-driven)
   - State-Dependent Requirements
   - Error Handling Requirements (Unwanted behavior)
   - Optional Requirements (Pro features)

3. **Boundary Conditions** - Edge cases with EARS format
   - Minimum/Maximum values
   - Empty/null handling
   - Over-limit behavior

4. **Concrete Examples** - Specific scenarios with numbers
   - Trigger → State → Result → Verification

5. **Not In Scope** - What this ticket does NOT include
   - Prevents scope creep
   - Clarifies boundaries

6. **Acceptance Criteria** - Tied to requirement IDs
   - REQ-001: [Testable condition]
   - Each EARS requirement maps to acceptance criterion

### Template Quick Reference

```markdown
## User Story
**As a** [user type]
**I want** [goal/desire]
**So that** [benefit/value]

## Background & Context
Reference: PROJECT_IDEA.md Section X.X

## Functional Requirements (EARS Format)

### Core Requirements
| ID | Requirement |
|----|-------------|
| REQ-001 | **When** user taps "Coffee" button, the system shall display size selection bottom sheet. |
| REQ-002 | **When** user selects 250ml, the system shall record drink with calculated caffeine (250ml × 60mg/100ml = 150mg). |

### State-Dependent Requirements
| ID | Requirement |
|----|-------------|
| REQ-010 | **While** current caffeine ≥ daily limit, the system shall display progress bar at 100%. |

### Error Handling Requirements
| ID | Requirement |
|----|-------------|
| REQ-020 | **If** database save fails, **then** the system shall display error toast "保存に失敗しました". |

### Boundary Conditions
| Condition | Value | EARS Requirement |
|-----------|-------|------------------|
| Minimum | 0ml | **When** calculated amount is 0, the system shall still record the entry. |
| Daily limit exceeded | >300mg | **While** over limit, the system shall show exceeded amount in text (e.g., "350mg / 300mg"). |

## Concrete Examples
### Example 1: Record Coffee
- **Trigger**: User taps "Coffee" → selects "250ml"
- **State**: Current caffeine: 100mg, Limit: 300mg
- **Result**: Toast "☕ +150mg recorded", Progress shows 250mg/300mg
- **Verification**: Check DB has new record, UI updated

## Acceptance Criteria
- [ ] REQ-001: Bottom sheet appears with 150/250/350ml options
- [ ] REQ-002: Caffeine calculated correctly and saved
- [ ] REQ-020: Error toast shown on save failure
- [ ] Unit tests cover all REQ-* requirements

## Not In Scope
- NOT implementing: Custom drink creation (Pro feature, separate ticket)
- NOT handling: Undo functionality (future enhancement)

## Dependencies
- Depends on: #XX - Drink types, #YY - Database schema
- Blocks: #ZZ - History screen
```

See [templates/issue-template.md](templates/issue-template.md) for complete templates.

## Dependency Analysis Process

### Step 1: Identify Foundation Tasks
Foundation tasks that others depend on:
- Database schema definitions
- Core type definitions
- Base component creation
- Configuration setup

### Step 2: Map Dependencies
```
[Foundation Tasks]
      ↓
[Layer 1 Tasks] ← Can parallel within layer
      ↓
[Layer 2 Tasks] ← Can parallel within layer
      ↓
[Integration Tasks]
```

### Step 3: Group by Parallel Streams

Example parallel streams:
```
Stream A (UI):     Stream B (Data):    Stream C (Logic):
[基盤] Schema ─────────────────────────────────────────
     ↓                  ↓                    ↓
[並列可] Home UI   [並列可] DB Repo    [並列可] Service
     ↓                  ↓                    ↓
[並列可] List UI   [並列可] Hooks      [並列可] Validation
     ↓                  ↓                    ↓
────────────────── Integration ──────────────────────
```

## Git Worktree Strategy

### When to Suggest Worktree
- Parallel tickets touching different areas
- Long-running features that shouldn't block
- Multiple developers on same project

### Worktree Naming Convention
```
../project-{feature-category}/
Examples:
  ../hydro-caffeine-ui-home/
  ../hydro-caffeine-db-schema/
  ../hydro-caffeine-settings/
```

### Worktree Setup Template
```bash
# Create worktree for parallel work
git worktree add ../project-feature-name feature/issue-XX-description

# After completion
git worktree remove ../project-feature-name
```

## Ticket Categories

### 1. Foundation Tickets 【基盤】
Must complete before parallel work begins:
- Schema definitions
- Type definitions
- Core utilities
- Theme/constants

### 2. Parallel UI Tickets 【並列可】
Can work simultaneously:
- Different screens
- Independent components
- Isolated features

### 3. Parallel Data Tickets 【並列可】
Can work simultaneously:
- Different repository functions
- Independent hooks
- Separate API endpoints

### 4. Integration Tickets 【依存あり】
Require prior tickets:
- Connecting UI to data
- Cross-feature functionality
- E2E testing

## GitHub Issue Creation

### Using gh CLI
```bash
# Create issue with all metadata
gh issue create \
  --title "【並列可】Home Screen - Progress bars component" \
  --body "$(cat issue-body.md)" \
  --label "enhancement,parallel"

# Create linked issues
gh issue create \
  --title "【依存あり】Home Screen - Integration with data layer" \
  --body "Depends on #1, #2" \
  --label "enhancement,blocked"
```

### Labels to Use
| Label | Purpose |
|-------|---------|
| `parallel` | Can work in parallel |
| `blocked` | Waiting on dependencies |
| `foundation` | Must complete first |
| `ui` | User interface work |
| `data` | Data layer work |
| `integration` | Connects multiple parts |

## Analysis Workflow

### Phase 1: Requirement Analysis
1. Read requirements document thoroughly
2. Identify major feature areas
3. List all discrete functionality

### Phase 2: Dependency Mapping
1. Draw dependency graph mentally
2. Identify foundation requirements
3. Group independent work streams

### Phase 3: Ticket Creation Order
1. Create foundation tickets first
2. Create parallel tickets with worktree suggestions
3. Create integration tickets last
4. Add cross-references

### Phase 4: Validation
- Each ticket is independently testable
- Dependencies are explicit
- Parallel work is maximized
- Worktree names are consistent

## Example Breakdown

From requirements like PROJECT_IDEA.md:

```
Phase 1: Foundation 【基盤】
├── #1 Database schema (Drizzle) - drink_logs, settings
├── #2 Type definitions - DrinkType, Settings, DrinkLog
└── #3 Theme constants - Colors, spacing

Phase 2: Parallel Streams
├── UI Stream (worktree: hydro-ui)
│   ├── #4【並列可/worktree:hydro-ui】Progress bar component
│   ├── #5【並列可/worktree:hydro-ui】Quick add buttons
│   └── #6【並列可/worktree:hydro-ui】Today's log list
│
├── Data Stream (worktree: hydro-data)
│   ├── #7【並列可/worktree:hydro-data】Drink log repository
│   ├── #8【並列可/worktree:hydro-data】Settings repository
│   └── #9【並列可/worktree:hydro-data】Zustand store setup
│
└── Logic Stream (worktree: hydro-logic)
    ├── #10【並列可/worktree:hydro-logic】Caffeine calculation
    ├── #11【並列可/worktree:hydro-logic】Cutoff time logic
    └── #12【並列可/worktree:hydro-logic】Daily reset logic

Phase 3: Integration【依存あり】
├── #13 Home screen integration (depends: #4-6, #7-9)
├── #14 Settings screen integration
└── #15 History screen integration

Phase 4: Polish
├── #16【並列可】Onboarding flow
├── #17【並列可】Error handling
└── #18【並列可】Accessibility
```

## AI Assistant Instructions

When this skill is activated:

**Goal**: "誰が実装しても要件は絶対に満たせる" (Anyone can implement and definitely satisfy requirements)

### Analysis Phase

1. **Read Requirements First**: Thoroughly analyze the requirements document (PROJECT_IDEA.md)
   - Extract ALL specific values (numbers, colors, sizes, text)
   - Note section references for traceability
   - Identify implicit requirements that need clarification

2. **Create Source Requirements Table**: For each ticket, extract exact specs
   ```
   | Section | Reference | Specification |
   |---------|-----------|---------------|
   | プログレスバー | 4.3 | 現在量 / 目標量（例: 1.2L / 2.0L） |
   | カフェイン上限 | 4.2 | デフォルト300mg |
   ```

3. **Extract Key Values**: All numbers from requirements
   ```
   | Item | Value | Unit | Source |
   |------|-------|------|--------|
   | 水分目標デフォルト | 2,000 | ml | 4.9 |
   | カフェイン上限デフォルト | 300 | mg | 4.9 |
   | コーヒーのカフェイン | 60 | mg/100ml | 4.2 |
   | サイズオプション | 150, 250, 350 | ml | 4.11 |
   ```

4. **Identify Domains & Dependencies**: Split into logical domains (UI, Data, Logic, etc.)

5. **Maximize Parallel Work**: Group independent tasks

### Ticket Creation Phase - EARS Format Required

1. **Write EARS Requirements**: Every ticket MUST have requirements in EARS format
   - Use **When** for user interactions (Event-driven)
   - Use **While** for state-dependent behavior (State-driven)
   - Use **If/then** for error handling (Unwanted behavior)
   - Use **Where** for Pro/optional features (Optional)
   - The [system] shall... for universal constraints (Ubiquitous)

2. **Assign Requirement IDs**:
   - REQ-001, REQ-002... for core requirements
   - REQ-010, REQ-011... for state requirements
   - REQ-020, REQ-021... for error handling
   - UI-001, UI-002... for UI requirements
   - A11Y-001... for accessibility

3. **Map Requirements to Acceptance Criteria**:
   - Each REQ-XXX must have corresponding acceptance criterion
   - Criteria must be testable: "REQ-001: [specific verifiable condition]"

4. **Include Concrete Examples** (CRITICAL - at least 4 per ticket):

   **Example Format**:
   ```
   ### Example 1: Happy Path - Record Coffee
   Trigger:    User taps "コーヒー" button, selects 250ml
   Pre-state:  Today's caffeine = 100mg, Limit = 300mg
   Calculation: 250ml × (60mg/100ml) = 150mg
   Post-state: Today's caffeine = 250mg
   UI Result:
     - Toast: "☕ +150mg recorded"
     - Progress bar: 250mg / 300mg (83%)
     - Today's log: New entry "コーヒー 250ml (150mg) - 10:30"
   Verification: Check DB has record with { type: 'coffee', amount_ml: 250, caffeine_mg: 150 }
   ```

   **Required Examples**:
   - Happy path: Normal successful flow with specific values
   - Boundary case: Edge values (0, max, 100% exceeded, empty list)
   - Error case: What happens when things fail
   - Edge case: First use, empty state, etc.

5. **Boundary Conditions Table** (MANDATORY):
   ```
   | Condition | Value | EARS Requirement | Example |
   |-----------|-------|------------------|---------|
   | Minimum | 0ml | **When** value is 0, the system shall display "0ml / 2,000ml". | 0 → "0ml / 2,000ml" |
   | Over 100% | >2000ml | **While** value > target, the system shall show bar at 100% and text as "2,500ml / 2,000ml". | 2500/2000 → bar 100%, text "2,500ml" |
   | Empty list | 0 records | **While** no records exist, the system shall show "💧 まだ記録がありません". | Empty → placeholder |
   ```

6. **UI Specifications Table**:
   ```
   | ID | Property | Value | Source |
   |----|----------|-------|--------|
   | UI-001 | Touch target | 44pt × 44pt minimum | HIG |
   | UI-002 | Water color | iOS Blue (#007AFF) | PROJECT_IDEA.md 9.2 |
   | UI-003 | Caffeine color | iOS Brown (#A2845E) | PROJECT_IDEA.md 9.2 |
   ```

7. **Not In Scope** (MANDATORY):
   - Explicitly state what this ticket does NOT include
   - Prevents scope creep
   - Reference other tickets for excluded items

8. **Verification Checklist**:
   - Step-by-step manual test procedure
   - Each step maps to a requirement

### Output Format

1. **Summary Table**: Show all tickets in a table first
2. **Dependency Graph**: Visual representation if complex
3. **Phase Breakdown**: Group by implementation phase
4. **Worktree Plan**: List suggested worktrees

### Quality Checks

**Requirements Quality**:
- [ ] Every ticket has EARS-formatted requirements with IDs
- [ ] Requirements include specific values from PROJECT_IDEA.md
- [ ] Source Requirements table references PROJECT_IDEA.md sections
- [ ] Key Values table lists ALL numbers from requirements

**Examples Quality**:
- [ ] At least 4 concrete examples per ticket
- [ ] Examples include specific values (250ml, 150mg, 16:00)
- [ ] Happy path, Boundary, Error, Edge cases covered
- [ ] Each example has: Trigger → Pre-state → Action → Post-state → UI Result → Verification

**Boundary Conditions**:
- [ ] Minimum value defined (0, empty, null)
- [ ] Maximum value defined (limit, overflow)
- [ ] 100% exceeded behavior defined
- [ ] Empty state behavior defined

**Acceptance Criteria**:
- [ ] Criteria reference requirement IDs (REQ-XXX)
- [ ] Each criterion is testable with specific values
- [ ] Boundary conditions have acceptance criteria

**Dependencies**:
- [ ] Dependencies are bidirectional (depends on / blocks)
- [ ] Parallel work is maximized
- [ ] Worktree names are descriptive and consistent

### Never

- Write vague requirements like "properly displays" without specific values
- Create tickets without Source Requirements table
- Skip the Key Values table
- Use placeholder values like "XX" or "[value]" - always use real values
- Write examples without specific numbers (250ml, not "some amount")
- Skip boundary condition definitions
- Omit the Not In Scope section
- Create acceptance criteria that don't map to requirements
- Assume dependencies without marking them
- Miss opportunities for parallel work
- Forget worktree suggestions for parallel work

### Example: Good vs Bad Ticket

**❌ BAD (vague, no one can implement confidently)**:
```markdown
## 概要
プログレスバーコンポーネント

## 受け入れ条件
- [ ] 進捗を表示する
- [ ] 100%超過時の処理
- [ ] アクセシビリティ対応
```

**✅ GOOD (anyone can implement exactly)**:
```markdown
## User Story
**As a** user
**I want** to see my daily water and caffeine progress at a glance
**So that** I can track my consumption goals

## Source Requirements

| Section | Reference | Specification |
|---------|-----------|---------------|
| プログレスバー | 4.3 | 現在量 / 目標量（例: 1.2L / 2.0L） |
| 100%超過 | 4.3 | バーは100%で停止、数値のみ超過表示（例: 2.5L / 2.0L ✓達成） |

## Functional Requirements (EARS Format)

| ID | Requirement | Verification |
|----|-------------|--------------|
| REQ-001 | The progress bar shall display current value and target as "X.X L / Y.Y L" format. | Text matches format |
| REQ-002 | **While** current ≥ target, the system shall display bar at 100% width. | Bar does not exceed container |
| REQ-003 | **While** current ≥ target, the system shall display text as "X.X L / Y.Y L ✓達成". | Checkmark visible |

## Boundary Conditions

| Condition | Value | EARS Requirement | Example |
|-----------|-------|------------------|---------|
| Zero | 0ml | **When** value is 0, the system shall display "0ml / 2,000ml" with 0% bar. | 0 → empty bar |
| 100% exactly | 2000ml | **When** value equals target, the system shall display bar at 100% and "2,000ml / 2,000ml ✓達成". | 2000/2000 → full bar + ✓ |
| Over 100% | 2500ml | **While** value > target, the system shall show bar at 100% (not overflow) and "2,500ml / 2,000ml ✓達成". | 2500/2000 → bar stays 100%, text shows 2,500 |

## Concrete Examples

### Example 1: Happy Path - 60% Progress
Trigger:    Component renders with currentValue=1200, targetValue=2000
Pre-state:  n/a (initial render)
UI Result:
  - Bar width: 60% of container
  - Text: "1.2 L / 2.0 L"
  - No checkmark
Verification: Visual inspection, snapshot test

### Example 2: Boundary - Exactly 100%
Trigger:    Component renders with currentValue=2000, targetValue=2000
UI Result:
  - Bar width: 100% of container
  - Text: "2.0 L / 2.0 L ✓達成"
  - Checkmark visible
Verification: Visual inspection, unit test

### Example 3: Over 100%
Trigger:    Component renders with currentValue=2500, targetValue=2000
UI Result:
  - Bar width: 100% (not 125%)
  - Text: "2.5 L / 2.0 L ✓達成"
Verification: Bar does not overflow, text shows exceeded value

### Example 4: Empty/Zero
Trigger:    Component renders with currentValue=0, targetValue=2000
UI Result:
  - Bar width: 0%
  - Text: "0 L / 2.0 L"
Verification: Bar is visible but empty

## Acceptance Criteria
- [ ] REQ-001: Format "X.X L / Y.Y L" displayed correctly
- [ ] REQ-002: Bar at 100% when current ≥ target
- [ ] REQ-003: "✓達成" shown when current ≥ target
- [ ] Boundary: 0% displays correctly (Example 4)
- [ ] Boundary: 100% displays correctly (Example 2)
- [ ] Boundary: >100% bar does not overflow (Example 3)
- [ ] A11Y: VoiceOver announces "60% complete, 1.2 liters of 2.0 liters"
```

## Templates

See [templates/](templates/) directory for:
- [issue-template.md](templates/issue-template.md) - Standard issue template
- [planning-checklist.md](templates/planning-checklist.md) - Pre-planning checklist

## Additional Resources

- [Reference Guide](reference.md) - Detailed patterns and examples
