# Troubleshooting Guide

This document helps diagnose and fix common issues with Claude Code skills.

## Skill Not Activating

### Diagnosis Steps

1. **Check Description**:
   - Does description include keywords you're using?
   - Add more trigger keywords if needed
   - Ensure "Use when..." clause exists

2. **Verify Name Format**:
   ```bash
   # Ensure lowercase with hyphens only
   echo "my-skill-name" | grep -E '^[a-z0-9-]+$'
   ```

3. **Validate YAML**:
   ```yaml
   # Check for proper formatting
   ---
   name: skill-name   # Space after colon required
   description: Text  # Space after colon required
   ---
   ```

4. **Check File Location**:
   ```bash
   # Verify file exists
   ls -la ~/.claude/skills/skill-name/SKILL.md
   ls -la .claude/skills/skill-name/SKILL.md
   ```

5. **Test Manually**:
   ```
   Ask Claude: "What skills are available?"
   Ask Claude: "Should you use [skill-name] for this task?"
   ```

### Common Causes

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| Never activates | Description too vague | Add specific keywords and "Use when..." |
| Claude doesn't know about it | Wrong directory | Move to correct skills/ location |
| YAML errors | Bad formatting | Check indentation and colons |
| Name not recognized | Invalid characters | Use lowercase-with-hyphens only |

## Skill Activates at Wrong Times

### Solutions

1. **Make Description More Specific**:
   ```yaml
   # ✗ Too broad
   description: Helps with testing

   # ✅ Specific
   description: Generate Jest tests for React components with hooks and async testing. Use when testing React hooks, async components, or writing Jest tests.
   ```

2. **Add Negative Triggers**:
   ```markdown
   ## When NOT to Use This Skill

   Don't use for:
   - Python testing (use pytest-skill instead)
   - E2E testing (use e2e-skill instead)
   ```

3. **Narrow Scope**:
   ```yaml
   # ✗ Too general
   description: Code analysis and refactoring

   # ✅ Narrow scope
   description: Analyze TypeScript code complexity and suggest refactoring for functions > 50 lines. Use when reviewing TypeScript code or refactoring complex functions.
   ```

### Differentiate Similar Skills

When you have multiple related skills:

```yaml
# Skill 1: Unit testing
description: Generate unit tests for individual functions and modules with mocking. Use when writing unit tests, testing isolated functions, or mocking dependencies.

# Skill 2: Integration testing
description: Generate integration tests for API endpoints and database operations. Use when testing APIs, database queries, or service interactions.

# Skill 3: E2E testing
description: Generate Playwright E2E tests for user flows and UI interactions. Use when testing user journeys, browser interactions, or visual workflows.
```

## Files Not Loading

### Check References

1. **Relative Path Issues**:
   ```markdown
   # ✗ Wrong
   See [reference](./reference.md)
   See [reference](/absolute/path/reference.md)

   # ✅ Correct
   See [reference](reference.md)
   ```

2. **File Exists**:
   ```bash
   ls -la ~/.claude/skills/my-skill/
   # Should show reference.md, templates/, etc.
   ```

3. **File Permissions**:
   ```bash
   chmod 644 ~/.claude/skills/my-skill/*.md
   ```

## Tool Restrictions Not Working

### Verify Syntax

```yaml
# ✗ Wrong
allowed-tools: [Read, Grep, Glob]
allowed_tools: Read, Grep, Glob

# ✅ Correct
allowed-tools: Read, Grep, Glob
```

### Valid Tool Names

Only these exact names are valid:
- `Read`, `Write`, `Edit`
- `Grep`, `Glob`
- `Bash`
- `WebFetch`, `WebSearch`
- `Task`, `Skill`
- `TaskCreate`, `TaskUpdate`, `TaskList`, `TaskGet`
- `AskUserQuestion`
- `NotebookEdit`

## Performance Issues

### Skill Too Slow

1. **Check SKILL.md size**:
   ```bash
   wc -l ~/.claude/skills/my-skill/SKILL.md
   # Should be < 500 lines
   ```

2. **Split large skills**:
   - Move detailed reference to `reference.md`
   - Move examples to `examples.md`
   - Keep SKILL.md focused

3. **Use scripts for heavy computation**:
   ```markdown
   Run validation script:
   ```bash
   python scripts/validate.py $ARGUMENTS
   ```
   ```

### Too Many Skills Loading

1. **Make descriptions more specific** to reduce false activations
2. **Use `disable-model-invocation: true`** for timing-sensitive skills
3. **Split monolithic skills** into focused ones

## YAML Validation Errors

### Common YAML Mistakes

```yaml
# ✗ Missing space after colon
name:skill-name

# ✅ Correct
name: skill-name
```

```yaml
# ✗ Unquoted special characters
description: Use for: testing & debugging

# ✅ Quote if using special characters
description: "Use for: testing & debugging"
```

```yaml
# ✗ Tabs instead of spaces
---
name:	skill-name  # Tab character

# ✅ Use spaces only
---
name: skill-name
```

### Online Validation

Use an online YAML validator to check syntax:
1. Copy your YAML frontmatter (including `---` markers)
2. Paste into a YAML validator
3. Fix any reported errors

## Debugging Checklist

When a skill isn't working as expected:

- [ ] SKILL.md exists in correct location
- [ ] YAML frontmatter is valid (test with validator)
- [ ] Name uses lowercase-with-hyphens format
- [ ] Description includes specific trigger keywords
- [ ] Description includes "Use when..." clause
- [ ] Referenced files exist and are readable
- [ ] allowed-tools syntax is correct (if used)
- [ ] No conflicting skills with similar descriptions
- [ ] File size is reasonable (< 500 lines for SKILL.md)

## Getting Help

If issues persist:

1. Check Claude Code documentation
2. Verify with `/skills` command to see loaded skills
3. Ask Claude: "Why didn't you use the [skill-name] skill?"
4. Test activation with explicit prompts containing trigger keywords
