# Authoring Principles: Rationale and Anti-list

## Table of Contents

- [English is the authoring language](#english-is-the-authoring-language)
- [Concise is key](#concise-is-key)
- [A skill is a prompt](#a-skill-is-a-prompt)
- [Degrees of freedom](#degrees-of-freedom)
- [Deterministic work belongs in scripts](#deterministic-work-belongs-in-scripts)
- [Three-level loading and the size budget](#three-level-loading-and-the-size-budget)
- [Content rules](#content-rules)
- [Canonical directory layout](#canonical-directory-layout)
- [What NOT to put in a skill](#what-not-to-put-in-a-skill)
- [Production patterns worth copying](#production-patterns-worth-copying)

SKILL.md states each of these as a one-line rule. This file is the rationale,
the full examples, and the edge cases — read it once while authoring or
reviewing; SKILL.md never needs to repeat it.

## English is the authoring language

Write every part of a skill in English: `description`, SKILL.md body,
`references/`, `assets/`, script comments, sub-agent prompts, and the
user-facing text the skill instructs Claude to emit (questions, reports,
summaries). This holds even when the request arrives in Japanese and even for
skills only tomada will ever run — these skills ship as plugins, and tomada
uses them to keep reading English.

Descriptions are **English-only**, with no mirrored Japanese trigger keywords.
A Japanese request still matches an English description; trigger vocabulary is
matched on meaning, so pairing each English trigger with its Japanese
equivalent buys nothing and costs the description budget that truncation eats
first.

Use another language only where that language *is* the subject matter:

- the skill produces Japanese output (copy, release notes, mail drafts) — say
  so explicitly in the body;
- a reference quotes Japanese source material, UI labels, or error strings
  verbatim;
- a pattern must match Japanese text (audit regexes, slug rules for Japanese
  input).

Existing Japanese skills are not retrofitted. Translate one only when the user
asks, or when a playbook is already rewriting that file for another reason.

## Concise is key

The context window is a public good, shared with system prompts, history,
other skills' metadata, and the user request. **Default assumption: Claude is
already very smart.** Add only context it doesn't already have — challenge
each piece with "does Claude really need this?"

## A skill is a prompt

Structure decides *when* text reaches the model; wording decides whether it
helps once it gets there. Several instructions that were load-bearing for
earlier models are now neutral or harmful — forced re-verification, severity
self-filtering in review steps, requests to echo reasoning. Before writing or
approving skill prose, read `prompt-authoring.md` (linked from SKILL.md's Resources).

The single most common defect in an older skill: instructions that restate
behavior the model now has by default. They are not free — they crowd context
and pull toward a worse-specified version of what would have happened anyway.

## Degrees of freedom

Match instruction specificity to fragility:

- **High freedom** (text instructions): multiple valid approaches,
  heuristic-driven.
- **Medium freedom** (pseudocode/scripts with parameters): a preferred pattern
  with some leeway.
- **Low freedom** (specific scripts, few parameters): fragile operations,
  consistency critical.

A narrow bridge with cliffs needs guardrails; an open field allows many
routes.

## Deterministic work belongs in scripts

Any step whose result would be identical on every run — enumerating files,
counting, validating structure, converting formats, applying a rule table,
running tests — is a script, not prose. A script is faster, costs no context
for its source, and can be tested; prose describing the same procedure is
re-derived by the model each time and drifts. Keep judgment in the prose: what
the numbers mean, what to do about a failure, which of several valid routes to
take.

Scripts follow the conventions in `scripts-guide.md`'s Conventions section
(linked from SKILL.md's Resources): `scripts/` +
`scripts/tests/test_<name>.py`, `--json` for anything an agent parses, exit
codes 0/1/2, one responsibility per script, stdlib first with other
dependencies declared in SKILL.md, test coverage ≥ 90 %, and generated files
(`__pycache__/`, `.coverage*`) in `.gitignore`.
`scripts/check_scripts.py` enforces the checkable parts.

## Three-level loading and the size budget

1. **Metadata** (name + description, ~100 words) — always in context.
2. **SKILL.md body** — loaded when skill triggers, stays in context across
   every subsequent turn.
3. **Bundled resources** — loaded as needed; scripts can execute without ever
   being read.

Because the body is a recurring cost rather than a one-time one, the budget is
tight: **target ≤150 lines, warning above 200 (`W031`), error above 500
(`E030`)** — the same 500-line ceiling the official Agent Skills best
practices treat as a hard cap. `references/*.md` files get their own ceiling
for the same reason a body does: warning above 400 lines (`A010`) — moving
content out of SKILL.md only helps if it lands in a file scoped to one domain,
not a second monolith.

The decision rule for what stays in the body versus what moves to
`references/`: the body keeps the dispatch map, the decision points, and the
hard rules. Anything only one branch needs, any rationale, any worked example,
and any single sub-topic running past roughly 15 lines moves to a reference
with a one-line "read when" pointer left behind. See `patterns-and-structure.md`'s
"Sizing and slimming SKILL.md" section (linked from SKILL.md's Resources) for
the walkthrough of applying this to an existing oversized skill.

## Content rules

Cheap, mechanical, and each one fixes a real failure mode:

- **References one level deep from SKILL.md.** A reference that links to
  another reference gets previewed with `head`, not read — the model then
  acts on half the file.
- **Table of contents in any reference over 100 lines**, so a partial read
  still shows the full scope.
- **Forward slashes everywhere**, on every platform.
- **One default, not a menu.** "Use pdfplumber" beats "you could use pypdf,
  pdfplumber, or PyMuPDF". Give the escape hatch only where it's real: "for
  scanned PDFs, use pdf2image with pytesseract instead".
- **One term per concept.** Mixing "field"/"box"/"element" for the same thing
  makes instructions ambiguous to a literal reader.
- **No time-sensitive statements.** "Before August 2026, use the old API"
  rots. Put superseded material under an "Old patterns" heading instead.
- **MCP tools fully qualified** — `ServerName:tool_name`, or resolution fails
  when several servers are connected.
- **Name dependencies explicitly.** Don't assume a package is installed.

## Canonical directory layout

```
skill-name/
├── SKILL.md              # Required. Instructions
├── scripts/              # Executable code (token-efficient — output only loads)
├── references/           # Loaded only when needed; >100 lines → add ToC
└── assets/               # Templates, images, boilerplate used in output
```

## What NOT to put in a skill

- `README.md`, `INSTALLATION_GUIDE.md`, `QUICK_REFERENCE.md`, `CHANGELOG.md` —
  use git history.
- Auxiliary docs about the creation process or user-facing setup.
- Explanations of concepts Claude already knows (programming basics, common
  libraries).
- "When to Use" sections in the SKILL.md body — that information must live in
  the description field if you also want auto-triggering.

## Production patterns worth copying

- **QA as bug hunting** (from Anthropic's PPTX skill): assume problems exist
  and hunt for them — QA is a bug hunt, not a confirmation step. First
  renders are almost never correct. Frame the finding step as coverage and
  put filtering in a later phase, so the model doesn't suppress findings it
  judges minor.
- **Fresh-context verification, for long runs only**: on autonomous runs that
  stretch across many phases, a separate sub-agent checking the work against
  the spec beats self-critique, because drift accumulates. On a scoped task
  it is waste — the model verifies its own work by default, and instructing
  it again causes over-verification. Set an interval rather than a per-task
  rule.
- **Critical Rules section**: for fragile operations (OOXML, complex
  formats), add a prescriptive "Critical Rules" block at the bottom of
  SKILL.md listing exact constraints that must never be violated. Keep the
  block scoped to what is genuinely fragile; prescriptiveness elsewhere costs
  quality.
