# Kickoff artifacts and state

Every stage hands off through files, so a stage can be re-entered in a later session and a
child skill never needs the conversation that produced its input.

## Contents

- [State directory](#state-directory)
- [state.md](#statemd)
- [Where drafts land in the repository](#where-drafts-land-in-the-repository)
- [Finding a run to resume](#finding-a-run-to-resume)

## State directory

```
STATE_ROOT=${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/kicking-off-apps
STATE=$STATE_ROOT/<slug>/
├── state.md              ← this skill; the resume anchor
├── requirements.md       ← refining-requirements (stage 1)
├── ux-flows.md           ← designing-wireframes (stage 2)
├── ux-guidelines.md      ← ui-ux-designing (stage 2)
├── design-direction.md   ← refero-design (stage 3), plus the contrast table
├── init.json             ← bootstrapping-from-templates' create script output (stage 4)
└── issues/               ← planning-tickets drafts (stage 8), one file per issue
```

`<slug>` is the repository name the app will get: lowercase kebab-case of the working
title (`Habit Tracker` → `habit-tracker`). It is settled in the first hearing round. If
the name changes before stage 4, `mv` the directory and update `slug:` in `state.md`;
after stage 4 the repository name is fixed.

## state.md

Write it when the slug is known, and update it at the end of every stage — never only
at the end of the run. The header is read by a script-free grep, so keep one `key: value`
per line.

```markdown
---
slug: habit-tracker
app_name: Habit Tracker
template: tomada1114/tauri-template
template_path: /Users/me/ghq/github.com/tomada1114/tauri-template
repo: tomada1114/habit-tracker
repo_path: /Users/me/ghq/github.com/tomada1114/habit-tracker
visibility: public
identity: bundle-id=io.tomada.habittracker author="Jane Doe" email=jane@example.com
stage: 3
---

## Stages
- [x] 1 Hearing — requirements.md signed off (MVP 6 features, 9 non-goals)
- [x] 2 UX — 7 screens, ux-guidelines.md settled
- [ ] 3 Design system
- [ ] 4 Init (remote writes approved: no)
- [ ] 5 Permissions
- [ ] 6 Handoff
- [ ] 7 Architecture docs
- [ ] 8 Issues
- [ ] 9 Wrap-up

## Decisions
- One line per decision the user made, with the stage it came from.

## Open
- Anything deferred, with what would settle it.
```

`repo` and `repo_path` stay empty until stage 4 writes them.

## Where drafts land in the repository

Stage 4 copies the drafts into the new repository so everything later cites an in-repo
path. When the template already has a home for one of these (for example a
`docs/design/` tree or a requirements page), use that home instead and record the
mapping in `state.md`.

| Draft | Repository path |
|---|---|
| `requirements.md` | `docs/product/requirements.md` |
| `ux-flows.md` | `docs/product/ux-flows.md` |
| `ux-guidelines.md` | `docs/design/ux-guidelines.md` |
| `design-direction.md` | `docs/design/design-direction.md` (the research record; the binding lock is written in stage 7 where the template's `designing-ui` says) |

## Finding a run to resume

On invocation, before anything else:

```bash
STATE_ROOT=${AGENT_SKILL_STATE_DIR:-$HOME/.local/state/agent-skills}/kicking-off-apps
top=$(git rev-parse --show-toplevel 2>/dev/null)
grep -l "^repo_path: $top\$" "$STATE_ROOT"/*/state.md 2>/dev/null   # inside the new repository
grep -l "^stage: [0-6]\$" "$STATE_ROOT"/*/state.md 2>/dev/null      # unfinished pre-handoff runs
```

A `repo_path` match means this is the post-handoff session: continue from the first
unchecked stage. An unfinished pre-handoff run whose `template_path` is the current
directory is offered as "resume <slug>" alongside "start a new app".
