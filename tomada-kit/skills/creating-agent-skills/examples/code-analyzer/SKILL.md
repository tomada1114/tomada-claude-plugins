---
name: code-analyzer
description: Review code structure, complexity, and security patterns under a hard read-only guarantee — the editing tools are removed for the turn, so findings can be produced against an untrusted or production checkout without any risk of a write. Use when auditing an unfamiliar codebase, scoping a refactor, or reviewing a branch you must not modify.
allowed-tools: Read, Grep, Glob
disallowed-tools: Write, Edit, NotebookEdit
---

# Code Analyzer

Demonstrates the two tool fields, which do opposite things and are constantly confused.

## The two fields

- `allowed-tools: Read, Grep, Glob` — **pre-approval**. These run without a permission prompt for the rest of the turn. It grants; it does not restrict.
- `disallowed-tools: Write, Edit, NotebookEdit` — **removal**. These leave Claude's pool while the skill is active. This is the line that makes the skill read-only.

Listing only `allowed-tools` would leave `Write` and `Edit` fully available, merely prompting for permission as usual. Pick the fields by intent: pre-approve the tools the task hammers, remove the tools whose absence is the guarantee you are selling.

Both fields clear when the user sends the next message. For a restriction that outlives the turn, use deny rules in permission settings.

## Procedure

Glob to scope, Grep to locate, Read to confirm. Report each finding as `<file>:<line>` plus the specific change that resolves it. Where a fix is non-obvious, write the replacement inline in the report — the whole value here is that the user applies it, not you.
