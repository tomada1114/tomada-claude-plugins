# Support-file guide — packaging the lead engineer's head for the executor

The goal session is a fresh, often **weaker/cheaper model** (e.g. Sonnet executing what an Opus
session designed) with **zero shared context**: it has not seen your discovery, the user's answers,
or your design reasoning. Support files are how the lead's intent survives the handoff. This guide
covers when to create each file and how to write it so the executor never has to guess.

## Contents

- [The handoff principle](#the-handoff-principle)
- [The standard menu](#the-standard-menu)
- [design.md — decisions and their reasons](#designmd--decisions-and-their-reasons)
- [examples.md — show, don't point](#examplesmd--show-dont-point)
- [research.md — distilled findings with evidence](#researchmd--distilled-findings-with-evidence)
- [checklist.yaml — a machine-checkable work queue](#checklistyaml--a-machine-checkable-work-queue)
- [decisions.md — pre-answered questions and fallbacks](#decisionsmd--pre-answered-questions-and-fallbacks)
- [Wiring the bundle into goal.md](#wiring-the-bundle-into-goalmd)
- [Anti-patterns](#anti-patterns)
- [Worked example: a design-heavy bundle](#worked-example-a-design-heavy-bundle)

## The handoff principle

Two rules generate everything else:

1. **Whatever you don't write down is lost.** Discovery findings, design choices, and pattern
   knowledge live only in the authoring conversation — the executor cannot see it. If re-deriving
   something could plausibly go a different way, write it down.
2. **Show, don't tell.** "Follow the existing pagination pattern" makes the executor find, read,
   and interpret the pattern — three chances to diverge. A pasted code block with the load-bearing
   lines annotated leaves one way to comply. Concrete artifacts (code blocks, exact commands,
   filled examples) beat descriptions every time.

Calibrate to **decision density, not page count**: a support file earns each line by preventing a
wrong decision. Ten lines that pin an interface beat three pages of narrative.

## The standard menu

`goal.md` always exists in a bundle: it carries the contract (GOAL / DONE WHEN / VERIFY /
CONSTRAINTS / STOP RULES) and *points* to the siblings; the siblings carry the knowledge. Create
only the siblings that earn their place:

| File | Carries | Create when |
|---|---|---|
| `design.md` | target design: interfaces/schemas as code blocks, decisions + rationale + rejected alternatives | you made any design choice the executor could plausibly make differently |
| `examples.md` | patterns to imitate as fenced code blocks — verbatim repo snippets, Before/After pairs | "follow the style of X" is not enough; you want to show, not point |
| `research.md` | distilled findings: current behavior, root causes, repro commands, verified-vs-inferred | you learned non-obvious facts the executor would burn turns rediscovering |
| `checklist.yaml` (`.md` for short queues) | the work queue, one acceptance criterion per item, machine-checkable statuses | multi-item work — migrations, audits, content production, coding or not |
| `decisions.md` | pre-answered questions + fallback rules ("if X, do Y") | any run long enough to hit an ambiguity you can predict |

Merge rather than pad: if design + research together are ~30 lines, one `design.md` with a
"Findings" section is fine. Split when a file stops being skimmable. The menu is canonical, not a
straitjacket — a migration inventory may live as `checklist.yaml` items or a dedicated
`inventory.md` used as the queue; keep the *roles* (and their quality rules), adapt the names.

Scaffolds for every file: [../assets/support-file-templates.md](../assets/support-file-templates.md)
(clone and fill; delete unused sections).

## design.md — decisions and their reasons

The executor should implement your design, not invent one. Requirements:

- **Lead with the target state as code.** Interfaces, function signatures, schemas, config shapes —
  as fenced code blocks. These are the contract; prose around them is commentary.
- **Record decisions with rationale AND the rejected alternative.** One line each. Naming the
  rejected road stops the executor from "improving" its way back onto it mid-run.
- **Show data flow** with a small ASCII diagram when more than two components interact.
- **State what the design deliberately does NOT cover** — the executor treats silence as an
  invitation to extrapolate.

Decision entry shape:

```markdown
### D1: Token bucket, not sliding window
- Decision: rate limiting uses a token-bucket per API key, stored in Redis (`INCR` + `EXPIRE`).
- Why: matches the existing quota code in `src/middleware/quota.ts`; O(1) per request.
- Rejected: sliding-window log — precise but O(n) memory per key; overkill at our traffic.
```

## examples.md — show, don't point

- **Every pattern is a fenced, language-tagged code block**, complete enough to adapt (imports,
  signature, error handling included). Never elide with `...` where the elision hides the point.
- **Prefer verbatim code from the repo, with its source path** ("from `src/api/orders.ts:31-58`").
  Real code is proof the pattern compiles and matches house style; invented examples drift.
- **Migrations/refactors get Before/After pairs** — the diff *is* the instruction.
- **Annotate load-bearing lines** with short comments ("← keep this ordering: hook must register
  before the router mounts").
- **Include a labeled wrong-way block** when a tempting-but-wrong approach exists:

````markdown
### Pattern: paginated list endpoint (from src/api/orders.ts:31-58)

```ts
export async function listOrders(req: Request): Promise<Page<Order>> {
  const cursor = decodeCursor(req.query.cursor);      // ← always cursor, never offset
  const page = await repo.orders.list({ cursor, limit: clamp(req.query.limit, 1, 100) });
  return { items: page.rows, nextCursor: encodeCursor(page.last) };
}
```

### Do NOT do this (offset pagination — breaks under concurrent writes)

```ts
const page = await repo.orders.list({ offset: req.query.page * 20 });  // ✗
```
````

## research.md — distilled findings with evidence

- **Facts with evidence**, not narrative: `file:line` references, pasted command output, version
  numbers. The executor should be able to spot-check any claim.
- **Mark verified vs inferred.** "Verified: `npm test` fails with `TypeError: …` (ran 2026-07-02)"
  vs "Inferred: likely caused by the v4 upgrade — not confirmed."
- **Bugs get a repro command**, so the executor confirms the fix against the same signal instead
  of re-litigating whether the bug is real.
- **Distill, never dump.** Raw exploration transcripts bury the one load-bearing fact under noise.

## checklist.yaml — a machine-checkable work queue

YAML beats prose checklists for anything beyond a handful of items: statuses are grep-countable
(`grep -c 'status: done'`), updates are clean diffs, and the whole-run rules live in one header
instead of being repeated per item.

```yaml
meta:
  ordering: strict            # strict = do items in order | any
  verify_all: "npm test && npm run lint"   # final whole-run check; boxes alone never satisfy DONE WHEN
  skip_rule: "after 3 distinct failed attempts set status: skip with a reason; max 2 skips total"
items:
  - id: T1
    task: "Migrate src/api/users.ts to getUserV2"
    acceptance: "npm run build exits 0 AND `rg getUserV1 src/api/users.ts` is empty"
    status: pending           # pending | done | skip
    notes: ""
```

Rules (these mirror the checklist section of
[goal-authoring-guide.md](goal-authoring-guide.md) — same anti-cheat logic):

- **One acceptance criterion per item** — the exact command and expected result. The session must
  paste that command's fresh output *before* flipping `status: done`.
- **`meta.verify_all` is mandatory**: `DONE WHEN` = all items done-or-skip AND the whole-run check's
  fresh output — statuses alone are self-graded.
- **Non-coding tasks use the same shape**, with measurable acceptance: `"wc -m of draft.md is
  3000–4000 and every H2 from meta.outline appears"` — never "the section reads well".
- A short queue (≤ ~8 items, no ordering/skip subtleties) may stay a Markdown checklist; the same
  per-item-acceptance and verify-all rules apply.

## decisions.md — pre-answered questions and fallbacks

Everything the executor *would* ask if it could. Two sections:

```markdown
## Pre-answered questions
Q: New endpoints — REST or extend the existing GraphQL schema?
A: REST under /api/v2/. Decided by user (2026-07-02). GraphQL layer is being deprecated.

Q: Where do rate-limit configs live?
A: config/limits.yaml, one entry per route group — lead judgment, mirrors config/quota.yaml.

## Fallback rules
- If a test is genuinely obsolete, leave it failing? No — mark it in the checklist notes and skip
  the item; never delete or xfail (CONSTRAINTS applies).
- If Redis is unreachable in the dev env, use the in-memory fallback already in
  src/lib/cache.ts — do not add a new abstraction.
```

Tag each answer with its source — *user answer* vs *lead judgment* — so a human reviewing the run
knows which decisions were delegated.

## Wiring the bundle into goal.md

Point, never duplicate — a fact living in two files will contradict itself after one edit.

In `CONTEXT`, list every sibling by **absolute path** with a read-first order:

```
CONTEXT: Before any work, read in order:
  1. ${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/goal-prompts/<slug>/design.md    — the target design; implement it, don't redesign
  2. ${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/goal-prompts/<slug>/examples.md  — patterns to imitate verbatim
  3. ${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/goal-prompts/<slug>/checklist.yaml — work queue; update statuses as you go
  decisions.md (same dir) pre-answers ambiguities — consult it before assuming.
```

In `CONSTRAINTS`, add the **divergence rule** (support files were written at authoring time; the
repo may have moved):

> If the repo contradicts a *fact* in a support file, trust the repo and note the divergence in the
> final report. If a *design* element turns out impossible as specified, apply the fallback in
> decisions.md; if none applies, stop and report per STOP RULES — never silently improvise a new design.

## Anti-patterns

| Anti-pattern | Why it fails | Instead |
|---|---|---|
| Prose description of code ("use a factory that…") | executor reinvents it differently | paste the code block |
| Raw research/transcript dump | the load-bearing fact drowns | distilled findings with evidence |
| Same fact in goal.md and a sibling | drift → contradiction mid-run | goal.md points; the sibling carries |
| Checklist items without acceptance criteria | ticks become self-graded | command + expected result per item |
| "See existing code for patterns" | find → read → interpret = three divergence points | verbatim snippet + source path in examples.md |
| Support files never referenced from goal.md | they are never read | CONTEXT read-first list, absolute paths |
| Design deferred to the executor ("choose a sensible approach") | a weaker model designs under anti-thrash pressure | decide now; record decision + rationale in design.md |

## Worked example: a design-heavy bundle

Task: "add per-key rate limiting to the public API" — designed by the authoring session, executed
unattended. Bundle at
`${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/goal-prompts/api-rate-limiting/`:

- `goal.md` (~30 lines) — GOAL: middleware live on all /api/v2 routes, tests pass; DONE WHEN tied
  to `GOAL_DONE:` sentinel after `npm test` output; CONTEXT: read-first list above; CONSTRAINTS:
  scope + anti-cheat + divergence rule; STOP RULES: 40-turn ceiling, degraded terminal for PR push.
- `design.md` — token-bucket decision D1 (above), the middleware signature as a `ts` block, ASCII
  flow `request → keyExtract → bucket.take() → 429|next`, non-goals ("no per-user limits, no
  admin UI").
- `examples.md` — verbatim middleware pattern from `src/middleware/quota.ts` with annotations,
  wrong-way block (per-route in-memory counters).
- `checklist.yaml` — 6 items (middleware, config loader, wiring, tests, docs, whole-run verify),
  each with an acceptance command.
- `decisions.md` — 3 pre-answered questions, 2 fallback rules.

The executor never designs, never hunts for patterns, and never guesses at ambiguities — it reads,
implements, verifies, and updates statuses. That is the whole point of the handoff.
