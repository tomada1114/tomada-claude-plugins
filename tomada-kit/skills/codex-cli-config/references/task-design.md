<!-- platform-annex -->

# Task Design for Codex CLI

## 1. Validation is Key

Autonomy is bounded by how verifiable "done" is, not by how much filesystem
or network access the agent is granted. A widely-permissioned agent with a
vague done-condition still stops and waits, or declares success prematurely,
because it has no way to check its own work. A narrowly-permissioned agent
whose done-condition resolves to a command's exit code can run a full
write-test-fix loop unattended.

`sandbox_mode` and `approval_policy` decide what Codex is *allowed* to touch;
task design decides how far it can go *without asking*. Writing a task so its
completion is verifiable — ideally by a command Codex can run itself — is
what actually produces autonomous, self-correcting runs. Generous
permissions paired with a fuzzy goal ("make it better") do not make a run
more autonomous; they just make it fail faster and with less traceability.

## 2. Task granularity and splitting

Task size maps onto PR size: too large hurts review and rollback, too small
hurts visibility into what was accomplished.

| Size | Example | Approach |
|---|---|---|
| Small | single-file fix, small addition | hand it over as one task |
| Medium | multi-file change, new feature with tests | confirm a plan first (Plan mode, §5) |
| Large | module design, architecture change, cross-module rework | split into staged tasks |

Two costs push toward splitting a large task rather than running it as one shot:

- **Debugging cost on failure.** Bundle five changes into one run and a
  broken result means reading a multi-file diff to find which change broke
  it. Run them as five sequential tasks and the failure is isolated
  automatically — "everything up to task N was fine, task N failed."
- **Context consumption.** Long sessions accumulate history, file reads, and
  tool output in the same context window (`/compact` summarizes but loses
  detail). Smaller tasks consume less context each, so a session handles
  more of them before a summary or a fresh session is needed.

**The splitting rule**: one task = one clear verification, and the
done-condition should fit on one line. "Implement user authentication"
expands into several lines of done-condition (login returns 200, register
succeeds, logout invalidates the token, unit + integration tests both pass) —
that's the signal it should split, e.g.:

- Task 1: User model + migration — done when the migration runs and the
  schema matches.
- Task 2: `/auth/register` endpoint — done when its integration test passes.
- Task 3: `/auth/login` endpoint — done when its integration test passes and a
  token is issued.
- Task 4: protected-route middleware — done when unauthenticated requests get
  401 and authenticated ones get 200.

Splitting too finely has its own cost: re-explaining context, waiting on, and
reviewing each task scales with task count. **Merge when the same
verification covers the change** — don't split just to split. Split when you
need to isolate a failure, need a separate review unit, or a policy decision
falls mid-task. Hold both rules together — one task one verification, and
merge changes that share a verification — that balance is the target.

Plan mode (§5) is a useful check on this call: if the plan it returns has many
disparate steps, that's a signal to split further.

## 3. The Mini Codex template

Four elements, always in this order, gathered up front: **Goal**, **Context
Pointers**, **Constraints**, **Done When**. Missing any one of them means
Codex fills the gap with a guess — a plausible-looking library, a naming
convention pulled from general training data, code landing in `utils/`
instead of the `auth/` directory it belongs in. That's not the agent cutting
corners; it's resolving an unspecified point the only way it can.

**Applicability threshold**: skip it for typo fixes and trivial renames —
filling out four elements for a one-line change slows you down. Use it for
tasks over ~30 minutes, spanning multiple files, or touching unfamiliar code.

### Goal

What the agent should achieve, stated through the destination — include the
verb, not just the noun. "Add a category filter to the product search
screen" is a Goal; "clean up search" is not — it leaves open whether this is
investigation, design, or a fix.

### Context Pointers

Locations, not summaries: file paths, directories, README sections, issue or
doc URLs relevant to the task. Point at where to look and let Codex read the
material itself rather than paraphrasing it into the prompt — a paraphrase
risks losing the detail that mattered. List only what's relevant to this
task; too few pointers leaves Codex guessing, too many buries the ones that
matter.

### Constraints

What the agent must and must not do: reuse existing libraries, don't add new
dependencies, follow existing naming conventions, don't touch the DB schema.
Constraints carry a project's accumulated history — prior design decisions,
team conventions, compatibility requirements — that Codex cannot infer from
code alone. Without them, a Goal-only prompt tends to get implemented with
whatever's currently fashionable rather than what fits the codebase.

**Constraints need both a positive and a negative instruction.** "Reuse the
existing `<FilterDropdown>` component" (positive) pairs with "don't add a new
dependency" (negative). The negative half is the one people forget to write,
and it's exactly the gap where an agent "helpfully" breaks something that
already worked. AGENTS.md can hold project-wide conventions long-term; put
task-specific constraints in the prompt when a task needs them enforced
strongly.

### Done When

What counts as complete, in a form that resolves to yes/no by running or
checking something rather than by feel — covered in depth in §4.

### Worked example

Bad — no judgment material at all:

```text
add a category filter to search
```
Codex fills every unstated gap with the most plausible-looking guess: which
screen, how the API extends, whether to reuse or rebuild the UI component —
it might land fine, or silently replace an existing filter component or
break API backward compatibility.

Good — all four elements present:

```text
Goal: Add a category filter to the product search screen.

Context Pointers:
- Existing search screen: src/screens/ProductSearch/
- Search API implementation: src/api/products.ts
- Category definitions: src/constants/categories.ts
- Existing spec: the "Search" section of README.md

Constraints:
- Do not change the existing search API signature (query-param addition only)
- Reuse the existing <FilterDropdown> UI component
- No category selected -> return all items as before (backward compatible)
- Do not add any new dependency

Done When:
- npm test passes in full
- Selecting a category shows only that category's products (verified by E2E test)
- Search with no category selected still behaves as before (existing tests pass)
- Zero lint errors
```

Goal states the verb, not just the topic. Context Pointers name only
locations directly relevant to this task. Constraints pair a positive
instruction (reuse `<FilterDropdown>`) with negatives (don't change the
signature, don't add a dependency) that close off the exact shortcuts an
agent tends to take. Done When gives four independently checkable conditions
covering functional behavior, backward compatibility, and quality — Codex can
run its own tests, see what fails, fix, and re-run, because each condition
resolves to yes/no.

## 4. Done When — verification levels

Done When determines how much of a task Codex can close out on its own.
"Make it usable" gives Codex no way to judge its own output, so it reports
"done" at some arbitrary point and stops for a human to decide. "Show the
same validation error message as the existing form, and `npm test` / `npm
run lint` both pass" lets Codex verify most of the work itself. The
difference comes entirely from how Done When is written — and it only stays
writable at this precision when the task is already cut to a verifiable size
(§2).

### Three levels

| Level | How it's judged | Examples |
|---|---|---|
| 1 | A command | `npm test`, `npm run lint`, `pytest`, `cargo test` passes |
| 2 | Observed behavior | unauthenticated request returns 401, authenticated returns 200; selecting a category shows only matching products |
| 3 | Human review | no UI awkwardness, copy reads naturally, matches the design direction |

Level 1 is the ideal — an unambiguous pass/fail an agent can loop on — but
most real tasks can't stay entirely there: on-screen results need level-2
behavioral checks, and UI feel or design-direction fit are level-3 by
nature. Decide per task how much Codex verifies and where the human takes
over, and write that split into Done When explicitly.

### Bad -> good rewrites

| Category | Bad Done When | Good Done When |
|---|---|---|
| Validation | make it nice | Matches the existing form-validation error message; `npm test` and `npm run lint` both pass |
| API | make the API solid | Integration test confirms 401 when unauthenticated, 200 when authenticated |
| Search | improve search | Selecting a category shows only that category's items; no selection still shows all, as before |
| Copy | make the copy natural | Produce 3 copy candidates, each with a rationale for why it matches the existing screen's tone |

What the bad column shares: the bar for "done" shifts by who's judging it.
"Nice," "solid," "natural" exist only as an image in the requester's head.
The good column instead names a behavior, command, or review lens to check
against — even the level-3 row becomes usable once it names what to look at.

### Template for judgment-heavy tasks

When a task is inherently subjective — copy, UI feel, architecture-direction
calls — don't hand Codex the final decision; have it produce options and
tradeoffs and let a human decide. Reusable shape:

```text
Done When:
- Produce 3 candidate options
- Attach the pros/cons of each
- Report whether each fits the existing screen's tone/style
- Final selection is made by a human
```

Codex still does the legwork of generating and comparing options; the
judgment call stays explicitly with the human.

### Post-work report template

Pair Done When with a fixed reporting shape so a finished run is reviewable
without re-deriving what happened from the diff. Put this directly in the
prompt:

```text
After the work is done, report the following:
- Files changed
- Validations run
- Checks that passed
- Checks that failed
- Unconfirmed items
- Points that need human judgment
```

This lets a reviewer get the full picture before reading the diff. The last
two bullets are load-bearing: "unconfirmed items" surfaces things like a
skipped test environment or external API call, and "points that need human
judgment" flags exactly where a level-3 decision is still open.

## 5. Plan mode

Plan mode is not a way to hand the whole decision to the agent — it's a way
to make gaps in task design visible before any code gets written. A weak
Goal draws a clarifying question, missing Context Pointers surface as an open
question about what to read, missing Constraints show up as a risky choice in
the plan, a weak Done When leaves the verification step vague — the same
four elements from §3, checked against the actual codebase instead of
assumptions. It's most valuable whenever a wrong assumption would otherwise
surface only after a multi-file diff already exists, when walking it back
costs more than confirming the plan up front would have.

### Three phases

| Phase | What happens | Human's role |
|---|---|---|
| 1. Ground in the environment | Codex surveys existing code, dependencies, design, test entry points | provide initial direction |
| 2. Intent chat | Goal, success criteria, scope, and Constraints get aligned through dialogue | answer questions, supply context |
| 3. Implementation chat | files to change, function-level handling, data flow, and verification method get written up as an implementation plan | review the plan, decide to proceed or send it back |

Phase 1 gives Codex the codebase's shape but not the reasoning behind it —
why old compatibility code is still there, which screen is frozen
pre-release, which dependency the team avoids; that reaches Codex only
through phase 2's dialogue. Phase 3 turns the aligned intent into a concrete
plan: files, function handling, migration needs, test ordering. In phase 2,
Codex may return structured questions with a recommended option plus
alternatives (backed by a `request_user_input`-style mechanism) rather than
an open-ended "what do you want?" — picking the recommendation or an
alternative is cheaper than composing a free-form answer each time.

Controls: `Shift+Tab` cycles collaboration mode; `/plan` switches directly
into Plan mode; `/plan <prompt>` switches and sends in one step (current mode
shows in the CLI footer). Once a plan is presented, read it, ask questions or
request changes if something's off, and only then proceed to implementation.

### When to use it

- Refactoring spanning multiple files or modules
- New features touching API, screen, and tests together
- Directory restructuring or layer separation
- Unfamiliar codebases where existing design shouldn't break
- Hard-to-reverse changes: DB migrations, auth, billing, notifications
- Changes crossing UI, view-model, repository, and local storage together

### When to skip it

- Typo fixes
- A small copy change confined to one file
- Fixing one existing test's expected value
- A mechanical replacement where the approach is already decided
- Investigation-only tasks

The decision test is whether reviewing the approach before implementation is
worth the time it costs. Plan mode can double as a way to think out loud with
still-forming requirements, but the human still has to settle Goal and Done
When by the end of that conversation — Plan mode surfaces missing
requirements, it doesn't replace writing them.

### Reviewing a plan through the Mini Codex lens

A returned plan is a review target, not just a description to skim:

| Lens | What to check |
|---|---|
| Goal | Is the end state described as a concrete behavior? |
| Context Pointers | Are the files to read, related existing implementation, and test entry points identified? |
| Constraints | Are existing compatibility, dependencies, naming conventions, and no-touch areas respected? |
| Done When | Are the verification commands, screens to check, and expected results spelled out? |
| Blast radius | Is the change scoped tightly enough to review and roll back? |
| Ordering | Does it front-load investigation/tests/small changes and push riskier changes later? |

Codex's actual plan headings don't literally read "Goal" or "Done When" —
they show up as `Summary` (Goal), `Key Changes` (Context Pointers), `Assumptions`
(Constraints — what it will and won't do), and `Test Plan` (Done When). A
missing `Test Plan`, or a `Key Changes` that barely engages with existing
implementation, is the signal to send the plan back.

### Reasoning effort during planning

`model_reasoning_effort` and `plan_mode_reasoning_effort` can be set
independently in `config.toml`, so planning uses a higher effort than
ordinary execution:

```toml
# ~/.codex/config.toml
model_reasoning_effort = "medium"    # normal turns
plan_mode_reasoning_effort = "high"  # Plan mode only
```

Worth doing where missing something in the blast radius, or getting the
ordering wrong, costs more than the implementation itself — auth-method
migrations, schema changes, cross-cutting redesigns. It increases latency, so
reserve it for planning and drop back once implementation starts.

### Plan-size diagnostic: count verification axes, not steps

A long Key Changes list is not itself evidence a task is too big — a single
well-detailed feature naturally produces a long plan. What matters is
whether the **Test Plan spans unrelated concerns**. Checks covering several
distinct features or screens, rather than variations on one operation, is
the signal Plan mode is holding a task too large for it — go back to §2.

Concretely: six Test Plan items that are all variations on one delete
operation (cancel leaves state unchanged, confirm clears it, state survives
reload, buttons disable at zero items) is one verification axis. Six items
spanning form input, data-migration compatibility, search, sorting, due-date
display, and mobile layout is six axes in one plan — same item count,
different scope. Count of independent verifications, not line count of Key
Changes, is the real oversize signal.

## 6. Intervening during an in-flight run

Input sent while Codex is mid-turn is interpreted differently depending on
how it's sent:

| Key | Meaning | When to use it |
|---|---|---|
| `Tab` | queues input for the next turn | reserve the current work, schedule what comes after it finishes |
| `Enter` | injects into the current turn | correct or add to the premise of the work in progress |
| `Esc` | interrupts the current turn | stop now, in the normal input state (closes an open popup first if one is in front) |

`Tab` is for a natural next step following the current work — run tests after
implementation, tidy changed files after tests pass, produce the post-work
report at the end. Avoid queuing a follow-up you can't yet judge without
seeing the current result — e.g. "apply the same approach to the order
screen" before the search-screen change has even been reviewed.

`Enter` is for correcting the premise of the turn already running: "use the
existing `requireAdmin` check, don't build new authorization," or "use the
existing `UserPreferences` store, don't create a new one." Don't use `Enter`
to smuggle in an unrelated task ("also redesign the profile screen") — that
blurs the original Goal and Done When; queue it with `Tab` or send it as a
separate task afterward.

`Esc` is for changes not worth waiting out: an unintended `npm install`,
touching a file it shouldn't, or heading toward something hard to reverse (a
migration, a deletion). After interrupting mid-change across multiple files,
check what's already changed versus still pending before resuming.

### Escalating interventions is a task-design signal

Recurring interventions mean the setup missed something — fold it into the
prompt next time instead of catching it live. A constraint repeated each run
belongs in Constraints; a report requested after the fact belongs in Done
When; a file location pointed out each time belongs in Context Pointers:

```text
Instructions added mid-run this time:
- do not add new dependencies
- use `UserPreferences`
- run the ViewModel tests when done

Fold into next time's Constraints/Done When:
- do not add new dependencies
- store settings via the existing `UserPreferences`
- report the result of `./gradlew testDebugUnitTest`
```

A rising rate of `Enter`/`Esc` interventions is the practical signal that
task design was too loose — fix it at the prompt level, not by absorbing it
live every run.
