# Provenance and refresh

What the knowledge in this skill was collected from, and how to bring it
forward when a new model ships. The dates below are data, not instructions —
they tell a reader how far the per-model files can be trusted.

## Collected knowledge

| Reference file | Source page | Model versions covered | Collected |
|---|---|---|---|
| `general-practices.md`, `rules.md` | [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) | cross-model reference for the current generation | 2026-09-05 |
| `general-practices.md` | [Prompt engineering overview](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview) | — | 2026-09-05 |
| `model-fable-5-1.md` | [Prompting Claude Fable 5.1](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1) | Claude Fable 5.1, Claude Mythos 5.1 | 2026-09-05 |
| `model-opus-5.md` | [Prompting Claude Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5) | Claude Opus 5 | 2026-09-05 |
| `model-sonnet-5.md` | [Prompting Claude Sonnet 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5) | Claude Sonnet 5 | 2026-09-05 |

Models named in the best-practices reference at collection time, so a model
absent from this list is newer than the files: Fable 5.1, Mythos 5.1, Fable 5,
Mythos 5, Opus 5, Opus 4.8, Opus 4.7, Opus 4.6, Sonnet 5, Sonnet 4.6, Haiku 4.5.

## Refreshing after a model release

The user triggers this; the skill does not check for new releases on its own.

1. Fetch the best-practices reference above. Its model-specific guidance table
   lists one page per current model — that table is the authority on which
   per-model files should exist.
2. Fetch the per-model page for each model this skill tracks, plus any page the
   table lists that has no `model-<name>.md` file yet.
3. Rewrite the affected `model-*.md` files. Replace rather than append: a
   per-model file describes one model's current behavior, and stacking
   generations makes it unreadable.
4. Update the divergence table in `general-practices.md#where-the-three-models-diverge`
   and the row set in the table above.
5. Review `rules.md` against the new pages. A rule survives only while the
   behavior it guards against is still real; a behavior that reversed (a model
   that now under-formats where its predecessor over-formatted) usually means
   the rule's *fix* text changes, not the rule's existence.
6. When a rule's detection changes, update `scripts/lint_prompt_doc.py` and its
   test in the same change, then run the suite from the skill directory.
7. Retire a model file when its model leaves the best-practices reference's
   model table. Delete it and its row rather than keeping it as history.
