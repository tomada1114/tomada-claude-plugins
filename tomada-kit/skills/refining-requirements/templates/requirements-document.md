# Requirements Document Template

```markdown
# <Product name> — Requirements

- **Status:** Draft | Signed off YYYY-MM-DD
- **Platform and stack:** <platform>; <template or stack, and what it fixes>

## 1. Overview
- What it is, in one paragraph
- Target users: who, in what situation, with what pain
- Core interaction: the one thing a user does most; if this is not good, nothing is

## 2. Scope
### MVP
- <feature> — why it is needed for the core interaction (links to §3.x)
### Later
- <feature> — why it waits, and what would pull it forward
### Non-goals
- <what the app will not do, even where easy> — why

## 3. Features
(one section per MVP feature, using requirements-section.md)

## 4. Cross-cutting rules
Error handling, validation, loading and feedback, accessibility, data retention and
privacy — only the product-level decisions. Omit a line a later UX stage owns.

## 5. Data
Entities, their fields with types and limits, where they live, how long they are kept.

## 6. Open questions
- <question> — what would settle it

## 7. Decision log
- YYYY-MM-DD <decision> (rejected: <alternative>, because <reason>)
```

Match length to substance: a section with nothing decided is omitted, not padded.
