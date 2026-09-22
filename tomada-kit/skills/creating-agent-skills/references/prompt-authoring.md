<!-- audit-ignore-file: A006 -->
<!-- prompt-lint-ignore-file: P001,P002,P003,P004,P005,P006,P008,P009,P013 -->
# Prompt Authoring Inside Skills

A skill is a prompt. Structure (frontmatter, `references/`, `scripts/`) decides *when* text reaches the model; this file decides whether that text still *helps* once it gets there. Quoted phrasings below are anti-patterns shown for recognition, not instructions.

Several instructions that were load-bearing for earlier generations now measurably reduce output quality or trigger refusals. Audit skill prose against this file whenever you write or review one.

Sources: Anthropic's [prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) and the per-model guides for Opus 5.5, Fable 5.1, and Sonnet 5. Where a behavior was measured on Opus 5 and carried over to Opus 5.5, the row says so.

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
| "Add a final verification step", "use a sub-agent to double-check", "re-verify before responding" | Opus self-verifies and self-corrects by default (measured on Opus 5, carried to 5.5). These compound with it: more tokens, no quality gain. | Nothing. If you need evidence, ask for it: "State the commands you ran and their output." |
| "Only report high-severity issues", "be conservative", "don't nitpick" | Opus 5.5 and Sonnet 5 follow this **literally**: they investigate just as deeply, then suppress findings. Recall drops while the model looks worse at reviewing. | "Report every issue you find, including low-severity and uncertain ones. Attach a confidence and severity to each. Filtering happens in a separate phase." |
| "Show your reasoning", "explain how you arrived at this", "write out your thought process" | Can be declined under the `reasoning_extraction` refusal category (Opus 5.5 and Fable 5.1). | Ask for evidence, not thinking: `file:line` citations, command output, the artifact itself. |
| "Think carefully", "think step by step before answering" | Thinking is always on and sized by effort. The line adds latency, not quality. | Delete. Raise effort where the task needs more thought. |
| `CRITICAL:`, "You MUST", "NEVER EVER" | Written for models that undertriggered. Current models overtrigger on it: the rule fires where it should not. | Plain imperative plus the reason. Keep hard emphasis only for irreversible constraints, and say what breaks. |
| "If in doubt, use X", "always use the X tool" | Same root cause as shouting, as a blanket default. | Name the condition: "Use X when it would change the answer." |
| "After every 3 tool calls, summarize progress" | Opus 5.5 writes short updates between tool calls on its own; a fixed cadence adds noise. | Delete unless a harness needs a specific cadence. If the shape is wrong, show one example update. |
| "Hold all findings for the final response", "no running commentary" | Opus 5-era narration damping. Opus 5.5 already reports plainly; suppression makes long runs look stalled. | Delete. Add it back only if output is still too chatty on re-test. |
| A long list of "do NOT do X" clauses | Weaker than a positive example, and every clause costs context. | One or two positive examples in `<example>` tags. |
| "Use sub-agents whenever helpful" | Opus 5.5 already delegates readily. An open-ended nudge spawns sub-agents for work a single grep would finish. | State when delegation is and isn't warranted, and cap the count. |
| Step-by-step scripting of work that has many valid routes | Over-prescription built for earlier models degrades output on current ones. | Reserve low-freedom instructions for fragile operations. Elsewhere give the goal, the constraints, and the output contract. |
| "Be thorough and go above and beyond" on every task | Invites scope expansion the model already tends toward. | Say what "done" is. Ask for maximal coverage only on the one task that needs it. |

The rows most likely to hide in an older skill are the last two and restated defaults in general. When auditing, ask of each instruction: *does it change what the model would do without it?*

---

## What works

**Give the reason, not only the request.** `I'm doing X for Y; they need Z. With that in mind: <request>.` A model that knows why generalizes to cases the rule did not list.

**State the scope of an instruction explicitly.** Current models read literally and do not silently generalize from one item to another. "Apply this to every section, not just the first" is not redundant.

**Use positive examples over prohibitions.** 1–3 diverse examples in `<example>` tags beat a paragraph of rules.

**Separate content types with XML tags.** When a prompt mixes instructions, context, and variable input, `<instructions>` / `<context>` / `<input>` removes ambiguity. This matters most in sub-agent prompts, where the parent pastes in file slices.

**Pin the output contract.** Exact section names, finding format, citation style — whatever a downstream step merges mechanically.

**Calibrate length for written deliverables.** Files the model writes run long (measured on Opus 5; still the starting assumption). If a skill produces documents: "Match document length to the substance; no filler sections, redundant summaries, or boilerplate."

**Ask for evidence behind claims.** For long-running skills: "Cite the tool result behind each claim in the report; mark anything unverified."

**Constrain scope for narrow tasks.** "Deliver what was asked, at the scope intended. If a better approach exists, say so in a sentence and continue as asked rather than quietly transforming the task."

**Name the unwanted early stops in unattended skills.** On long multi-part runs Opus 5.5 can end a turn with a progress report and no tool call. A skill meant to run without a human says which stops it does not want (announcing the next step instead of doing it, offering to continue, listing non-blocking decisions) and which it does (blocked on the user, or on something deliberately protected).

---

## Sub-agent prompt layers

Every sub-agent prompt a skill emits carries the five layers listed in A4 of `orchestration-patterns.md` (load via SKILL.md): intent, bootstrap pointers, concrete paths, embedded slices, output contract with an escalation rule. Intent — one sentence on why the investigation exists and what the parent will do with the result — is the cheapest quality lever of the five.

Keep sub-agent prompts free of the legacy phrasings above. A parent skill that tells its sub-agent to "double-check the findings before reporting" pays for over-verification on every spawn.

---

## Assigning models and effort

A skill that spawns sub-agents says which tier each one runs on. Left unspecified, the mechanical specialist and the hard one both run on whatever the session happens to be.

| Sub-agent's job | Tier |
|---|---|
| Complex implementation, design judgment, code review and bug-finding, synthesizing scattered findings, anything with unresolved spec | `architect` (Opus 5.5 high) |
| Fully specified work with a clear pass/fail (settled-spec implementation, run the tests, add coverage, make CI green, commit, open the PR, bulk replace), routine research and enumeration | `executor` (Opus 5.5 low) |

The dividing line is **spec completeness, not size**. If the sub-agent could plausibly come back asking what you meant, it needed `architect`. The lower the tier, the more self-contained the prompt must be: an `executor` spawn needs explicit paths, an explicit output shape, and no open questions; an `architect` spawn can be handed the goal and the constraints.

Where the skill lives decides how to write this in. A skill installed alongside `orchestrating-models` (the user's global skills) names the tier by agent name and points to that skill for the criteria — it does not copy them, so a model change touches only the agent definitions and `orchestrating-models`. A skill that must stand alone (a public repository, a plugin others install) writes the conclusion in with `<!-- derived from orchestrating-models §2 -->` and ships its own `executor` / `architect` definitions under `.claude/agents/`.

Do not pin a model in SKILL.md frontmatter to control sub-agents — frontmatter `model:` sets the model for the skill's own turn and should usually be omitted so it inherits the session.

Effort is what separates the tiers, and not every spawn mechanism accepts it — naming only a model silently runs the spawn at the session's effort. How each host selects a tier is in `platform-notes.md` (load via SKILL.md).

---

## Prescriptiveness budget

Match instruction density to fragility, as in the degrees-of-freedom scale in SKILL.md — but bias lower than you would have for earlier models.

- **Low freedom is still correct** for fragile formats (OOXML, binary containers, migration ordering) where an improvised step corrupts the output.
- **Everything else** states the goal, the boundaries, and the output contract, and leaves the route open.

When refactoring an older skill, delete an instruction and check whether the default behavior is already at least as good. Frequently it is. Instructions that restate default behavior crowd the context and can pull the model toward a worse-specified version of what it would have done anyway.

---

## Review checklist

Used by the Improving playbook's *prose* lens. Run `audit_skill.py` first; its `A006` hint flags most legacy phrasings mechanically. These items are what a script cannot judge.

### PA1: Every instruction earns its tokens
For the two or three longest sections, ask what the model would do without them. If the answer is "the same thing," that section is a FAIL — it restates default behavior instead of adding to it.

### PA2: No forced verification
Look for an added verification step, a mandated re-check, or an extra pass inserted before responding. Self-verification is already the default; these cause over-verification, not better results.

### PA3: No severity self-filtering in detection or review steps
"Only report high-severity," "be conservative," "don't nitpick" lower recall — the model still investigates deeply, then suppresses findings. Filtering belongs in a later phase.

### PA4: No request to echo or explain reasoning, and no "think carefully" lines
Asking the model to narrate how it arrived at an answer is a FAIL; ask for evidence instead. A standing "think carefully" line is a FAIL too — effort controls thinking.

### PA5: Scope of each instruction is explicit for a literal reader
"Apply this to every section, not just the first" is required, not redundant.

### PA6: Prescriptiveness matches fragility
Step-by-step scripting is reserved for fragile operations (binary formats, migration ordering). Elsewhere the instruction gives goal, constraints, and output contract, and leaves the route open.

### PA7: Prohibitions replaced by positive examples where an example would do the work
Flag long negative-enumeration lists that one or two examples could replace.

### PA8: Emphasis and defaults are conditional
No shouted `CRITICAL` / `MUST` outside genuinely irreversible constraints, and no blanket "always use X" tool default.

### PA9: English throughout
`description` is English-only; the body and any user-facing text are English throughout, except where another language is genuinely the subject matter (e.g. a localization skill).
