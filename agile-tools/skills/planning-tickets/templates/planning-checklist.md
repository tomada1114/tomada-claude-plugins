# Planning Checklist

Use this checklist before creating tickets to ensure thorough planning.

## Pre-Planning Checklist

### 1. Requirements Understanding
- [ ] Read requirements document completely
- [ ] Identify all feature areas
- [ ] Note any ambiguities to clarify
- [ ] Understand success criteria

### 2. Domain Identification
- [ ] UI/Presentation layer features
- [ ] Data/Repository layer features
- [ ] Business logic features
- [ ] Infrastructure/Configuration
- [ ] External integrations

### 3. Foundation Requirements
- [ ] Database schema needs
- [ ] Type definitions needed
- [ ] Constants/configuration
- [ ] Shared utilities

## Dependency Analysis Checklist

### 4. Map Dependencies
- [ ] Draw dependency arrows between features
- [ ] Identify circular dependencies (eliminate them!)
- [ ] Find foundation items (no dependencies)
- [ ] Find leaf items (no dependents)

### 5. Parallel Stream Identification
- [ ] Group independent features into streams
- [ ] Name each stream (UI, Data, Logic, etc.)
- [ ] Assign worktree names to streams
- [ ] Verify streams don't conflict

### 6. Phase Planning
- [ ] Phase 1: Foundation (【基盤】)
- [ ] Phase 2: Parallel work (【並列可】)
- [ ] Phase 3: Integration (【依存あり】)
- [ ] Phase 4: Polish/Testing

## Ticket Quality Checklist

### 7. Each Ticket Should Have
- [ ] Clear, descriptive title with prefix
- [ ] 2-3 acceptance criteria minimum
- [ ] Estimated file count
- [ ] Dependencies listed (or "None")
- [ ] Worktree suggestion (if parallel)

### 8. Ticket Size Check
- [ ] Can complete in 1-3 hours? → Good size
- [ ] Would take 4+ hours? → Consider splitting
- [ ] Splitting creates dependencies? → Keep as one
- [ ] Too small and trivial? → Consider combining

### 9. Independence Verification
For each 【並列可】 ticket:
- [ ] Different files from other parallel tickets?
- [ ] No shared state modifications?
- [ ] Independent test cases?
- [ ] Can merge without conflicts?

## Worktree Planning Checklist

### 10. Worktree Strategy
- [ ] List all worktree names needed
- [ ] Naming follows convention: `project-feature-area`
- [ ] Each parallel stream has a worktree
- [ ] Document worktree setup commands

### 11. Branch Naming
- [ ] `feature/issue-XX-short-description`
- [ ] Consistent prefix per category
- [ ] Under 50 characters

## Final Validation

### 12. Review All Tickets
- [ ] Every ticket has explicit dependencies
- [ ] No orphan tickets (connected to the graph)
- [ ] Integration tickets exist for connections
- [ ] Foundation completes before parallel phase

### 13. Create Summary
- [ ] Table of all tickets with status columns
- [ ] Dependency graph (if complex)
- [ ] Phase breakdown list
- [ ] Worktree assignment list

## Quick Reference: Ticket Prefixes

| Prefix | Meaning | Color Label |
|--------|---------|-------------|
| 【基盤】 | Foundation | Purple #5319E7 |
| 【並列可】 | Parallel OK | Green #0E8A16 |
| 【並列可/worktree:xxx】 | Parallel + WT | Green #0E8A16 |
| 【依存あり】 | Has Dependencies | Red #B60205 |
| 【順次】 | Sequential | Yellow #FBCA04 |

## Common Mistakes to Avoid

1. **Creating too-small tickets** that all depend on each other
2. **Missing integration tickets** between parallel work
3. **Forgetting worktree suggestions** for parallel work
4. **Unclear acceptance criteria** that can't be tested
5. **Not marking dependencies** in both directions
6. **Assuming parallel** when files overlap

## Example Planning Flow

```
1. Read requirements (30 min)
         ↓
2. List all features (15 min)
         ↓
3. Draw dependency graph (30 min)
         ↓
4. Identify parallel streams (15 min)
         ↓
5. Create foundation tickets (15 min)
         ↓
6. Create parallel tickets (30 min)
         ↓
7. Create integration tickets (15 min)
         ↓
8. Review and validate (15 min)
         ↓
9. Create issues in GitHub (30 min)
```
