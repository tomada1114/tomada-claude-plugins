---
name: kicking-off-apps
description: >-
  Take a rough app idea ("I want an app that…") to a new public GitHub repository cut
  from one of the user's template repositories, with signed-off requirements, UX flows,
  a researched design system, architecture docs and ADRs, a loose project
  .claude/settings.json, and a dependency-ordered issue backlog for the template's
  shipping-issues. Orchestrates one child skill per stage — refining-requirements,
  designing-wireframes, ui-ux-designing, refero-design, bootstrapping-from-templates,
  configuring-project-permissions, designing-architecture, planning-tickets — and defers
  to the template's own skills wherever they exist. Resumable through a state file;
  hands off to a fresh session inside the new repository after init. Use when starting
  a new app from a template repository, when the user describes an app to build while
  in a template, or when resuming a kickoff.
argument-hint: "[app idea, free-form | resume]"
metadata:
  platforms: claude-code
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

**Input:** `$ARGUMENTS` — the app idea in the user's words, `resume`, or empty. Empty
with no resumable run → ask for the idea in one open question.

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
   this template", and the index of `.claude/skills/*/SKILL.md` frontmatter. Note which
   of these exist, because they replace a global default later: `starting-an-app`,
   `designing-ui`, `recording-architecture-decisions`, `steering-the-roadmap`,
   `triaging-issues`, `shipping-issues`. The template fixes the stack; questions it
   already answers are not asked.

## Stages

Run in order. At the end of each stage: update `state.md`, show the user a short
summary of what was decided, and move on once they agree. Every question goes through
AskUserQuestion, batched (at most 4 per call), with one recommended option when there
is a real recommendation.

| # | Stage | Skill | Output |
|---|---|---|---|
| 1 | Hearing and scrutiny | `refining-requirements` (hearing mode) | `requirements.md` |
| 2 | UX | `designing-wireframes`, then `ui-ux-designing` | `ux-flows.md`, `ux-guidelines.md` |
| 3 | Design system | `refero-design`, then the contrast pass of `ui-ux-designing` | `design-direction.md` |
| 4 | Init | `bootstrapping-from-templates` | the repository, Product section, drafts copied in, labels |
| 5 | Permissions | `configuring-project-permissions` | `.claude/settings.json` committed |
| 6 | Handoff | this skill | resume prompt |
| 7 | Architecture docs | `designing-architecture` | architecture overview, ADRs, design lock, roadmap |
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

**Gate before stage 4.** One AskUserQuestion call confirming the identity inputs (owner,
repository name, visibility — public unless the user said otherwise — display name,
bundle identifier where the template has one) and listing every remote write stages 4–5
will make: create the repository from the template, push to `main`, sync labels — and
running the template's bootstrap, which templates reserve for a human's request. A yes
authorizes exactly that list; record it in `state.md`.

**Stages 4–5** run on the new clone by absolute path (`git -C`, `cd <repo_path> && …`).
Stage 4 writes `AGENTS.md`'s Product section from the signed-off requirements, since
the template's checks fail while it is a placeholder. Stage 5 is a short hearing of its
own — the permission questions are the user's — and comes before the handoff so the
next session starts with the loose permissions already in place.

**Stage 6 — handoff.** The session started in the template directory, so the new
repository's settings, hooks, and skills are not loaded. Mark stage 6 done, then print
this and stop:

```
cd <repo_path> && claude
/kicking-off-apps resume
```

**Stage 7.** `designing-architecture` turns the drafts into the stable documents; commit
and push to `main` directly — the branch ruleset is not applied until wrap-up.

**Stage 8.** `planning-tickets`, told the repository's own `triaging-issues` and
`shipping-issues` exist (when they do) so their label vocabulary, body rules, and
dependency spelling win. Show the plan table and get one yes before creating anything.

**Stage 9.** Report: repository URL, documents written, ADRs and their status, issue
count by tier with the tracking issues linked, and the human-only steps the template's
`starting-an-app` lists (branch ruleset, repository security settings, release secrets).
Offer to run the ruleset recipe for them; it writes to GitHub, so only on a yes. The
next move is the template's `shipping-issues`.

## Where decisions live

Stable things become documents — what the app is and is not (the Product section at
stage 4, the requirements it cites), and at stage 7 the architecture's philosophy and
patterns, each hard-to-reverse choice as an ADR, the
direction as a roadmap. Units of work become issues at stage 8, and every issue cites
the document section it implements rather than restating it. A decision that changes
later is amended in its document, never only in an issue thread.

## Delegation

Stages 1–3, 5, and 7 are dialogue with the user and run in this session. Delegate only
bounded, briefed work: a long verification run in stage 4 to an `executor`; drafting
many issue bodies from a settled plan in stage 8 to a `worker`. Tiers: the
`orchestrating-models` skill.
