---
name: kicking-off-apps
description: >-
  Take a rough app idea ("I want an app that…") to a new public GitHub repository cut
  from one of the user's template repositories, with signed-off requirements, UX flows,
  a researched design system, design decisions in the template's skills (no
  architecture docs), loose project permissions,
  and a dependency-ordered issue backlog for the template's shipping-issues.
  Orchestrates one child skill per stage — refining-requirements, designing-wireframes,
  ui-ux-designing, refero-design, bootstrapping-from-templates,
  configuring-project-permissions, designing-architecture, planning-tickets — and
  defers to the template's own skills. Resumable; hands off to a fresh session in the
  new repository. A `feature` mode scrutinizes a request for an app that already runs
  and files it as a tracking issue with sub-issues. Use when starting a new app from a
  template, when the user describes an app to build in a template, when resuming
  a kickoff, or when turning a feature request for an existing app into parent and
  sub-issues.
argument-hint: "[app idea, free-form | resume | feature <request>]"
metadata:
  platforms: claude-code, codex
---

# Kicking Off Apps

The user plays the client: they describe an app loosely, and this skill runs the
engagement — hearing, UX, visual design, repository, architecture, backlog — by calling
one child skill per stage and carrying decisions between them in files. Without it each
stage is done ad hoc, decisions made in conversation are lost at the session boundary,
and the template's own conventions (its bootstrap, its lock format, its issue contract)
get overwritten by generic defaults.

This skill owns the order, the gates, the state file, and the handoff. It does not own
any stage's content: each child skill does, and a template skill beats a global one on
the same subject.

## Contract

**Input:** the skill's argument — the app idea in the user's words, `resume`,
`feature <request>`, or empty. Empty with no resumable run → ask for the idea in one
open question.

**`feature <request>`** runs a different, shorter engagement on an existing app's
repository: scrutiny and hearing, optional wireframes and decisions, then a tracking
issue with sub-issues. It writes no state and no documents — the requirements live in
the issues. Follow [references/feature-mode.md](references/feature-mode.md) instead of
everything below; only the question-round rules and the precedence of the repository's
own skills carry over.

**Output:** the new repository at `$(ghq root)/github.com/<owner>/<slug>` and the state
directory described in [references/artifacts.md](references/artifacts.md), which also
defines every artifact path used below. Read it before stage 1.

## Before stage 1

1. **Resume check** — run the lookup in [artifacts.md](references/artifacts.md#finding-a-run-to-resume).
   A match resumes at the first unchecked stage; re-read `state.md` and the drafts
   instead of re-asking anything recorded there.
2. **Locate the template.** The working directory is normally the template. Confirm it
   with `gh repo view --json nameWithOwner,isTemplate`. If it is not a template, list
   the user's templates (`gh repo list --json name,isTemplate --limit 200` filtered on
   `isTemplate`) and ask which one fits the idea — or recommend one after stage 1's
   first round settles the platform.
3. **Read the template's map:** `AGENTS.md` (or `CLAUDE.md`), `README.md`'s "Using
   this template", and the index of the repository's skill frontmatter
   (`.claude/skills/*/SKILL.md` or `.agents/skills/*/SKILL.md`). Note which of these
   exist, because they replace a global default later: `starting-an-app`,
   `designing-ui`, `triaging-issues`, `shipping-issues`, and the skills that own each
   subject (stage 7 writes decisions into them). A `recording-architecture-decisions`
   skill, an ADR tree, a roadmap page or `steering-the-roadmap` skill, or a
   `docs/architecture*` tree is not one of them: the owner keeps design only in skills
   and no roadmap, so stage 7 removes it from the new app. When the host
   does not load a repository skill by name, read its `SKILL.md` and follow it the
   same way. The template fixes the stack; questions it already answers are not asked.

## Stages

Run in order. At the end of each stage: update `state.md`, show the user a short
summary of what was decided, and move on once they agree. Every question is asked as
2–4 options with their trade-offs, batched (at most 4 questions per round), with one
recommended option when there is a real recommendation; then wait for the answers.

| # | Stage | Skill | Output |
|---|---|---|---|
| 1 | Hearing and scrutiny | `refining-requirements` (hearing mode) | `requirements.md` |
| 2 | UX | `designing-wireframes`, then `ui-ux-designing` | `ux-flows.md`, `ux-guidelines.md` |
| 3 | Design system | `refero-design`, then the contrast pass of `ui-ux-designing` | `design-direction.md` |
| 4 | Init | `bootstrapping-from-templates` | the repository, Product section, drafts copied in, labels |
| 5 | Permissions | `configuring-project-permissions` | `.claude/settings.local.json` and `.codex/rules/local.rules`, gitignored |
| 6 | Handoff | this skill | resume prompt |
| 7 | Design decisions | `designing-architecture` | each decision and the design lock written into the skill that owns it — no architecture docs, ADRs, or roadmap |
| 8 | Issues | `planning-tickets` (repository conventions first) | tracking issues, sub-issues, dependencies |
| 9 | Wrap-up | this skill | report and human-only steps |

**Stage 1.** Pass the idea, the output path `$STATE/requirements.md`, and the template's
constraints (platform, stack, what the sample app shows). The hearing loops until the
user explicitly signs off; scrutiny — contradictions, missing flows, MVP bloat, conflicts
with the template — is part of each loop, not a separate pass. The first round also
settles the working title, which fixes `<slug>`: create `$STATE/state.md` then.

**Stage 2.** `designing-wireframes` writes screens and flows to `$STATE/ux-flows.md`;
`ui-ux-designing` writes app-wide UX policy to `$STATE/ux-guidelines.md`. Tell each the
platform and that the other document exists, so neither restates the other.

**Stage 3.** Read the template's `designing-ui` first: its lock format and its token
files are the target shape. Run `refero-design` for the research and the direction, and
write the result — primary reference, what is preserved and borrowed, role rules, token
values for light and dark — to `$STATE/design-direction.md` in that shape. Measure the
palette with `ui-ux-designing`'s contrast pass (`contrast <palette-source> into
$STATE/design-direction.md`); a failing pair goes back to the direction, not to a
silent tweak. Tokens are not applied to code here; that is a stage 8 issue.

**Gate before stage 4.** One question round confirming the identity inputs (owner,
repository name, visibility — public unless the user said otherwise — display name,
bundle identifier where the template has one, author, and the public contact for any
contact slot the template has: a profile URL, never an email address, which
`bootstrapping-from-templates` does not publish, the repository's one-line description
of what it is for, and whether it is a keeper — a repository a later cleanup must not
delete, which gets `【残す】` in front of the description and the `keep` topic) and
listing every remote write stages 4–5 will make: create the repository from the
template, set its description and topics, push to `main`, sync labels — and
running the template's bootstrap, which templates reserve for a human's request. A yes
authorizes exactly that list; record it in `state.md`.

**Stages 4–5** run on the new clone by absolute path (`git -C`, `cd <repo_path> && …`).
Stage 4 writes `AGENTS.md`'s Product section from the signed-off requirements, since
the template's checks fail while it is a placeholder. Stage 5 is a short hearing of its
own — the permission questions are the user's — and comes before the handoff so the
next session starts with the loose permissions already in place.

**Stage 6 — handoff.** The session started in the template directory, so the new
repository's settings, hooks, and skills are not loaded. Mark stage 6 done, then print
only the block for the host this run is on — start a session in the new repository, then
invoke this skill with `resume` — and stop:

```
# Claude Code
cd <repo_path> && claude
/kicking-off-apps resume

# Codex CLI
cd <repo_path> && codex
$kicking-off-apps resume
```

**Stage 7.** `designing-architecture` settles the decisions and writes each into the
skill that owns its subject; commit and push to `main` directly — the branch ruleset is
not applied until wrap-up. Every decision is written as present state in a skill, and an
architecture document, roadmap, or ADR machinery the template still ships is removed in
the same change.

**Stage 8.** `planning-tickets`, told the repository's own `triaging-issues` and
`shipping-issues` exist (when they do) so their label vocabulary, body rules, and
dependency spelling win. Show the plan table and get one yes before creating anything.

**Stage 9.** Report: repository URL, documents written, the decisions and where each is written, issue
count by tier with the tracking issues linked, and the human-only steps the template's
`starting-an-app` lists (branch ruleset, repository security settings, release secrets).
Offer to run the ruleset recipe for them; it writes to GitHub, so only on a yes. The
next move is the template's `shipping-issues`.

## Where decisions live

What the app is and is not becomes the Product section at stage 4, with the
requirements it cites. How it is built and why becomes skills at stage 7: each
hard-to-reverse choice as present-state text in the skill that owns its subject, where
an agent loads it when it touches that code — never an architecture overview, an ADR,
or a roadmap (git holds what a decision used to say; direction is the Product section
and the open issues). Units of work become issues at stage 8, and every issue cites the
requirements section or skill it implements rather than restating it. A decision that
changes later is rewritten in place in its skill, never only in an issue thread.

## Delegation

Stages 1–3, 5, and 7 are dialogue with the user and run in this session. When the
runtime can delegate, hand off only bounded, briefed work: a long verification run in
stage 4 to a low-effort executor sub-agent; drafting many issue bodies from a settled
plan in stage 8 to a tool-free writing sub-agent. The brief inlines what the
sub-agent needs (for stage 8: the approved plan table and the issue template content
from `planning-tickets`) and passes `repo_path` and `$STATE` as absolute paths, since a
sub-agent neither shares this skill's directory nor starts in the clone. When it cannot,
run the same work here, stage by stage in the same order. Tier names per host: [references/platform-notes.md](references/platform-notes.md).

## Platform notes

See [references/platform-notes.md](references/platform-notes.md).
