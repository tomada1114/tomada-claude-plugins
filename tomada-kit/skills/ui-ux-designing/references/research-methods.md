# Competitor UX research

How to research competitors' flows, navigation, and state handling. The goal is not a list of nice-looking apps but the material the question rounds are built from. Visual style research (palettes, typography, look and feel) is out of scope: `refero-design` does it.

When research is delegated, this file is the sub-agent's procedure and output contract; the prompt template is `agents/research-competitors.md`.

## Contents

- [Three steps](#three-steps)
- [Choosing what to study](#choosing-what-to-study)
- [Search queries](#search-queries)
- [Summary format](#summary-format)
- [Sources](#sources)

---

## Three steps

Keep the order. Why: looking at competitors first turns their UI into the requirements.

### Step 1: Jobs to be done (before looking at competitors)

Write 3–5 jobs for the target user in the form "When [situation], I want to [motivation], so I can [expected outcome]". Judge everything after this by whether the job gets done.

```markdown
### Jobs to be done
1. When [commuting, one hand free], I want to [see what's next today], so I can [know the next item within 3 seconds of opening]
```

Write them from the confirmed target user. If they cannot be written, the gap is in requirements, not research — stop and say so.

### Step 2: The same 3–4 flows across every competitor

Pick 3–4 flows that serve the jobs and walk **the same flows in every competitor**. The unit of comparison is the whole flow — step count and what each step does — not individual screens.

Always include "first launch → first success". The rest map to the top 2–3 jobs (e.g. search → compare → decide, create → share).

| Flow | Steps | Competitor A | Competitor B | Competitor C | Implication |
|---|---|---|---|---|---|
| First launch → first success | A:5 / B:3 / C:7 | What each step asks for or shows | | | What this product does |

Record per step: screen count / fields requested / likely drop-off points (permission prompts, sign-up, payment) / whether the user can go back.

Prefer hands-on use. Mark rows written only from articles or screenshots. Why: many reviews are written without using the UI.

### Step 3: Heuristic scoring on a fixed rubric

Score each competitor 1–5 on six criteria. Do not add criteria. Why: more criteria make the scoring sloppier and the comparison useless.

| Criterion | 1 | 5 |
|---|---|---|
| Navigation clarity | Current location unclear | Location and way back always clear |
| Information structure and labels | Terms change between screens | Consistent vocabulary, no guessing |
| Feedback and status | Result of an action unclear | In progress / done / failed visible at once |
| Error handling and recovery | Error text stops the user | Cause and next action stated |
| Empty states and first run | Blank screen | Says what to do next |
| Accessibility and trust cues | Color-only distinctions, unclear pricing or terms | Non-color cues, terms shown up front |

Give every score a one-line reason.

---

## Choosing what to study

The main session picks at least three products; the sub-agent never swaps them. Candidates come from the "Reference products" tables in `app-type-ux-patterns.md` / `app-type-ux-patterns-verticals.md`, plus real products close to the target user. Products marked as observed anti-examples are studied for what to avoid.

---

## Search queries

Replace `{year}` with the current year at run time; fill `[App Name]` and `[app type]`.

```
"[App Name] onboarding flow screens"
"[App Name] user experience critique {year}"
"[App Name] app UX case study"
"[app type] onboarding flow comparison"
"best [app type] app UX patterns {year}"
"[App A] vs [App B] UX comparison"
```

Check each article's date. Do not use "trend" articles older than two years as evidence (primary guidelines are exempt). Do not use undated articles, articles that never show the actual UI, or affiliate listicles.

---

## Summary format

Everything goes into one summary with **these section names in this order** — the main session and the delegation contract both depend on them.

```markdown
## UX research summary

### Scope and assumptions
- Product / target user / app type / competitors studied (3+)
- Which were used hands-on and which were judged from articles only

### Jobs to be done
1. When [situation], I want to [motivation], so I can [outcome]

### Flow comparison
| Flow | Steps | Competitor A | Competitor B | Competitor C | Implication |

### Heuristic scores
| Criterion | Competitor A | Competitor B | Competitor C | Direction for this product |
(all six criteria, each score with a one-line reason)

### Patterns to avoid
| Pattern | Problem | Alternative | Seen in |

### Implications
- Adopt: [pattern] — why, and which job it serves
- Reject: [pattern] — why
- Split decisions: [point] — option A vs B (asked in the question rounds)

### Sources
- [Title](URL) — date / what it was used for
```

Every claim has a source or says "hands-on". Anything unverified is marked "Unverified".

---

## Sources

Primary, preferred:

- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/) — iOS and macOS conventions
- [Material Design 3](https://m3.material.io/) — Android conventions
- [Nielsen Norman Group](https://www.nngroup.com/articles/) — research-based usability principles
- [Baymard Institute](https://baymard.com/research) — measured e-commerce and checkout research (first choice for commerce)
- [WCAG 2.2 Understanding](https://www.w3.org/WAI/WCAG22/Understanding/) — what each criterion means

Real product flows:

- Refero flows (`refero:refero_search_flows`, `refero:refero_get_flow`) when the Refero MCP server is connected — multi-step journeys of real products, directly usable for Step 2
- [Mobbin](https://mobbin.com/) — real app screens organized by flow
- Installing the product and walking the flows yourself — best when possible

Use with care: Dribbble and Behance shots are concept art that ignore states, accessibility, and real data volume — never UX evidence. SEO listicles and personal blogs only when they cite a primary source.
