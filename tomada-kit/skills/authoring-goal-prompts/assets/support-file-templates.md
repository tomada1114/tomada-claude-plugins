# Support-file scaffolds

Clone-and-fill scaffolds for the bundle siblings. Create only the files the task earns (see
[../references/support-file-guide.md](../references/support-file-guide.md) for the when/why and
quality rules). Bracketed notes are guidance — delete them from the final files. Delete unused
sections; an empty heading is noise the executor must skip.

---

## design.md

```markdown
# Design: [one-line summary of the target state]

## Target interfaces
[The contract, as code. Signatures, schemas, config shapes — fenced and language-tagged.]

```ts
[interface / signature blocks]
```

## Decisions
### D1: [decision title]
- Decision: [what, concretely — names, storage, algorithm]
- Why: [one line]
- Rejected: [alternative] — [one-line reason, so the executor doesn't drift back to it]

[repeat D2, D3…]

## Data flow
[Only if >2 components interact. Small ASCII diagram:]
request → [keyExtract] → [bucket.take()] → 429 | next()

## Non-goals
[What this design deliberately does NOT cover — silence invites extrapolation.]
- [not building X]
```

---

## examples.md

````markdown
# Patterns to imitate

## Pattern: [name] (from [src/path/file.ts:LINES])
[Verbatim from the repo where possible; complete enough to adapt — imports, signature, error
handling. Annotate load-bearing lines.]

```ts
[code block — annotate with // ← comments on the lines that must not change]
```

## Before / After: [migration name]
[For migrations/refactors — the diff IS the instruction.]

```ts
// Before
[old call shape]

// After
[new call shape]
```

## Do NOT do this: [tempting wrong approach]
[Include only when a plausible wrong path exists.]

```ts
[wrong code]  // ✗ [one-line reason]
```
````

---

## research.md

```markdown
# Findings: [topic]

## Verified
[Facts you ran/read yourself. Evidence: file:line, pasted output, versions.]
- [finding] — evidence: `[file:line]` / output: `[pasted line]`
- Bug: [symptom]. Repro: `[exact command]` → `[observed output]`

## Inferred (not confirmed)
[Mark clearly — the executor should re-verify before relying on these.]
- [hypothesis] — based on [signal]

## Environment
- [tool/lib versions, auth state, anything preflight-checked at authoring time]
```

---

## checklist.yaml

```yaml
meta:
  ordering: strict            # strict = do items in order | any
  verify_all: "[full-suite command]"   # DONE WHEN needs this output too — statuses alone never suffice
  skip_rule: "after [M] distinct failed attempts set status: skip with a reason; max [K] skips total"
items:
  - id: T1
    task: "[one concrete unit of work]"
    acceptance: "[exact command AND expected result — pasted fresh before flipping status]"
    status: pending           # pending | done | skip
    notes: ""
```

---

## decisions.md

```markdown
# Pre-answered decisions

## Pre-answered questions
Q: [question the executor would ask if it could]
A: [the decision]. — [user answer YYYY-MM-DD | lead judgment], because [one line].

## Fallback rules
- If [predictable situation], then [action].
- If [environmental failure the session can't fix], then [salvage action + degraded sentinel — keep
  consistent with STOP RULES in goal.md].
```
