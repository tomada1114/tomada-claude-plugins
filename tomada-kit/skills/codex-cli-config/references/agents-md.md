<!-- platform-annex -->

# AGENTS.md

## Discovery order

Codex builds an instruction chain once per run, in this precedence order:

1. **Global scope** — in the Codex home directory (`~/.codex` by default, or `$CODEX_HOME`), Codex reads `AGENTS.override.md` if it exists, otherwise `AGENTS.md`. Only the first non-empty file at this level is used.
2. **Project scope** — starting at the project root (typically the Git root), Codex walks down to the current working directory. If no project root is found, it only checks the current directory. In each directory along the path it checks for `AGENTS.override.md`, then `AGENTS.md`, then any names listed in `project_doc_fallback_filenames`. At most one file per directory.
3. **Merge order** — files are concatenated from the root down, joined by blank lines. Files closer to the current directory override earlier guidance because they appear later in the combined prompt.

Concretely, for a session started in `my-project/packages/api/`:

```
~/.codex/AGENTS.md (or AGENTS.override.md)
my-project/AGENTS.md
my-project/packages/AGENTS.md            # if present
my-project/packages/api/AGENTS.md
my-project/packages/api/AGENTS.override.md   # shadows the sibling AGENTS.md in *this* directory only
```

`AGENTS.override.md` shadowing is per-directory: it replaces the plain `AGENTS.md` in the same directory, it does not suppress `AGENTS.md` files in other directories along the walk.

Because nearer-to-cwd content wins in the combined prompt, put repo-wide rules in the root `AGENTS.md` and put package- or directory-specific rules in that subdirectory's `AGENTS.md` — a conflicting instruction placed closer to the working directory takes priority over one placed higher up.

Related config keys:

- `project_doc_fallback_filenames` (`array<string>`) — extra filenames to try in a directory when neither `AGENTS.override.md` nor `AGENTS.md` is present.
- `project_doc_max_bytes` (default `32768`, i.e. 32 KiB) — Codex skips empty files and stops adding files once the combined size reaches this cap.
- `model_instructions_file` — points Codex at a file that fully *replaces* AGENTS.md instead of adding to it.

### When AGENTS.md gets truncated

If the combined size hits `project_doc_max_bytes`, the remainder is silently dropped — you get partial instructions with no error. Two remedies:

- Raise `project_doc_max_bytes` in `config.toml`.
- Split content across subdirectory `AGENTS.md` files instead of one large root file — only the directories relevant to the current working directory get pulled into the chain, so per-directory files also reduce what any single session loads.

`/init` scaffolds a starter `AGENTS.md` in the current working directory by exploring the project (package manifests, test framework, Git history) and writing a baseline you then edit. A `## Code Review Rules` section in AGENTS.md also feeds Codex's GitHub code review integration.

## AGENTS.md as Single Source of Truth across tools

Once GitHub Copilot, Claude Code, Cursor, Cline, or Amazon Q are all in play alongside Codex, writing the same coding standard into each tool's own config file produces duplicate — and eventually conflicting — copies of the same rule. The fix is to designate one file as the Single Source of Truth (SSOT) and make every other tool's config a one-line pointer into it.

Put the substance — coding conventions, security requirements, architecture decisions, test policy, prohibited actions — in the repo-root `AGENTS.md`. Then reduce each other tool's config to a pointer line:

| Tool | Config/pointer file | Content |
|---|---|---|
| Codex | `AGENTS.md` (repo root) | Loaded directly — no pointer needed. |
| GitHub Copilot | `.github/copilot-instructions.md` | "Refer to AGENTS.md for repository rules." |
| Claude Code | `CLAUDE.md` | "Refer to AGENTS.md for repository rules." |
| Cursor | `.cursor/rules/main.mdc` | "Refer to AGENTS.md for repository rules." |
| Cline | `.clinerules/main.md` | "Refer to AGENTS.md for repository rules." |
| Amazon Q | `.amazonq/rules/main.md` | "Refer to AGENTS.md for repository rules." |

This is not a Codex-specific convention — AWS's `awslabs/aidlc-workflows` and GitHub's Spec Kit (`Constitution.md`) implement the same pointer-to-SSOT pattern for the same reason: one edit to the SSOT propagates to every tool, and a new tool joining the stack needs only a one-line pointer added, not a rule rewrite.

Two operating rules keep the structure from rotting:

- **No stray rules.** Nothing but a pointer line goes into the other tools' config files — a rule written directly into `.cursor/rules/main.mdc` or similar breaks the SSOT guarantee silently.
- **Change AGENTS.md through review.** Treat it like a constitution: changes land through a pull request with an owner's approval, and the PR description captures *why* the rule changed, not just what changed — that context is what makes the rule maintainable six months later.

## Three-layer model: Always-on / On-demand / Enforced

| Layer | Mode | Mechanism | Role |
|---|---|---|---|
| 1 | Always-on | `AGENTS.md` | Auto-loaded on every session start. Holds the minimal set of invariant rules and pointers to other layers. |
| 2 | On-demand | Skills (`.agents/skills/`) | Loaded only when relevant. Specialized knowledge — case-type implementation patterns, domain-specific know-how — split out of AGENTS.md. See `references/skills-and-plugins.md`. |
| 3 | Enforced | Hooks (`~/.codex/hooks.json`, project `.codex/hooks.json`) | Fires mechanically before/after tool execution: `PreToolUse` (block before running), `PostToolUse` (verify after running), `UserPromptSubmit` (intervene on input). |

The distinction that matters operationally: **AGENTS.md is a request, Hooks are a mechanical block.** An instruction like "never touch `.env` files" in AGENTS.md can be ignored by the model under the right pressure; the same constraint enforced as a `PreToolUse` hook cannot be bypassed by the model at all — it fails the tool call outright. Route anything mechanically checkable (lint, formatting, secret-pattern scanning, forbidden paths, forbidden commands) to Hooks rather than relying on AGENTS.md prose to hold the line; keep AGENTS.md for guidance that genuinely requires judgment. Hooks require trust confirmation before running (see hook trust state, `--dangerously-bypass-hook-trust`).

Keep layer 1 thin — a bloated AGENTS.md pushes real rules out past the byte cap or past what the model reliably attends to. Push specialized, occasionally-needed knowledge to Skills, and push anything with a deterministic pass/fail check to Hooks.

## Retrospective-driven growth cycle

AGENTS.md and Skills are not finished after the first draft — they accumulate accuracy through use. Run periodic retrospectives (a recurring practice, not a one-off): ask Codex to review recent sessions for what went wrong and what an AGENTS.md addition would have prevented, then fold the highest-value 1-2 findings in. Splitting "surface the pattern" (Codex's job) from "decide whether it belongs in the SSOT" (a human's job) keeps this from becoming unreviewed self-modification.

Signals that a retrospective is due:

- Codex repeats the same mistake across sessions (you're issuing the same correction repeatedly).
- Review feedback on Codex's output keeps landing on the same point.
- Different team members phrase instructions to Codex inconsistently, producing inconsistent results.
- A new team member can't get expected behavior out of the existing AGENTS.md alone.

### Update-destination decision table

| Situation | Update destination |
|---|---|
| Change Codex's behavior repo-wide | Repo-root `AGENTS.md` |
| Rule scoped to one directory or sub-team | Subdirectory `AGENTS.md` |
| A reusable procedure worth invoking repeatedly | Skill (`SKILL.md` + supporting files) |
| A temporary override in one location | `AGENTS.override.md` (same directory) |
| A personal, provisional preference | `~/.codex/AGENTS.md` or `~/.codex/AGENTS.override.md` |

### Sizing principle

Short and accurate beats long and vague. A large AGENTS.md that Codex can't fully hold in context loses exactly the rules you most need enforced — every addition should be paired with periodic pruning, not appended indefinitely. The same applies to Skills: start with one or two high-value skills, and only widen scope once the initial set is proven out in practice.

A practical cadence: fold a five-minute "Codex friction" slot into a recurring team retro, land one or two concrete AGENTS.md/Skill edits per cycle, and route review-derived findings into an AGENTS.md `Review guidelines` section so the review bar sharpens over time along with everything else.
