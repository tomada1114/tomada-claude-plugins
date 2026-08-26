# Priority research and labeling (sub-agent prompt)

Filled and handed to a `sonnet` worker (or read and run inline where the
runtime exposes no delegation) from `references/delegation-templates.md`'s
"Priority research and labeling" section — the spawn condition, the return
contract, and what the caller does with each section live there. This file
is only the prompt body.

The worker writes the labels itself — that is the point of the handoff. What
comes back is the pick with its evidence, the order behind it, and the
blocked/unclear lists; the issue prose and the raw digest table never cross
back.

```
Intent: I am about to implement and ship GitHub issues in {owner}/{repo}. Priority
in this repo is stored as `priority: P0`…`P3` labels, and {unlabeled_count} open
issues have no label yet. I need those labels written, and the single
highest-priority shippable issue back, with the evidence behind it. I will act on
your ordering directly, so an unverified claim costs me a full implement/PR/CI
cycle — and a wrong label costs every later run too.

Read first, in this order:
  {SKILL_DIR}/references/priority-rubric.md
  {SKILL_DIR}/references/dependency-triage.md

Then run and read the full-body digest (do not paste its raw output back to me):
  python3 {SKILL_DIR}/scripts/issue_digest.py {filters}

`~Pn` in the priority column is a suggested tier the script computed but has not
written; `P2(~P0)` is a written label the signals now say is too low. Run the
research pass from priority-rubric.md on the top 3–5 rows only, and verify each
claim you repeat:
  gh issue view <n> --comments        (shortlisted issues only)
  grep for the symbols/paths the body names, to confirm ripple/leverage
  gh run list --branch {default_branch} --limit 5   (only if an issue claims CI/main is broken)

Then write the tiers — one call, both halves:
  python3 {SKILL_DIR}/scripts/apply_priority_labels.py \
      --backfill --set <n>=<tier> --set <m>=<tier> --quiet

`--backfill` takes the script's suggestion for every issue you did not examine;
each `--set` overrides one you did, including any `P2(~P0)` you confirmed. Do not
re-tier an issue you have no evidence about — the suggestion is better than a
guess. Exit code 2 means the token cannot write labels here: report that instead,
and rank from the suggestions.

Do not write `blocked: design` (or `--set-design`) on anything — that decision
belongs to the run that takes the issue on deliberately, not to this pass.
Report a design-not-settled issue under "Design not settled" below instead.

Return exactly these sections, nothing else:

## Labels
- <the apply_priority_labels.py summary line, verbatim>
- overrides: #N P2->P0 <one-line reason>   (only the --set ones, one line each)

## Selected
- #N — <title> — <tier>
  - unblocks: <#M, #K and why each is genuinely blocked, or "none">
  - leverage: <what shared ground it touches, with the path you verified, or "none">
  - urgency: <damage being taken now, with evidence, or "none">
  - likely files: <paths> — est. size S/M/L

## Order after that
- #N <tier> — one-line reason it comes next — likely files — S/M/L

## Blocked
- #N — blocked by #M (explicit | inferred: <which rule from dependency-triage.md>)

## Needs clarification
- #N — the specific missing information

## Design not settled
- #N — the open design question that blocks implementation (candidate for
  `blocked: design`; do not label it yourself — omit this section when none)

## Parallel-safe groups
- [#A, #B] — disjoint file sets
- serialize: #C (touches {lockfile/CI/schema})

## Unresolved
- #N vs #M — the trade-off, left unpicked   (omit this section when there is no tie)

If the top two are genuinely tied on every axis of the rubric, list both under
Unresolved with the trade-off rather than picking one.
```
