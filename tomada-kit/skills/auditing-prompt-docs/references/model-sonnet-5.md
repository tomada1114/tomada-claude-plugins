<!-- audit-ignore-file: A006 -->
<!-- prompt-lint-ignore-file: P001,P002,P004,P006,P008,P010,P011 -->
# Prompting Claude Sonnet 5

Strong on coding and agentic tasks, and more agentic by default than Sonnet 4.6.
Existing 4.6 prompts run well; the items below are what needs tuning.
Provenance in `sources.md`.

## Table of Contents

- [Response length](#response-length)
- [Effort and thinking depth](#effort-and-thinking-depth)
- [Sampling parameters](#sampling-parameters)
- [Tool use triggering](#tool-use-triggering)
- [Progress updates](#progress-updates)
- [Literal instruction following](#literal-instruction-following)
- [Code review harnesses](#code-review-harnesses)
- [Interactive coding products](#interactive-coding-products)
- [Design and frontend defaults](#design-and-frontend-defaults)
- [Tone](#tone)

---

## Response length

Length is calibrated to task complexity rather than a fixed verbosity — shorter
on lookups, longer on open-ended analysis. If a product depends on a particular
shape, prompt for it:

```text
Provide concise, focused responses. Skip non-essential context, and keep
examples minimal.
```

For a specific kind of verbosity (over-explaining, say), a positive example of
the concision you want outperforms an instruction about what to avoid.

## Effort and thinking depth

Effort defaults to `high`. The ladder:

- `max` — maximum capability, no constraint on token spend.
- `xhigh` — the recommended setting for the hardest coding and agentic work.
- `high` — the default; balances tokens and intelligence.
- `medium` — cost-sensitive work, trading some intelligence.
- `low` — short scoped tasks and latency-sensitive work that is not
  intelligence-sensitive.

Rough migration mapping: Sonnet 5 at `medium` ≈ Sonnet 4.6 at `high`; Sonnet 5
at `high` ≈ Sonnet 4.6 at `max`. When benchmarking, match on observed thinking
length rather than effort name.

Effort levels are respected strictly, especially at the low end: at `low` and
`medium` the model scopes its work to exactly what was asked. Good for cost;
on a moderately complex task at `low`, there is some risk of under-thinking.

**When reasoning looks shallow, raise effort rather than prompting around it.**
Where latency forces `low`, a targeted nudge works:

```text
This task involves multistep reasoning. Think carefully through the problem
before responding.
```

Adaptive thinking is on by default — a change from 4.6, where a request with no
`thinking` field ran without thinking. Two consequences worth auditing for:
`max_tokens` is a hard limit on thinking plus response together, so budgets
tuned for a no-thinking 4.6 workload can now truncate; and the tokenizer
produces roughly 30% more tokens for the same text, compounding that. If
thinking blocks appear more often than wanted (common with large system
prompts), steer with the thinking-depth instruction in
`general-practices.md#thinking-and-effort`.

Manual extended thinking (`budget_tokens`) returns 400. See `rules.md` P010.

## Sampling parameters

Setting `temperature`, `top_p`, or `top_k` to a non-default value returns 400 —
new for Sonnet-class models. Remove them and steer tone and variety from the
prompt. See `rules.md` P011.

## Tool use triggering

More agentic by default: it reaches for tools and runs self-verification loops
more readily. Effort is a lever here too — `high` and `xhigh` show substantially
more tool use in agentic search and coding.

The exception is thinking disabled, where it is *less* likely to reach for a
tool or consider searching. A workload that depends on tool calls with thinking
off needs an explicit nudge in the system prompt describing when and why to use
each tool.

## Progress updates

It gives regular, well-calibrated updates through long agentic traces. Scaffolding
that forces interim status messages ("after every 3 tool calls, summarize") should
be removed. If the updates are miscalibrated for the use case, describe what they
should look like and give an example. See `rules.md` P006.

## Literal instruction following

It interprets prompts literally and explicitly, particularly at lower effort. It
does not silently generalize an instruction from one item to another, and it
does not infer requests you did not make.

The upside is precision for tuned API prompts, structured extraction, and
predictable pipelines. The cost is that **scope must be stated**: "Apply this
formatting to every section, not just the first one" is required, not redundant.

## Code review harnesses

A harness tuned for an earlier model can show *lower* recall on Sonnet 5. This
is a harness effect, not a capability regression: with "only report high-severity
issues" or "don't nitpick" in the prompt, the model investigates just as deeply,
finds the bugs, then declines to report what falls below the stated bar.
Precision rises, measured recall falls.

```text
Report every issue you find, including ones you are uncertain about or consider
low-severity. Do not filter for importance or confidence at this stage — a
separate verification step will do that. Your goal here is coverage: it is
better to surface a finding that later gets filtered out than to silently drop a
real bug. For each finding, include your confidence level and an estimated
severity so a downstream filter can rank them.
```

This works even without an actual second stage. If the harness does have a
verification, dedup, or ranking stage, say explicitly that the finding stage's
job is coverage. For genuine single-pass self-filtering, set a concrete bar
("bugs that could cause incorrect behavior, a test failure, or a misleading
result; omit pure style and naming preferences") rather than a qualitative word.

## Interactive coding products

For interactive, multi-turn coding agents, use `xhigh` or `high` effort, add
autonomous modes, and reduce the number of human turns required. Specify the
task, intent, and constraints in the first turn: an underspecified prompt
revealed progressively over several turns costs more tokens and sometimes
performs worse.

## Design and frontend defaults

On open-ended briefs it settles into a consistent default visual style, which
reads wrong for dashboards, dev tools, fintech, healthcare, and enterprise apps.
Generic corrections ("don't use that color", "make it clean") shift it to a
different fixed palette rather than producing variety. Two approaches work:

1. **Specify a concrete alternative** — exact palette hexes, typeface character,
   spacing and radius rules, section-by-section structure. It follows explicit
   specs precisely.
2. **Ask for options before building** — "Before building, propose 4 distinct
   visual directions (each as bg hex / accent hex / typeface plus a one-line
   rationale). Ask the user to pick one, then implement only that." With
   `temperature` unavailable, this is the recommended way to get meaningfully
   different directions across runs.

## Tone

Prose style shifts between model generations. A product relying on a specific
voice should re-evaluate its style prompts against the new baseline rather than
assume the old ones still land.
