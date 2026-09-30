---
name: planning-tickets
description: >-
  Break requirements and design documents into GitHub Issues an implementing agent can
  ship without asking back: concrete values with their source, EARS requirements,
  explicit Not In Scope, machine-readable `Depends on #N` edges, a parallel-first
  breakdown, tracking parents with native sub-issues, and native blocked-by
  dependencies. Follows the repository's own issue conventions first — a
  triaging-issues skill's labels and body rules, a shipping-issues skill's ship
  contract — and falls back to its own templates only where the repository has none.
  Use when cutting tickets, breaking a feature or a new app's MVP into issues, planning
  a sprint or backlog, or as the issues stage of kicking-off-apps.
metadata:
  platforms: claude-code
---

# Planning Tickets

An issue here is read by an agent that has none of this conversation: it must carry the
real values, the boundary of the work, and its place in the order, or the agent guesses.
The breakdown optimizes for parallel work — independent issues that do not touch the
same files — and makes every ordering constraint explicit and machine-readable.

## 1. Read the repository's conventions

Before drafting, look for the repository's own issue skills (`.claude/skills/` or
`.agents/skills/`) and forms (`.github/ISSUE_TEMPLATE/`, `.github/labels.yml`):

- **`triaging-issues`** — its labels (type, `priority: P0`–`P3`, `blocked: …`,
  `tracking`), what a body must contain, and how an ordering constraint is spelled.
  These **replace** this skill's defaults wherever they differ: its label set instead of
  the fallback labels, its body requirements added to the skeleton, its dependency
  spelling exactly.
- **`shipping-issues`** — the consumer. Read what it parses (its ship contract, e.g. a
  `<!-- ship: … -->` block, `touches=`, `design=`) and write every field it reads, so
  the backlog ranks and parallelizes without a research pass.
- **Title style** — follow the repository's existing issues and forms. The bracket
  prefixes in [templates/issue-template.md](templates/issue-template.md) are only for
  repositories with no convention.

## 2. Plan the breakdown

Sources are the documents, cited by path and section (`docs/product/requirements.md
§3.2`, an ADR number), never copied wholesale. Where a repository rule asks for a
`path:line` and the code does not exist yet, point at the file or directory the change
lands in and the document section it implements.

- **Independence over granularity.** A larger independent issue beats several small
  dependent ones; merge tasks whose split would only add edges. Target a reviewable
  pull request: one responsibility, a few files, 3–5 acceptance criteria.
- **Foundation first, then parallel streams, then integration.** Foundation issues
  (schema, core types, shared config, design tokens) get the highest tier the
  repository's rubric allows for groundwork; parallel issues must not touch the same
  files; every convergence of streams gets an integration issue.
- **Hierarchy is a judgment call.** Group issues under a tracking parent when they
  together deliver one outcome (a roadmap Now item, an MVP feature area) — the parent
  holds the checklist and the "done when", never work of its own. Skip the parent for a
  handful of unrelated issues.
- **Every issue** states concrete values with their source, EARS requirements
  (Ubiquitous / When / While / If-then / Where), boundary conditions, at least three
  concrete examples, acceptance criteria tied to requirement IDs, and Not In Scope
  naming where the excluded work lives. Skeleton and variants:
  [templates/issue-template.md](templates/issue-template.md).

Present the plan before creating anything: a summary table (title, labels, tier,
parent, depends on), the dependency layers, and which issues can run in parallel. Get
the user's yes — creating issues is a remote write.

## 3. Create

Follow [reference.md](reference.md): draft every body to a local file with provisional
IDs, create in dependency order, backfill real numbers into `Depends on` / `Blocks` /
`Part of` lines, then link natively — sub-issues under their tracking parent and
blocked-by relationships — so the edges show in GitHub's UI as well as in the bodies.
Body lines stay the source automation parses; native links mirror them.

When the repository has a roadmap page, fill each outcome's issue links after creation.

## Report

The created issues as a table with numbers and links, the tracking parents, the
dependency layers, and anything left for a human (a `blocked: design` decision, a
`blocked: external` step).
