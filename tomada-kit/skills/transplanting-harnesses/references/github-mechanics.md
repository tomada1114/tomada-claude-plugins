# GitHub mechanics and the plan format

`scripts/create_issues.py` owns every write to GitHub. This file is the contract between
the plan written at step 5 and what the script does with it — read it while writing
`plan.json`, not while debugging the script.

## Table of Contents

- [plan.json](#planjson)
- [Field semantics](#field-semantics)
- [What dry-run validates](#what-dry-run-validates)
- [Why REST rather than gh flags](#why-rest-rather-than-gh-flags)
- [The tracking issue's contract](#the-tracking-issues-contract)
- [Two-pass creation](#two-pass-creation)
- [Idempotency](#idempotency)
- [When a native link fails](#when-a-native-link-fails)

---

## plan.json

```json
{
  "repo": "owner/name",
  "reference": {"source": "<url or path>", "commit": "<sha>", "license": "MIT", "snapshot_dir": "docs/harness-reference"},
  "labels": [{"name": "priority: P0", "color": "b60205", "description": "..."}],
  "tracking": {"title": "...", "body_file": "bodies/tracking.md", "labels": ["chore"]},
  "issues": [
    {"key": "agents-md", "title": "...", "body_file": "bodies/agents-md.md",
     "priority": "P0", "labels": ["chore"], "depends_on": ["other-key"],
     "area": "policy-docs", "touches": ["AGENTS.md"], "design": "settled"}
  ]
}
```

## Field semantics

- `body_file` is relative to `plan.json`, so the run directory moves as a unit.
- `design` is `settled` or `open`. `open` earns the issue the `blocked: design` label,
  which holds it out of automatic implementation downstream until someone decides the
  approach and records the decision on the issue.
- `priority` is `P0`–`P3`. The script adds the matching `priority: Pn` label; the body
  never states the tier in prose.
- `depends_on` holds plan keys, never issue numbers — the numbers do not exist yet. The
  script computes `Blocks` as the reverse edges, so each edge is declared exactly once.
- `area` and `touches` become the ship contract's `area=` and `touches=` fields.
- `labels` are the issue's own labels beyond the two the script derives. Label objects
  under the top-level `labels` key are the definitions created or updated in the repo
  before any issue is filed.
- `tracking` has no `priority`: the parent is an umbrella, and a tier on it invites a
  downstream workflow to try to implement it. The script appends the sub-issue task list
  to its body.
- `reference` is recorded for provenance and is what the seed pull request's README
  quotes: source, commit SHA, license, and the directory the snapshot lands in.

## What dry-run validates

Running the script without `--apply` writes nothing and checks the plan:

- every `body_file` exists, and none of them already contains a `## Dependencies`
  section, a ship contract comment or an idempotency marker — those are the script's to
  append, and a hand-written copy ends up duplicated or contradicted;
- no body mentions `plan.json`, a home-directory path or a `~/` path — the implementer
  reads the issue from another checkout where none of those exist;
- no body puts a dependency phrasing (`after`, `depends on`, `blocked by`, `requires`,
  `blocks`, and their Japanese forms) directly before or after a `{{#key}}` the plan does
  not declare as that edge — the downstream digest scrapes prose for exactly these and
  unions them with the declared edges, so "after {{#x}}" becomes a real blocker. Reword
  ("once {{#x}} lands") or declare the edge;
- every key in `depends_on` and every `{{#key}}` in a body names an issue in the plan;
- the dependency graph is acyclic;
- no blocker carries a lower priority than something it blocks (see `sequencing.md` for
  why that ordering deadlocks the downstream run);
- `repo` matches the repository the command is run in.

It then prints the issues in the order they will be created — key, title, priority,
depends-on. That list is what the user approves.

## Why REST rather than gh flags

The `gh` CLI grew `--parent`, `--add-sub-issue` and `--add-blocked-by` in version 2.94;
older installations are common and the failure mode is an unrecognised flag in the middle
of a half-created backlog. The script calls `gh api` against the REST endpoints instead,
which behave the same across CLI versions:

| Operation | Endpoint |
|---|---|
| Create or update a label | `gh label create --force` — stable across CLI versions, and it handles names such as `priority: P0` that a REST path would need URL-encoded |
| Create an issue | `POST /repos/{repo}/issues` |
| Attach a sub-issue | `POST /repos/{repo}/issues/{parent_number}/sub_issues`, body `{"sub_issue_id": <id>}` |
| Record a dependency | `POST /repos/{repo}/issues/{number}/dependencies/blocked_by`, body `{"issue_id": <id>}` |

Both link endpoints take the issue's **`id`** — the global database id from the create
response — not the `number` shown in the UI. Passing a number returns a 404, or worse
succeeds against an unrelated issue that happens to have that id.

Labels are created or updated, never deleted. Deleting a label removes it from every
issue in the repository that carries it, including issues this plan never touched.

## The tracking issue's contract

The tracking body gets a ship contract too: `tier=P3`, `blocked-by=` every sub-issue.
An umbrella with no contract looks like unblocked, unranked work to a downstream shipping
run, which then offers to implement it; declared as blocked by everything, it stays held
until the last sub-issue closes.

## Two-pass creation

1. **Create.** Every issue is filed with its body still holding `{{#key}}` references and
   no dependency section. The script records key → number, id and URL.
2. **Resolve and link.** Keys are substituted, `## Dependencies`, the ship contract and
   the marker are appended, the body is `PATCH`ed, and then the sub-issue and
   `blocked_by` links are made.

The split exists because an edge cannot reference a number that has not been assigned
yet. Splitting it also means a failure in pass 2 leaves readable issues behind rather
than half a graph.

`created.json` records the key → number, id and URL mapping plus which links succeeded.
It is what makes a resumed run cheap.

## Idempotency

Every created body ends with `<!-- harness-transplant: key=<key> -->`. Before creating
anything the script searches the repository's issues for those markers and reuses what it
finds, so a run interrupted after eleven of twenty issues picks up at the twelfth instead
of filing eleven duplicates. The marker is also how a later run recognises this plan's
issues when re-linking.

## When a native link fails

A failed sub-issue or dependency call is reported as a warning and the run continues. The
edges are already carried twice over: `Depends on #N` / `Blocks #N` in the body text, and
`blocked-by=` / `blocks=` in the ship contract, which is what the downstream shipping
workflow actually parses. The native links are the convenience layer for humans reading
the issue in the browser — worth having, not worth aborting a backlog for on a repository
where the feature is unavailable.
