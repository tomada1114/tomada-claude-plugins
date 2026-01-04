# GitHub Issue Template

Use this template when creating tickets with `gh issue create`.

**Goal**: "誰が実装しても要件は絶対に満たせる" (Anyone can implement and definitely satisfy requirements)

## EARS (Easy Approach to Requirements Syntax) Reference

EARS provides unambiguous, testable requirement patterns:

| Pattern | Template | Use When |
|---------|----------|----------|
| **Ubiquitous** | The [system] shall [action] | Always true behavior |
| **Event-driven** | **When** [trigger], the [system] shall [action] | Response to event |
| **State-driven** | **While** [state], the [system] shall [action] | During a state |
| **Unwanted** | **If** [condition], **then** the [system] shall [action] | Error/exception handling |
| **Optional** | **Where** [feature], the [system] shall [action] | Configurable features |
| **Complex** | Combination of above | Multiple conditions |

---

## Standard Issue Template

```markdown
## User Story

**As a** [user type]
**I want** [goal/desire]
**So that** [benefit/value]

## Background & Context

### Source Requirements
<!-- Extract EXACT specifications from PROJECT_IDEA.md -->

| Section | Reference | Specification |
|---------|-----------|---------------|
| [Section name] | Section X.X | [Exact text from requirements] |

### Key Values from Requirements
<!-- List ALL specific values mentioned in requirements -->

| Item | Value | Unit | Source |
|------|-------|------|--------|
| [e.g., Daily water goal] | 2,000 | ml | PROJECT_IDEA.md 4.1 |
| [e.g., Caffeine per 100ml coffee] | 60 | mg | PROJECT_IDEA.md 4.2 |

## Functional Requirements (EARS Format)

### Core Requirements

| ID | Requirement | Verification |
|----|-------------|--------------|
| REQ-001 | **When** [specific trigger], the system shall [specific action]. | [How to test] |
| REQ-002 | **When** [trigger], the system shall [response]. | [How to test] |

### State-Dependent Requirements

| ID | Requirement | Verification |
|----|-------------|--------------|
| REQ-010 | **While** [state/condition], the system shall [behavior]. | [How to test] |
| REQ-011 | **While** [state], **when** [event], the system shall [action]. | [How to test] |

### Error Handling Requirements

| ID | Requirement | Verification |
|----|-------------|--------------|
| REQ-020 | **If** [error condition], **then** the system shall [recovery action]. | [How to test] |
| REQ-021 | **If** [invalid input], **then** the system shall [error feedback]. | [How to test] |

### Optional/Configurable Requirements

| ID | Requirement | Verification |
|----|-------------|--------------|
| REQ-030 | **Where** [feature is enabled], the system shall [behavior]. | [How to test] |

### Invariant Requirements

| ID | Requirement | Verification |
|----|-------------|--------------|
| REQ-040 | The [component] shall [always-true behavior]. | [How to test] |

## Boundary Conditions

<!-- MUST define behavior at ALL boundaries -->

| Condition | Value | EARS Requirement | Example |
|-----------|-------|------------------|---------|
| Minimum | [e.g., 0ml] | **When** value is 0, the system shall [behavior]. | 0ml → show "0ml / 2,000ml" |
| Maximum | [e.g., 9999ml] | **When** value reaches maximum, the system shall [behavior]. | 9999ml → clamp at 9999 |
| Empty state | [e.g., no records] | **While** no records exist, the system shall [display]. | Empty list → show placeholder |
| Over limit | [e.g., >100%] | **While** value exceeds 100%, the system shall [display]. | 2500ml/2000ml → "125% (達成!)" |
| Null/undefined | - | **If** value is null, the system shall [fallback]. | null → use default 0 |

## Concrete Examples

<!-- MUST include at least 3 examples with SPECIFIC values -->

### Example 1: Happy Path - [Scenario Name]
```
Trigger:    User taps "Coffee" button
Pre-state:  Today's caffeine = 100mg, Daily limit = 300mg
Action:     User selects "250ml"
Calculation: 250ml × (60mg/100ml) = 150mg
Post-state: Today's caffeine = 250mg
UI Result:
  - Toast: "☕ +150mg recorded"
  - Progress bar: 250mg / 300mg (83%)
  - Today's log: New entry "Coffee 250ml (150mg) - 10:30"
Verification: Check DB has record with { type: 'coffee', amount_ml: 250, caffeine_mg: 150 }
```

### Example 2: Boundary Case - [Scenario Name]
```
Trigger:    User taps "Coffee" button
Pre-state:  Today's caffeine = 280mg, Daily limit = 300mg
Action:     User selects "250ml" (+150mg = 430mg total)
Post-state: Today's caffeine = 430mg (over limit)
UI Result:
  - Progress bar: Shows 100% filled (bar stops at 100%)
  - Text shows: "430mg / 300mg"
  - Color: Warning/exceeded color (not error)
Verification: Bar visually at 100%, text shows exceeded value
```

### Example 3: Error Case - [Scenario Name]
```
Trigger:    Database save fails (simulated)
Pre-state:  User has selected drink and size
Error:      SQLite write error
UI Result:
  - Toast (error style): "保存に失敗しました。もう一度お試しください"
  - Toast auto-dismisses after 3 seconds
  - No data added to today's log
Recovery:   User can retry by selecting drink again
```

### Example 4: Edge Case - Empty State
```
Trigger:    App launch on new day / first time
Pre-state:  No drink records for today
UI Result:
  - Progress bars: 0ml / 2,000ml (0%), 0mg / 300mg (0%)
  - Today's log: Empty state with icon + text "💧 まだ記録がありません"
  - Quick Add buttons: All enabled and ready
```

## UI/UX Requirements

### Visual Specifications (Ubiquitous)

| ID | Property | Value | Source |
|----|----------|-------|--------|
| UI-001 | Touch target | Minimum 44pt × 44pt | HIG, PROJECT_IDEA.md 4.14 |
| UI-002 | Primary color | iOS Blue (#007AFF) for water | PROJECT_IDEA.md 9.2 |
| UI-003 | Secondary color | iOS Brown (#A2845E) for caffeine | PROJECT_IDEA.md 9.2 |
| UI-004 | Border radius | Use `BorderRadius.md` (8pt) | Theme constants |
| UI-005 | Spacing | Use `Spacing.md` (16pt) | Theme constants |

### Layout Specifications

<!-- Include ASCII diagram if helpful -->
```
┌─────────────────────────────────────────┐
│  [Component layout with measurements]   │
│                                         │
│  ├── 16pt padding                       │
│  ├── Element height: 44pt minimum       │
│  └── Gap between items: 8pt             │
└─────────────────────────────────────────┘
```

### Interaction Requirements (Event-driven)

| ID | Requirement |
|----|-------------|
| UI-010 | **When** user taps [element], the system shall [response with duration]. |
| UI-011 | **When** user swipes left on [item], the system shall reveal delete button (iOS standard). |
| UI-012 | **When** user long-presses [element], the system shall [haptic feedback + action]. |

### Animation Requirements

| ID | Animation | Duration | Easing |
|----|-----------|----------|--------|
| ANIM-001 | Bottom sheet appear | iOS Spring | System default |
| ANIM-002 | Toast appear | 200ms | ease-in |
| ANIM-003 | Toast dismiss | 150ms | ease-out |

### Accessibility Requirements

| ID | Requirement |
|----|-------------|
| A11Y-001 | The component shall have accessibilityLabel "[specific descriptive text]". |
| A11Y-002 | The component shall have accessibilityRole "[button/text/header/etc]". |
| A11Y-003 | The progress bar shall announce "[current]% complete, [value] of [total]" to VoiceOver. |
| A11Y-004 | **When** state changes, the system shall announce "[change description]" via accessibilityLiveRegion. |

## Data Specifications

### Input/Output Types

```typescript
// Expected input
interface ComponentInput {
  currentValue: number;  // Current amount (0-9999)
  targetValue: number;   // Target/limit (1-9999)
  unit: 'ml' | 'mg';     // Display unit
}

// Expected output/callback
interface ComponentOutput {
  onValueChange?: (value: number) => void;
  onComplete?: () => void;
}
```

### Validation Rules

| Field | Rule | Error Message |
|-------|------|---------------|
| currentValue | >= 0 | "値は0以上である必要があります" |
| targetValue | >= 1 | "目標値は1以上である必要があります" |

## Acceptance Criteria

<!-- MUST map to EARS requirements -->

- [ ] REQ-001: [Restate as specific testable condition with values]
- [ ] REQ-002: [Restate as specific testable condition with values]
- [ ] REQ-010: [State-dependent behavior verified]
- [ ] REQ-020: Error handling works as specified
- [ ] UI-001: All touch targets ≥ 44pt (measured)
- [ ] A11Y-001: VoiceOver announces correctly
- [ ] Boundary: Empty state displays correctly
- [ ] Boundary: Over-limit state displays correctly
- [ ] Unit tests cover all REQ-* requirements
- [ ] TypeScript compiles without errors
- [ ] `pnpm check` passes

## Not In Scope

<!-- MUST explicitly state what is excluded -->

- NOT implementing: [feature that might be assumed but is excluded]
  - Reason: [why excluded - separate ticket, future enhancement, etc.]
- NOT handling: [edge case] → Will be addressed in #XX
- NOT integrating with: [related system] → Has its own ticket #YY
- NOT supporting: [platform/feature] → Out of MVP scope per PROJECT_IDEA.md

## Technical Notes (Optional)

### Suggested Files
- `path/to/file.ts` - [Brief reason]

### Reference Implementation
- Similar to [existing code] in [file path]

### Dependencies (npm packages)
- No new dependencies required
<!-- OR -->
- May need: `package-name` for [reason]

## Dependencies

### Depends On
- None
<!-- OR -->
- #XX - [What we need: types/components/etc]
- #YY - [Specific exports: `DrinkType`, `saveDrinkLog()`]

### Blocks
- #ZZ - [What depends on this ticket completing]

### Can Parallel With
- #AA, #BB, #CC - [Brief reason why no conflicts]

## Worktree Strategy (if parallel)

```bash
git worktree add ../project-feature-name feature/issue-XX-description
```

## Verification Checklist

<!-- Step-by-step manual test procedure -->

### Manual Testing
1. [ ] Start app in development mode
2. [ ] Navigate to [screen/component]
3. [ ] Test REQ-001: [action] → [expected result]
4. [ ] Test REQ-020: Simulate [error] → [expected handling]
5. [ ] Test boundary: [empty state] → [expected display]
6. [ ] Test boundary: [over limit] → [expected display]
7. [ ] Test A11Y: Enable VoiceOver → [expected announcement]

### Automated Testing
- [ ] Unit tests added for all REQ-* requirements
- [ ] Edge cases covered in tests
- [ ] `pnpm test` passes

## PR Instructions

Include `close #XX` in PR description to auto-close this issue.
```

---

## Foundation Issue Template (【基盤】)

For foundation/infrastructure tickets:

```markdown
## User Story

**As a** developer
**I want** [infrastructure/foundation]
**So that** other features can be built on top with consistent types and structure

## Background & Context

This is a foundation ticket that other tickets depend on.

### Source Requirements
<!-- Extract specifications from PROJECT_IDEA.md -->

| Section | Reference | Specification |
|---------|-----------|---------------|
| [Feature] | Section X.X | [Exact values and rules] |

## Functional Requirements (EARS Format)

### Type Definition Requirements

| ID | Requirement | Type/Interface |
|----|-------------|----------------|
| TYPE-001 | The system shall define `DrinkType` as union of: 'water' \| 'coffee' \| 'tea' \| 'green_tea' \| 'juice' \| 'milk'. | `type DrinkType = 'water' \| ...` |
| TYPE-002 | The system shall export all types from barrel file `index.ts`. | Export statement in index.ts |
| TYPE-003 | Each type shall have JSDoc documentation describing its purpose. | JSDoc comments |

### Type Specifications

| Type Name | Purpose | Fields | Constraints |
|-----------|---------|--------|-------------|
| `DrinkType` | Drink category | Union literal | 6 types as per PROJECT_IDEA.md 4.1 |
| `DrinkLog` | Single drink record | id, type, amount_ml, caffeine_mg, created_at | amount_ml >= 0, caffeine_mg >= 0 |
| `Settings` | User preferences | water_goal_ml, caffeine_limit_mg, bedtime, unit | All required, with defaults |

### Constant Specifications

| Constant | Value | Unit | Purpose | Source |
|----------|-------|------|---------|--------|
| `CAFFEINE_PER_100ML.coffee` | 60 | mg | Caffeine calculation | PROJECT_IDEA.md 4.2 |
| `CAFFEINE_PER_100ML.tea` | 30 | mg | Caffeine calculation | PROJECT_IDEA.md 4.2 |
| `CAFFEINE_PER_100ML.green_tea` | 20 | mg | Caffeine calculation | PROJECT_IDEA.md 4.2 |
| `DEFAULT_WATER_GOAL` | 2000 | ml | Initial setting | PROJECT_IDEA.md 4.9 |
| `DEFAULT_CAFFEINE_LIMIT` | 300 | mg | Initial setting | PROJECT_IDEA.md 4.9 |
| `DEFAULT_BEDTIME` | "22:00" | HH:mm | Initial setting | PROJECT_IDEA.md 4.9 |
| `CUTOFF_HOURS` | 6 | hours | Before bedtime | PROJECT_IDEA.md 4.4 |
| `SIZE_OPTIONS` | [150, 250, 350] | ml | Drink size presets | PROJECT_IDEA.md 4.11 |

### Schema Requirements (if database)

| ID | Requirement |
|----|-------------|
| SCHEMA-001 | The `drink_logs` table shall have columns: id (INTEGER PRIMARY KEY), drink_type (TEXT NOT NULL), amount_ml (INTEGER NOT NULL), caffeine_mg (INTEGER NOT NULL), created_at (INTEGER NOT NULL). |
| SCHEMA-002 | The `settings` table shall have columns: id (INTEGER PRIMARY KEY), water_goal_ml (INTEGER DEFAULT 2000), caffeine_limit_mg (INTEGER DEFAULT 300), bedtime (TEXT DEFAULT '22:00'), unit (TEXT DEFAULT 'ml'). |

## Concrete Examples

### Type Usage Example
```typescript
import { DrinkType, DrinkLog, CAFFEINE_PER_100ML, SIZE_OPTIONS } from '@/features/drinks/core/types';

// Valid DrinkType
const drinkType: DrinkType = 'coffee';  // OK
const invalid: DrinkType = 'soda';      // TS Error

// Calculate caffeine
const amountMl = 250;
const caffeineMg = (amountMl / 100) * CAFFEINE_PER_100ML.coffee; // 150mg

// Create DrinkLog
const log: DrinkLog = {
  id: 1,
  drinkType: 'coffee',
  amountMl: 250,
  caffeineMg: 150,
  createdAt: new Date(),
};

// Size options
SIZE_OPTIONS.forEach(size => console.log(`${size}ml`)); // 150ml, 250ml, 350ml
```

### Constant Usage Example
```typescript
import { DEFAULT_WATER_GOAL, DEFAULT_CAFFEINE_LIMIT, CUTOFF_HOURS } from '@/constants/drinks';

// Calculate cutoff time
const bedtime = new Date('2024-01-01T22:00:00');
const cutoffTime = new Date(bedtime.getTime() - CUTOFF_HOURS * 60 * 60 * 1000);
// Result: 16:00
```

## Acceptance Criteria

- [ ] TYPE-001: All 6 drink types defined and exported
- [ ] TYPE-002: All types importable via `import { X } from '@/path'`
- [ ] TYPE-003: All types have JSDoc documentation
- [ ] CONST-*: All constants match PROJECT_IDEA.md values exactly
- [ ] SCHEMA-001: Schema generates migration successfully
- [ ] TypeScript compiles without errors
- [ ] Unit tests verify constant values

## Not In Scope

- NOT implementing: Business logic using these types (separate tickets)
- NOT implementing: UI components
- NOT implementing: Repository/service functions
- NOT implementing: Custom drink type (Pro feature)

## Dependencies

### Depends On
- None (this is a foundation ticket)

### Blocks
- #XX - [Feature that needs these types]
- #YY - [Feature that needs these constants]
```

---

## Integration Issue Template (【依存あり】)

For integration tickets:

```markdown
## User Story

**As a** user
**I want** [integrated feature working end-to-end]
**So that** [user value/benefit]

## Background & Context

This ticket connects previously independent work:
- [Component A] from #XX - [what it provides]
- [Component B] from #YY - [what it provides]

### Integration Flow
```
User Action → [Component A] → [Transform] → [Component B] → UI Update
```

## Functional Requirements (EARS Format)

### Integration Flow Requirements

| ID | Requirement | Verification |
|----|-------------|--------------|
| INT-001 | **When** user taps Quick Add "Coffee", the system shall open Size Selection Sheet. | Sheet appears |
| INT-002 | **When** user selects 250ml in Sheet, the system shall call `saveDrinkLog({ type: 'coffee', amountMl: 250, caffeineMg: 150 })`. | DB record created |
| INT-003 | **When** save succeeds, the system shall update Progress Bar to show new total. | Bar updates immediately |
| INT-004 | **When** save succeeds, the system shall show Toast "☕ +150mg recorded". | Toast visible 2-3s |

### Data Flow Requirements

| ID | Source | Destination | Data | Transformation |
|----|--------|-------------|------|----------------|
| DATA-001 | Size Sheet | Drink Log Store | `{ drinkType, amountMl }` | Calculate caffeineMg |
| DATA-002 | Drink Log Store | Progress Bar | `{ totalWaterMl, totalCaffeineMg }` | Sum today's logs |
| DATA-003 | Settings Store | Cutoff Display | `{ bedtime }` | Subtract 6 hours |

### Loading & Error Requirements

| ID | Requirement |
|----|-------------|
| LOAD-001 | **While** saving to database, the system shall disable Quick Add buttons (prevent double-tap). |
| ERR-001 | **If** database save fails, **then** the system shall show error Toast and re-enable buttons. |

## Concrete Examples

### Example 1: Complete Flow - Record Coffee
```
Step 1: User sees Home Screen
  - Water: 500ml / 2,000ml (25%)
  - Caffeine: 0mg / 300mg (0%)
  - Cutoff: "カフェインは16:00まで" (bedtime 22:00)

Step 2: User taps "コーヒー" button
  - Size Sheet slides up from bottom
  - Options: 150ml, 250ml, 350ml, キャンセル

Step 3: User taps "250ml"
  - Sheet dismisses
  - Quick Add buttons briefly disabled
  - DB write: { type: 'coffee', amount_ml: 250, caffeine_mg: 150 }

Step 4: Success
  - Toast appears: "☕ +150mg recorded"
  - Water unchanged: 500ml / 2,000ml
  - Caffeine updated: 150mg / 300mg (50%)
  - Today's log shows: "コーヒー 250ml (150mg) - 10:30"
  - Quick Add buttons re-enabled

Verification:
  - Check database has new record
  - Check Zustand store updated
  - Check UI reflects changes
```

### Example 2: Cutoff Warning Flow
```
Pre-condition: Current time 16:30, Cutoff time 16:00

Step 1: User taps "コーヒー" button
Step 2: User selects "250ml"
Step 3: System shows Alert
  - Title: nil
  - Message: "就寝に影響する可能性があります"
  - Buttons: "記録する", "キャンセル"

Step 3a: User taps "記録する"
  - Record saved normally
  - Toast shown

Step 3b: User taps "キャンセル"
  - No record saved
  - Return to Home Screen
```

### Example 3: Error Recovery
```
Step 1: User selects drink and size
Step 2: DB save fails (simulated error)
Step 3: Error Toast shown: "保存に失敗しました"
Step 4: Quick Add buttons re-enabled
Step 5: User can retry immediately
```

## Acceptance Criteria

- [ ] INT-001: Tapping Quick Add opens Size Sheet
- [ ] INT-002: Selecting size saves to database with correct caffeine calculation
- [ ] INT-003: Progress bars update immediately after save
- [ ] INT-004: Toast shows with drink emoji and amount
- [ ] LOAD-001: Buttons disabled during save
- [ ] ERR-001: Error toast shown on failure, buttons re-enabled
- [ ] Cutoff warning shows after cutoff time
- [ ] Manual end-to-end test passes all steps
- [ ] No TypeScript errors

## Pre-requisites Checklist

Before starting this ticket:
- [ ] #XX (Size Sheet) is merged to main
- [ ] #YY (Drink Log Repository) is merged to main
- [ ] #ZZ (Zustand Store) is merged to main
- [ ] `git pull origin main` completed

## Not In Scope

- NOT modifying: Internal logic of connected components (unless bug fix)
- NOT adding: New features beyond connecting existing work
- NOT implementing: Custom drinks (Pro feature, separate ticket)

## Dependencies

### Depends On (MUST be merged)
- #XX - Size Sheet component (`<SizeSheet />`)
- #YY - Drink Log Repository (`saveDrinkLog()`, `getTodayLogs()`)
- #ZZ - Zustand Store (`useDrinkLogStore`)

### Blocks
- #AA - History screen integration

## Verification Checklist

### Manual Testing
1. [ ] Fresh app start → Progress bars at 0
2. [ ] Tap "水" → Size Sheet → Select 250ml → Toast "💧 +250ml recorded"
3. [ ] Verify water progress: 250ml / 2,000ml
4. [ ] Tap "コーヒー" → Size Sheet → Select 350ml → Toast "☕ +210mg recorded"
5. [ ] Verify caffeine progress: 210mg / 300mg
6. [ ] Verify today's log shows 2 entries in correct order
7. [ ] After cutoff time: Tap caffeine drink → Warning alert appears
8. [ ] Simulate DB error → Error toast appears, can retry
```

---

## CLI Command Examples

### Create Issue with Full Template
```bash
gh issue create \
  --title "【並列可】Home Screen - Progress bars component" \
  --body-file issue-body.md \
  --label "enhancement,parallel,ui-component"
```

### Create Foundation Issue
```bash
gh issue create \
  --title "【基盤】Type definitions - Drink tracking domain types" \
  --body-file issue-body.md \
  --label "foundation,types"
```

### Create Integration Issue
```bash
gh issue create \
  --title "【依存あり】Home Screen - Connect UI to data layer" \
  --body-file issue-body.md \
  --label "integration,has-dependency"
```

## Required Labels

```bash
# Create these labels in your repo
gh label create "parallel" --color "0E8A16" --description "Can work in parallel"
gh label create "foundation" --color "5319E7" --description "Must complete first"
gh label create "has-dependency" --color "B60205" --description "Waiting on dependencies"
gh label create "integration" --color "FBCA04" --description "Connects components"
```
