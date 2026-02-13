# Skills Structure and Patterns

This document covers directory structure, integration patterns, workflow patterns, and best practices for Claude Code skills.

## Table of Contents

- [Skill Content Types: Reference vs Task](#skill-content-types-reference-vs-task)
- [Skills vs Slash Commands](#skills-vs-slash-commands)
- [Three Storage Locations](#three-storage-locations)
- [Canonical Directory Structure](#canonical-directory-structure)
- [Progressive Disclosure Patterns](#progressive-disclosure-patterns)
- [Degrees of Freedom](#degrees-of-freedom)
- [Subagent Integration Patterns](#subagent-integration-patterns)
- [Workflow and Output Patterns](#workflow-and-output-patterns)
- [Token Efficiency](#token-efficiency)
- [Tool Restrictions](#tool-restrictions)

---

## Skill Content Types: Reference vs Task

### Reference Contents

Knowledge-oriented skills providing context and guidelines. The **task is determined by the main agent**, not the skill. Like a passive buff -- always active in background.

Examples: coding conventions, domain terminology, architecture guidelines.

Best pattern: Subagent + `skills:` field.

```yaml
# .claude/agents/code-reviewer.md
---
name: code-reviewer
tools: Read, Grep, Glob
skills: coding-standards, security-guidelines
---
```

### Task Contents

Action-oriented skills defining specific tasks. The **task is defined within SKILL.md itself**. Runs autonomously.

Examples: "Open a PR with this format", "Build and run tests", "Generate changelog".

Best pattern: `context: fork`.

```yaml
# .claude/skills/pr-opener/SKILL.md
---
name: pr-opener
context: fork
---
## Task
1. Get current branch diff
2. Generate PR title and description
3. Create PR using gh CLI
```

### Choosing the Right Pattern

| Content Type | What Determines Task | Best Pattern | `context: fork` |
|--------------|---------------------|--------------|-----------------|
| Reference | Main agent decides | Subagent + `skills:` | Not recommended |
| Task | SKILL.md defines | `context: fork` | Recommended |

Warning: `context: fork` with Reference Contents fails because the forked context needs explicit task instructions, not just guidelines.

---

## Skills vs Slash Commands

| Aspect | Slash Commands | Skills |
|--------|---------------|--------|
| Activation | Manual only (`/command`) | Auto or manual |
| Structure | Single .md file | Directory with resources |
| Tool restrictions | No | Yes (`allowed-tools`) |
| Invocation control | No | Yes (`disable-model-invocation`, `user-invocable`) |
| Fork context | No | Yes (`context: fork`) |
| Distribution | Via git | Via git or npm plugins |

Use **slash commands** for simple, frequent manual operations. Use **skills** for complex workflows, auto-discovery, tool restrictions, or bundled resources.

---

## Three Storage Locations

**1. Personal (`~/.claude/skills/`)** -- Available across all projects. Not shared with team. Use for personal preferences, experimental skills.

**2. Project (`.claude/skills/`)** -- Specific to one project, committed to git, shared with team. Use for team standards, project workflows.

**3. Plugin (via npm)** -- Under `node_modules/@company/claude-plugin/.claude-plugin/skills/`. Versioned and published. Use for org-wide standards.

---

## Canonical Directory Structure

```
skill-name/
├── SKILL.md              # Required. Instructions (<500 lines)
├── scripts/              # Executable code (Python/Bash)
├── references/           # Documentation loaded as needed
└── assets/               # Files used in output (templates, icons, fonts)
```

**scripts/**: Token-efficient -- code is NOT loaded into context, only execution output. Use for deterministic operations.

**references/**: Loaded only when Claude determines it is needed. Keep files one level deep. For files >100 lines, include a table of contents.

**assets/**: Templates, images, boilerplate copied or adapted for output. Not loaded until needed.

| Skill Size | Structure |
|------------|-----------|
| Simple (<200 lines) | `SKILL.md` only |
| Medium (200-500 lines) | `SKILL.md` + `references/` |
| Complex (>500 lines) | `SKILL.md` + `scripts/` + `references/` + `assets/` |

**Migration from legacy structure:** If a skill uses flat files like `reference.md`, `examples.md`, `templates/`, or `docs/`, consolidate into `scripts/` + `references/` + `assets/`. Move documentation to `references/`, templates to `assets/`, utility code to `scripts/`.

---

## Progressive Disclosure Patterns

Three levels of loading:

1. **Metadata** (name + description) -- always in context (~100 tokens)
2. **SKILL.md body** -- loaded when skill triggers (<5k tokens)
3. **Bundled resources** -- loaded on demand (scripts execute without loading)

### Pattern 1: High-Level Guide with References

SKILL.md contains the core workflow. Detailed specs live in `references/`.

```markdown
## Detailed Reference
For complete specification, see [references/spec.md](references/spec.md).
For extended examples, see [references/examples.md](references/examples.md).
```

### Pattern 2: Domain-Specific Organization

References organized by domain concern, not by file type.

```markdown
## References
- [references/api-contracts.md](references/api-contracts.md) -- API shape and validation
- [references/error-handling.md](references/error-handling.md) -- Error codes and recovery
- [references/deployment.md](references/deployment.md) -- Environment-specific config
```

### Pattern 3: Conditional Details

Branching logic loads different references based on context.

```markdown
## Framework Selection
- If React project: read [references/react-patterns.md](references/react-patterns.md)
- If Vue project: read [references/vue-patterns.md](references/vue-patterns.md)
- If Angular project: read [references/angular-patterns.md](references/angular-patterns.md)
```

Use progressive disclosure when SKILL.md exceeds 500 lines, extensive reference material exists, or multiple conditional paths need different instructions. Keep everything in SKILL.md when the skill is under 300 lines total.

---

## Degrees of Freedom

Match instruction specificity to the task's fragility. Open field = many routes (high freedom). Narrow bridge with cliffs = exact guardrails (low freedom).

### High Freedom: Text Instructions

Multiple valid approaches exist. Skill provides heuristics; Claude decides specifics.

```markdown
## Writing Style
Write in a conversational, engaging tone. Adapt formality to the target audience.
Use active voice. Prefer concrete examples over abstract descriptions.
```

### Medium Freedom: Pseudocode with Parameters

A preferred pattern exists but variation is acceptable. Skill defines structure; Claude fills details.

```markdown
## Component Generation
1. Create component at `src/components/{Name}/{Name}.tsx`
2. Extract props interface: `{Name}Props`
3. Add unit test at `src/components/{Name}/{Name}.test.tsx`
4. If >3 props, create separate `types.ts`
```

### Low Freedom: Specific Scripts

Fragile operations where deviations cause failures. Skill prescribes exact commands; Claude follows precisely.

```markdown
## OOXML Slide Generation
CRITICAL: OOXML is fragile. Do NOT improvise XML structure.
1. Run `python scripts/generate-slide.py --template assets/base-slide.xml --data input.json`
2. Validate: `python scripts/validate-ooxml.py --input output.pptx`
3. If validation fails, fix the specific XML element and re-validate
Never hand-write OOXML XML. Always use the generation script.
```

---

## Subagent Integration Patterns

Three patterns for combining skills with subagents. Choose based on whether the skill provides knowledge (reference) or tasks.

### Pattern 1: Subagent + `skills:` Field

Subagent receives knowledge from skills. Main agent determines the task.

```yaml
# .claude/agents/code-reviewer.md
---
name: code-reviewer
skills: coding-standards, security-guidelines
---
Review the provided code for quality and security issues.
```

Best for: Reference Contents.

### Pattern 2: `context: fork`

Skill runs in isolated forked context. SKILL.md content becomes the prompt.

```yaml
# .claude/skills/build-runner/SKILL.md
---
name: build-runner
context: fork
---
## Task
1. Run `npm run build`
2. Capture and categorize errors
3. Report results with suggested fixes
```

Best for: Task Contents.

### Pattern 3: `context: fork` + `agent:`

Combines custom subagent's system prompt with the skill's task definition.

```yaml
# .claude/skills/deep-analysis/SKILL.md
---
name: deep-analysis
context: fork
agent: module-builder
---
## Task
Analyze the auth module for security vulnerabilities.
```

Best for: Task Contents needing specialized agent behavior.

### Pattern Comparison

| Pattern | Context | Task Source | Best For |
|---------|---------|-------------|----------|
| Subagent + `skills:` | New | Main agent delegates | Reference Contents |
| `context: fork` | Forked | SKILL.md content | Task Contents |
| `context: fork` + `agent:` | Forked | SKILL.md + agent prompt | Task + custom behavior |

---

## Workflow and Output Patterns

### Sequential Workflow

Steps execute in fixed order, each depending on the previous.

```markdown
## Workflow
1. Gather requirements (ask clarifying questions)
2. Generate implementation plan
3. Write code following the plan
4. Run tests and fix failures
5. Create summary of changes
```

### Conditional Workflow (Decision Tree)

Different paths based on context or input.

```markdown
## Workflow
1. Detect project framework (check package.json, requirements.txt, go.mod)
2. Based on framework:
   - **Node.js**: Run `npm test`, check Jest/Vitest config
   - **Python**: Run `pytest`, check conftest.py
   - **Go**: Run `go test ./...`
3. Parse test output and report results
```

### Template Pattern

Use templates from `assets/` for consistent output. Distinguish strict sections (do not modify structure) from flexible sections (adapt to content).

```markdown
## Output Format
Use [assets/report-template.md](assets/report-template.md).
- Strict: header metadata, summary table, footer timestamp
- Flexible: analysis body, recommendations, code examples
```

### Examples Pattern (Input/Output Pairs)

Show expected transformation with concrete pairs. 2-3 examples are sufficient.

```markdown
**Input:** "Add error handling to the login function"
**Output:** Wrap in try/catch, add specific error types, return user-friendly messages

**Input:** "Optimize the search query"
**Output:** Add index on searched columns, cursor-based pagination, 5-min TTL cache
```

---

## Token Efficiency

### How Skill Loading Works

**Metadata (always):** ~50-100 tokens per skill. Even 50+ skills cost only a few thousand tokens.

**SKILL.md (on-demand):** Loads when activated. Target under 500 lines (~5k tokens).

**Referenced files:** Load only when needed. Scripts execute without loading source into context.

### One Skill = One Capability

Split monolithic skills. Only relevant context loads for each task.

```
# Bad: 2000-line monolith covering testing, docs, debugging
coding-assistant/SKILL.md

# Good: focused skills
testing-code/SKILL.md       # 300 lines
writing-documentation/SKILL.md  # 250 lines
debugging-errors/SKILL.md   # 200 lines
```

### What NOT to Include

- CHANGELOG.md, VERSION.md -- use git history
- Extensive inline docs -- move to `references/`
- Redundant examples -- 2-3 suffice
- Concepts Claude already knows

---

## Tool Restrictions

### Common Patterns

**Read-Only Analysis** -- `allowed-tools: Read, Grep, Glob`
Use for code analysis, security audits, complexity analysis.

**Documentation Only** -- `allowed-tools: Read, Grep, Glob, Write`
Use for generating docs without editing existing files.

**Safe Exploration** -- `allowed-tools: Read, Grep, Glob, WebSearch`
Use for exploring unfamiliar codebases with web research.

**Validation Only** -- `allowed-tools: Read, Bash`
Use for running validation scripts without file modifications.

### Available Tools

File ops: `Read`, `Write`, `Edit`, `Glob`, `NotebookEdit`. Search: `Grep`. Execution: `Bash`. Web: `WebFetch`, `WebSearch`. Agents: `Task`, `Skill`. Tasks: `TaskCreate`, `TaskUpdate`, `TaskList`, `TaskGet`. Utility: `AskUserQuestion`.
