# Competitor UX research — sub-agent prompt

Fill the placeholders and, if the runtime can delegate, pass the text below the rule as the prompt of one sub-agent at the low-effort execution tier (see SKILL.md step 2); otherwise run the same filled text yourself in the main session. Resolve `{SKILL_DIR}` to an absolute path before handing it over — a sub-agent does not start in the skill directory, so a relative path would resolve against the wrong place.

| Placeholder | Fill with |
|---|---|
| `{SKILL_DIR}` | Absolute path of this skill, resolved by the main session |
| `{{PRODUCT_SUMMARY}}` | Settled product summary, 2–3 lines |
| `{{TARGET_USER}}` | Target user: situation, motivation, constraints |
| `{{PLATFORMS}}` | Target platforms |
| `{{APP_TYPE}}` | App type, as a section name in `app-type-ux-patterns.md` or `-verticals.md` |
| `{{APPS}}` | At least three products, chosen by the main session |
| `{{FLOWS}}` | 3–4 flows to compare, always including "first launch → first success" |
| `{{USER_MATERIAL}}` | User-supplied product names, URLs, or screenshots when web search is unavailable; empty when it is available |

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
- User-supplied material: {{USER_MATERIAL}}
</context>

<instructions>
Read {SKILL_DIR}/references/research-methods.md in full first and follow its three steps (jobs to be done → the same flows across competitors → six-criterion rubric), its query patterns, and its source rules. File names mentioned inside it are relative to {SKILL_DIR}/references/. Replace the year in queries with the current year.

If you have no web search tool, do not guess from memory: say so in "Scope and assumptions", work only from the user-supplied material provided above, mark rows drawn from it "user-supplied", and mark every other cell "Unverified".

Scope is UX only: flows, navigation, state handling (empty, loading, error, offline, permission), feedback, forms, and accessibility cues. Skip visual style — colors, typography, look and feel.

Constraints: do not swap or add products; do not spawn sub-agents — finish in this session.
</instructions>

<output>
Return the summary in the "Summary format" of research-methods.md, with every section, in that order, under those names. Your final message is the summary only — no raw search results, work log, or article digests. Leave split decisions as options under "Implications → Split decisions"; do not decide them.
</output>
