# Feature mode

`feature <request>` — the app already exists and runs; the user wants something added or
changed. The engagement is the same client-and-PdM dialogue as a kickoff, shrunk to what
a change needs: scrutinize the request against the running app, settle it, and file it
as a tracking issue with sub-issues that the repository's `shipping-issues` can ship.

Nothing persists outside GitHub. There is no state directory, no `state.md`, no resume,
and no commit: the repository's documents are read, never edited, and the settled
requirements live in the issue bodies. Working drafts go to a temporary directory
(`mktemp -d`) that is removed after the issues exist.

## Contents

- [Before the first question](#before-the-first-question)
- [Steps](#steps)
- [Where the requirements go](#where-the-requirements-go)

## Before the first question

The working directory is the app's repository (not a template). Confirm it with
`gh repo view --json nameWithOwner,isTemplate`; if it is a template, the user wants a
kickoff, not this mode — say so and ask. Then read what constrains the answer, so no
question re-asks something the repository settles:

- `AGENTS.md` / `CLAUDE.md`, `README.md`, and the repository's skill index — note
  `triaging-issues`, `shipping-issues`, `designing-ui`, `steering-the-roadmap`; the same
  precedence rule as a kickoff applies.
- The product documents it has: requirements, UX flows and guidelines, design lock,
  architecture overview, roadmap — and ADRs only where an older repository still keeps
  them.
- The code the request touches — enough to know what exists, what it is named, and
  which files a change would land in. Delegate a wide sweep to a read-only search
  sub-agent and keep only its conclusions.
- Open issues and pull requests on the same subject (`gh issue list --search`,
  `gh pr list --search`): a duplicate or an overlapping plan is the first thing to raise.

## Steps

Each step ends the same way as a kickoff stage: a short summary, then move on once the
user agrees. Questions follow the same rules (2–4 options with trade-offs, at most 4 per
round, one recommendation when there is one).

| # | Step | Skill | Runs when |
|---|---|---|---|
| F1 | Scrutiny and hearing | `refining-requirements` (refinement mode) | always |
| F2 | Screens | `designing-wireframes` | the change adds or reshapes a screen, window, or flow |
| F3 | Decisions | this skill, one option round per choice | the change makes a hard-to-reverse choice |
| F4 | Issues | `planning-tickets` (repository conventions first) | always |
| F5 | Report | this skill | always |

**F1.** Pass the request, the constraints read above, and an output path inside the
temporary directory. Scrutiny is measured against the running app as well as the draft:
contradictions with the requirements and design documents already in the repository, flows the
current UI cannot reach, data the current model does not hold, migration of existing
users' data, scope that belongs in a separate request, and overlap with open issues.
Loop until the user explicitly signs off. Then ask once, in one round, whether F2 and F3
are needed, recommending from what F1 found.

**F2.** Tell `designing-wireframes` the platform, the existing screens the change
touches, and the repository's UX guidelines (if any) so it does not restate them. It
writes into the temporary directory.

**F3.** For each hard-to-reverse choice (a new dependency, a schema or storage change, a
new OS permission, an external service, a change that contradicts the documented design),
research the options and settle it in an option round. Record each as a short
"Decision — options considered — why" entry for the tracking issue. When the change
contradicts the documented design, say so in that entry and add a sub-issue that
rewrites the affected design text in place, in the present tense, in the same change as
the code; this mode does not edit it.

**F4.** Run `planning-tickets`, told the repository's `triaging-issues` and
`shipping-issues` exist (when they do) and told the sources are the temporary drafts,
not repository documents: where it would cite a document section, it cites the tracking
issue's section instead. Default shape: one tracking issue for the request, its work
split into sub-issues, native sub-issue and blocked-by links. A request that turns out
to be a single reviewable change gets one issue and no parent — say so in the plan.
Show the plan table and get one yes before creating anything; that yes is the only
remote write this mode makes.

**F5.** The tracking issue and its sub-issues as a table with numbers and links, the
dependency layers, and anything left for a human (a `blocked: design` decision, design
text to rewrite). Remove the temporary directory. The next move is the repository's
`shipping-issues`.

## Where the requirements go

The tracking issue body carries the settled request, so a sub-issue can cite it by
section instead of restating it:

- **Background** — the request in the user's words and the problem it solves.
- **Requirements** — the signed-off sections from F1 (features with concrete values,
  EARS requirements with IDs, edge cases), plus an explicit Not In Scope.
- **Screens** — the F2 wireframes and flows, when F2 ran.
- **Decisions** — the F3 entries, when F3 ran.
- **Existing context** — the repository documents and code paths the change builds on,
  as links, and any documented design it changes.
- **Done when** and the sub-issue checklist, in the shape `planning-tickets` and the
  repository's `triaging-issues` define.

Sub-issues follow `planning-tickets`' body rules and cite the tracking issue
(`#N § Requirements R2`) for anything already stated there.
