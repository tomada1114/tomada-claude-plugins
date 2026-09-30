# Competitor UX research — sub-agent prompt

Fill the placeholders and pass the text below the rule as the prompt of one `executor` sub-agent (see SKILL.md step 2).

| Placeholder | Fill with |
|---|---|
| `{{SKILL_DIR}}` | Absolute path of this skill |
| `{{PRODUCT_SUMMARY}}` | Settled product summary, 2–3 lines |
| `{{TARGET_USER}}` | Target user: situation, motivation, constraints |
| `{{PLATFORMS}}` | Target platforms |
| `{{APP_TYPE}}` | App type, as a section name in `app-type-ux-patterns.md` or `-verticals.md` |
| `{{APPS}}` | At least three products, chosen by the main session |
| `{{FLOWS}}` | 3–4 flows to compare, always including "first launch → first success" |

---

<context>
Research the UX of at least three competitors of a {{APP_TYPE}} product.

Why: the result becomes the evidence behind the UX policy options the main session puts to the user, and is shown to the user as-is. One unsupported claim corrupts every option built on it — cite a source for each claim and mark anything you could not confirm as "Unverified".

Settled inputs (do not re-research these):
- Product: {{PRODUCT_SUMMARY}}
- Target user: {{TARGET_USER}}
- Platforms: {{PLATFORMS}}
- App type: {{APP_TYPE}}
- Products to study: {{APPS}}
- Flows to compare: {{FLOWS}}
</context>

<instructions>
Read {{SKILL_DIR}}/references/research-methods.md in full first and follow its three steps (jobs to be done → the same flows across competitors → six-criterion rubric), its query patterns, and its source rules. Replace the year in queries with the current year.

Scope is UX only: flows, navigation, state handling (empty, loading, error, offline, permission), feedback, forms, and accessibility cues. Skip visual style — colors, typography, look and feel.

Constraints: do not swap or add products; do not spawn sub-agents — finish in this session.
</instructions>

<output>
Return the summary in the "Summary format" of research-methods.md, with every section, in that order, under those names. Your final message is the summary only — no raw search results, work log, or article digests. Leave split decisions as options under "Implications → Split decisions"; do not decide them.
</output>
