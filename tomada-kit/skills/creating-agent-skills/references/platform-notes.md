<!-- platform-annex -->
# Platform notes: orchestration runner names

`orchestration-patterns.md` describes orchestration concepts in neutral terms (a
"deterministic fan-out runner", "a single spawn", "an effort knob"). This file is
the one place that maps those neutral terms to the concrete tool each host offers —
see `agent-neutral-authoring.md` for why tool names live only here.

## Concept → host mapping

| Neutral capability | Claude Code | Codex |
|---|---|---|
| Deterministic fan-out runner (loops, branching, resume, progress) | the Workflow tool (Dynamic Workflow) | no equivalent |
| Single sub-agent spawn | the Task tool / Agent tool | run the work inline in the main context |
| Barrier-free pipelining across stages | `pipeline()` inside a Workflow script | run stages sequentially in the main context |
| Per-spawn effort knob (in addition to model) | `agent()`'s `effort` param in a Workflow script | not exposed — only the main context's own effort applies |

## When to prefer the fan-out runner

Reach for it first for parallel or multi-stage execution: it gives deterministic
control flow, token-budget awareness, resume, and progress visibility, which suits
large decomposable, verification-heavy orchestration.

It is not a fit for steering interactively mid-run, or driving a real TUI from
outside — those fall back to spawning individual sub-agents (Claude Code) or
running the equivalent steps inline (Codex). Conversational questions and single
trivial edits need neither.

## Codex limitations (best-effort degradation)

- No deterministic fan-out runner exists on Codex: any pattern described as
  "spawn N in parallel, then join" or "pipeline stages without a barrier" becomes
  sequential inline work in the main context. Phase order is preserved; wall-clock
  time increases.
- No separate effort knob: Codex has only the main context's own effort/verbosity,
  not a per-spawn setting.
