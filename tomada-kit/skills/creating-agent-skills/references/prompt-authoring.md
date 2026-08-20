<!-- audit-ignore-file: A006 -->
# Prompt Authoring Inside Skills

A skill is a prompt. Structure (frontmatter, `references/`, `scripts/`) decides *when* text reaches the model; this file decides whether that text still *helps* once it gets there.

Model behavior moved. Instructions that were load-bearing for earlier generations are now neutral at best and actively harmful at worst — several of them measurably reduce output quality or trigger refusals on current models. Audit skill prose against this file whenever you write or review one.

Sources: Anthropic's [prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) and the per-model guides for Fable 5, Opus 5, and Sonnet 5.

## Table of Contents

- [Legacy phrasings to remove](#legacy-phrasings-to-remove)
- [What works](#what-works)
- [Sub-agent prompt layers](#sub-agent-prompt-layers)
- [Assigning models and effort](#assigning-models-and-effort)
- [Prescriptiveness budget](#prescriptiveness-budget)
- [Review checklist](#review-checklist)

---

## Legacy phrasings to remove

| Phrasing in the skill | What it now does | Write instead |
|---|---|---|
| "Add a final verification step", "use a sub-agent to double-check", "re-verify before responding" | Opus 5 self-verifies and self-corrects by default. These compound with that behavior and cause **over-verification** — more tokens, no quality gain. | Nothing. If you need evidence, ask for the report: "State the commands you ran and their output." |
| "Only report high-severity issues", "be conservative", "don't nitpick" | Sonnet 5 and Opus 5 follow this **literally**. They investigate just as deeply, then suppress findings. Recall collapses while the model looks like it got worse at reviewing. | "Report every issue you find, including low-severity and uncertain ones. Attach a confidence and severity to each. Filtering happens in a separate phase." |
| "Show your reasoning", "explain how you arrived at this", "write out your thought process" | On Fable 5 this can trigger the `reasoning_extraction` refusal category and force fallbacks to an older model. | Ask for evidence, not for thinking: file:line citations, command output, the artifact itself. |
| "After every 3 tool calls, summarize progress" | Current models already emit well-calibrated progress updates. Fixed scaffolding fights that and adds noise. | Delete it. If the shape is wrong, show one example of the update you want. |
| A long list of "do NOT do X" clauses | Negative enumeration is weaker than a positive example, and every clause costs context. | One or two positive examples of the output you want, wrapped in `<example>` tags. |
| "Use sub-agents whenever helpful" | Opus 5 and Fable 5 already delegate readily. An open-ended nudge produces sub-agents for work a single grep would finish. | State when delegation is and isn't warranted, and cap the count. See [Assigning models and effort](#assigning-models-and-effort). |
| Step-by-step scripting of work that has many valid routes | Over-prescriptive skills built for earlier models **degrade** output on Fable 5. | Reserve low-freedom instructions for fragile operations. Elsewhere give the goal, the constraints, and the output contract. |
| "Be thorough and go above and beyond" attached to every task | Invites scope expansion; Opus 5 already widens scope unprompted. | Say what "done" is. If you genuinely want maximal coverage, say so on the one task that needs it. |

The last two rows are the ones most likely to be hiding in an older skill of your own. When auditing, ask: *is this instruction still earning its tokens, or is it describing behavior the model now has by default?*

---

## What works

**Give the reason, not only the request.** Models connect a task to relevant context when they know why it exists. `I'm doing X for Y; they need Z. With that in mind: <request>.`

**State the scope of an instruction explicitly.** Sonnet 5 does not silently generalize from one item to another. "Apply this to every section, not just the first" is not redundant — without it you get the first section only.

**Use positive examples over prohibitions.** 1–3 examples in `<example>` tags beat a paragraph of rules. Make them diverse enough that the model doesn't over-fit one shape.

**Separate content types with XML tags.** When a prompt mixes instructions, context, and variable input, `<instructions>` / `<context>` / `<input>` removes ambiguity about which is which. This matters most in sub-agent prompts, where the parent pastes in file slices.

**Pin the output contract.** Exact section names, exact finding format, exact citation style. Mechanical merging downstream depends on it.

**Calibrate length explicitly.** Opus 5 writes longer files and longer replies than prior models. If a skill produces documents, say: "Match document length to the substance; no filler sections, redundant summaries, or boilerplate."

**Ground progress claims.** For skills that run long: "Before reporting progress, check each claim against a tool result from this session. If something is unverified, say so."

**Constrain scope for narrow tasks.** "Deliver what was asked, at the scope intended. If a better approach exists, say so in a sentence and continue as asked rather than quietly transforming the task."

---

## Sub-agent prompt layers

Extends A4 in `orchestration-patterns.md` (load via SKILL.md). Every sub-agent prompt a skill emits should carry five layers:

1. **Intent** — why this investigation exists and what the parent will do with the result. One sentence. Cheapest quality lever available.
2. **Bootstrap pointers** — reference files to read *before* anything else, by absolute path.
3. **Concrete paths** — the file list the parent already extracted. Never make a sub-agent `find` what the parent could have located.
4. **Embedded slices** — paste the relevant section of the diff or design doc directly, so the sub-agent doesn't re-fetch it.
5. **Output contract** — the exact return shape, plus an escalation rule ("if a judgment call is needed, report it as unresolved rather than deciding").

Layers 2–5 were already the discipline. Layer 1 is the addition: sub-agents given intent produce reports the parent can actually use, instead of generically complete ones.

Keep sub-agent prompts free of the legacy phrasings above. A parent skill that tells its sub-agent to "double-check the findings before reporting" pays for over-verification on every spawn.

---

## Assigning models and effort

A skill that spawns sub-agents should say which model each one runs on. Leaving it unspecified means every specialist — the mechanical one and the hard one alike — runs on whatever the session happens to be.

| Sub-agent's job | Model |
|---|---|
| Hard implementation, code review and bug-finding, synthesizing scattered findings, anything with unresolved spec | `opus` |
| Fully specified work with a clear pass/fail: run the tests, add coverage, make CI green, commit, open the PR, bulk replace, routine collection | `sonnet` |
| Enumerating, formatting, mechanical greps with no judgment | `haiku` |

The dividing line is **spec completeness, not size**. If the sub-agent could plausibly come back asking what you meant, it needed `opus`. This table is a derived copy of the canonical one in `orchestrating-models` §2 — revise there first. <!-- derived from orchestrating-models §2 -->

`fable` is available as a spawn target too, but it is rarely the right one: it is the orchestrator tier, suited to long-horizon and genuinely ambiguous work. A skill that spawns Fable for a bounded specialist task is usually mis-scoped — tighten the spec and use `opus`.

Do not pin a model in SKILL.md frontmatter to control sub-agents — the frontmatter `model:` field sets the model for the skill's own turn and should usually be omitted so it inherits the session. Set the model per spawn instead.

Effort is a separate lever from model. The Workflow tool's `agent()` accepts both `model` and `effort`; the Agent tool accepts `model` only. Use `low` for mechanical stages and `xhigh` only for the hardest verification or judgment stages. Dropping effort is the first cost lever to try on Opus, before dropping to a cheaper model.

Two rules of thumb carry most of the value when designing a multi-model skill. **Whether to delegate at all**: delegate for independent parallel tracks, for mechanical bulk work where the round-trip costs less than doing it inline, and for context isolation; do it yourself when judgment and execution are inseparable. **Per-model prompting**: the cheaper the model, the more self-contained the prompt must be — `haiku` and `sonnet` spawns need explicit paths, explicit output shape, and no open questions, while an `opus` spawn can be handed the goal and the constraints. Where the `orchestrating-models` skill is installed, its references cover this in depth.

---

## Prescriptiveness budget

Match instruction density to fragility, as in the degrees-of-freedom scale in SKILL.md — but bias lower than you would have for earlier models.

- **Low freedom is still correct** for fragile formats (OOXML, binary containers, migration ordering) where an improvised step corrupts the output.
- **Everything else** should state the goal, the boundaries, and the output contract, and leave the route open.

When refactoring an older skill, delete an instruction and check whether the default behavior is already at least as good. Frequently it is. Instructions that merely restate default behavior are not free — they crowd the context and can pull the model toward a worse-specified version of what it would have done anyway.

---

## Review checklist

Used by the Improving playbook's *prose* lens. Run `audit_skill.py` first; its `A006` hint flags most legacy phrasings mechanically. These items are what a script cannot judge.

### PA1: Every instruction earns its tokens
For the two or three longest sections, ask what the model would do without them. If the answer is "the same thing," that section is a FAIL — it restates default behavior instead of adding to it.

### PA2: No forced verification
Look for an added verification step, a mandated re-check, or an extra pass inserted before responding. Self-verification is already the model's default; instructions like these cause over-verification, not better results.

### PA3: No severity self-filtering in detection or review steps
"Only report high-severity," "be conservative," "don't nitpick" collapse recall — the model still investigates deeply, then suppresses findings. Filtering belongs in a later phase, not the detection step.

### PA4: No request to echo or explain reasoning
Asking the model to narrate how it arrived at an answer is a FAIL. Ask for evidence instead — citations, command output, the artifact itself.

### PA5: Scope of each instruction is explicit for a literal reader
"Apply this to every section, not just the first" is required, not redundant — a reader who does not silently generalize needs the scope spelled out.

### PA6: Prescriptiveness matches fragility
Step-by-step scripting is reserved for fragile operations (binary formats, migration ordering). Elsewhere the instruction should give goal, constraints, and output contract, and leave the route open.

### PA7: Prohibitions replaced by positive examples where an example would do the work
A list of "do NOT do X" clauses is weaker than one or two positive examples. Flag long negative-enumeration lists that an example could replace.

### PA8: English throughout
`description` is English-only; the body and any user-facing text are English throughout, except where another language is genuinely the subject matter (e.g. a localization skill).
