# Troubleshooting Guide

Common issues with Claude Code skills and how to fix them.

## Tier 1 vs Tier 2 Field Validation

If using the official `package_skill.py` validator, only Tier 1 fields (name, description, license, allowed-tools, metadata, compatibility) pass validation. Tier 2 fields (context, agent, disable-model-invocation, user-invocable, model, hooks, argument-hint) are Claude Code extensions and will cause validation errors.

## Skill Not Activating

### Diagnosis Steps

1. **Check Description**: Does it include keywords you're using? Ensure "Use when..." clause exists.

2. **Verify Name Format**:
   ```bash
   echo "my-skill-name" | grep -E '^[a-z0-9-]+$'
   ```

3. **Validate YAML**:
   ```yaml
   ---
   name: skill-name   # Space after colon required
   description: Text  # Space after colon required
   ---
   ```

4. **Check File Location**:
   ```bash
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

1. **Make Description More Specific**:
   ```yaml
   # Bad
   description: Helps with testing
   # Good
   description: Generate Jest tests for React components with hooks and async testing. Use when testing React hooks, async components, or writing Jest tests.
   ```

2. **Add Negative Triggers** in the skill body:
   ```markdown
   Don't use for:
   - Python testing (use pytest-skill instead)
   - E2E testing (use e2e-skill instead)
   ```

3. **Differentiate Similar Skills** -- use distinct technology names, action verbs, and "Use when..." clauses per skill to avoid overlap.

## Files Not Loading

1. **Use bare filenames** (not `./` or absolute paths):
   ```markdown
   # Wrong
   See [reference](./reference.md)
   # Correct
   See [reference](reference.md)
   ```

2. **Verify file exists and is readable**:
   ```bash
   ls -la ~/.claude/skills/my-skill/
   chmod 644 ~/.claude/skills/my-skill/*.md
   ```

## Tool Restrictions Not Working

```yaml
# Wrong
allowed-tools: [Read, Grep, Glob]
allowed_tools: Read, Grep, Glob

# Correct
allowed-tools: Read, Grep, Glob
```

### Valid Tool Names

`Read`, `Write`, `Edit`, `Grep`, `Glob`, `Bash`, `WebFetch`, `WebSearch`, `Task`, `Skill`, `TaskCreate`, `TaskUpdate`, `TaskList`, `TaskGet`, `AskUserQuestion`, `NotebookEdit`

## Performance Issues

1. **SKILL.md too large**: Keep under 500 lines. Move details to `reference.md`, examples to `examples.md`.
2. **Too many skills loading**: Make descriptions more specific, use `disable-model-invocation: true` for timing-sensitive skills, split monolithic skills.
3. **Heavy computation**: Offload to scripts (`python scripts/validate.py $ARGUMENTS`).

## YAML Validation Errors

```yaml
# Missing space after colon
name:skill-name          # Wrong
name: skill-name         # Correct

# Unquoted special characters
description: Use for: testing & debugging           # Wrong
description: "Use for: testing & debugging"         # Correct

# Tabs instead of spaces
name:	skill-name       # Wrong (tab character)
name: skill-name         # Correct (spaces only)
```

## Debugging Checklist

- [ ] SKILL.md exists in correct location
- [ ] YAML frontmatter is valid
- [ ] Name uses lowercase-with-hyphens format
- [ ] Description includes specific trigger keywords
- [ ] Description includes "Use when..." clause
- [ ] Referenced files exist and are readable
- [ ] allowed-tools syntax is correct (if used)
- [ ] No conflicting skills with similar descriptions
- [ ] File size is reasonable (< 500 lines for SKILL.md)
- [ ] Tier 2 fields excluded if running official validator
