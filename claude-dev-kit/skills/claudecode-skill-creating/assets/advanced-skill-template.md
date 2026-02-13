---
name: advanced-skill-name
description: Comprehensive description including what it does, technologies involved, and when to use it. Use when [scenario 1], [scenario 2], or working with [tech1], [tech2], [tech3].
allowed-tools: Read, Grep, Glob, Write, Edit
# Tier 2 fields (Claude Code extensions, will fail official validator):
# disable-model-invocation: true
# user-invocable: false
# argument-hint: "[arg1] [arg2]"
# model: claude-opus-4-5-20251101
# context: fork
# agent: Explore
---

# Advanced Skill Name

Comprehensive introduction explaining the skill's purpose and what makes it different from simpler approaches.

**Don't use this skill for:**
- [When a simpler approach would work]
- [Scenarios better handled by another skill]

## Core Concepts

1. **Principle 1**: [Explanation]
2. **Principle 2**: [Explanation]
3. **Principle 3**: [Explanation]

### Architecture

```
[Diagram or description of how components work together]
```

## Prerequisites

- [Required knowledge or setup]
- [Required dependencies or tools]

## Instructions

### Basic Workflow

1. **Preparation**: [What to prepare and check]
2. **Analysis**: [What to analyze, patterns to look for]
3. **Implementation**: [What to implement, how to structure]
4. **Validation**: [How to test and verify]

### Advanced Usage

[More complex workflows or edge cases]

## Examples

### Example 1: Basic Scenario

**Context**: [Describe the scenario]

**Input**:
```[language]
// Starting code or data
```

**Process**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Output**:
```[language]
// Resulting code or data
```

---

### Example 2: Advanced Scenario

**Context**: [More complex scenario]

**Input**:
```[language]
// Complex starting point
```

**Process**:
1. [Advanced step 1]
2. [Advanced step 2]
3. [Advanced step 3]

**Output**:
```[language]
// Complex result
```

**Trade-offs**: [Discuss alternatives and why this was chosen]

## Best Practices

**Always**:
- [Critical best practice 1]
- [Critical best practice 2]
- [Critical best practice 3]

**Never**:
- [Anti-pattern 1 and why it's bad]
- [Anti-pattern 2 and why it's bad]

## Common Patterns

### Pattern 1: [Pattern Name]

**Use when**: [Scenario]

```[language]
// Pattern template
```

### Pattern 2: [Another Pattern]

**Use when**: [Scenario]

```[language]
// Pattern template
```

## Troubleshooting

**[Common Problem 1]**: [Symptoms] -> [Solution steps]

**[Common Problem 2]**: [Symptoms] -> [Solution steps]

## Supporting Files

- **[reference.md](reference.md)**: Detailed reference and specifications
- **[examples.md](examples.md)**: Extended examples
- **[templates/](templates/)**: Reusable templates
- **[scripts/](scripts/)**: Utility scripts

## AI Assistant Instructions

When activated, assess complexity first:
- Basic use case: simplified workflow
- Advanced: full workflow
- Edge case: check troubleshooting first

Execution:
1. Gather context: [What to collect and examine]
2. Choose strategy: If [condition] use Pattern A, if [other condition] use Pattern B, if uncertain ask user
3. Implement following the chosen pattern
4. Validate against quality checks below

Quality checks before completing:
- [ ] [Domain-specific check 1]
- [ ] [Domain-specific check 2]
- [ ] Code follows project conventions
- [ ] Edge cases handled

Always: Explain approach before implementing. Highlight trade-offs. Reference supporting files.
Never: Implement without explaining. Skip error handling. Ignore existing patterns.
When uncertain: Present options with pros/cons. Suggest safest approach.
