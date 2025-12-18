# Skill Development Guide

This guide covers the recommended process for developing effective skills: evaluation-driven development, iterative refinement with Claude, workflow patterns, and multi-model testing.

## Contents

- [Evaluation-Driven Development](#evaluation-driven-development)
- [Iterative Development with Claude](#iterative-development-with-claude)
- [Workflow Patterns](#workflow-patterns)
- [Multi-Model Testing](#multi-model-testing)
- [Observing Skill Usage](#observing-skill-usage)

---

## Evaluation-Driven Development

**Create evaluations BEFORE writing extensive documentation.** This ensures your skill solves real problems rather than documenting imagined ones.

### The Process

```
1. Identify gaps     → Run Claude without a skill, document failures
2. Create evaluations → Build 3+ scenarios that test these gaps
3. Establish baseline → Measure performance without the skill
4. Write minimal content → Just enough to pass evaluations
5. Iterate           → Execute evaluations, compare, refine
```

### Step 1: Identify Gaps

Run Claude on representative tasks **without** a skill. Document:
- What context did you have to provide repeatedly?
- Where did Claude fail or produce suboptimal results?
- What domain knowledge was missing?

**Example**: Working on BigQuery analysis, you might notice:
- You had to explain table schemas repeatedly
- Claude forgot to filter out test accounts
- You kept providing the same SQL patterns

### Step 2: Create Evaluations

Build at least 3 scenarios that test the identified gaps:

```json
{
  "skills": ["bigquery-analysis"],
  "query": "Generate a quarterly revenue report for Q4 2024",
  "files": ["schemas/revenue.json"],
  "expected_behavior": [
    "Uses the correct revenue table (billing.transactions)",
    "Filters out test accounts (account_type != 'test')",
    "Groups by quarter correctly",
    "Includes comparison to previous quarter"
  ]
}
```

### Step 3: Establish Baseline

Measure Claude's performance **without** the skill:
- How many expected behaviors does it achieve?
- What information does it lack?
- Where does it make mistakes?

This baseline is your comparison point.

### Step 4: Write Minimal Content

Create **just enough** skill content to pass evaluations:
- Don't anticipate every possible scenario
- Focus on the documented gaps
- Keep it concise

### Step 5: Iterate

```
Run evaluation → Compare to baseline → Identify remaining gaps → Update skill → Repeat
```

### Why This Works

- **Solves real problems**: You're addressing actual failures, not imagined ones
- **Prevents bloat**: You only add content that's proven necessary
- **Measurable improvement**: You can quantify the skill's value
- **Focused effort**: No time wasted on unused documentation

---

## Iterative Development with Claude

The most effective skill development involves Claude itself. Use two instances:

- **Claude A** (Designer): Helps create and refine the skill
- **Claude B** (Tester): Uses the skill in real tasks

### Creating a New Skill

#### Step 1: Complete a Task Without a Skill

Work through a problem with Claude A using normal prompting:

```
You: "Help me analyze our BigQuery sales data"
Claude A: "I'll need some information about your schema..."
You: [Provides table names, field definitions, filtering rules]
```

**Notice what you repeatedly provide** - this becomes skill content.

#### Step 2: Identify the Reusable Pattern

After completing the task, ask yourself:
- What context did I provide that would be useful for similar tasks?
- What rules or conventions did I explain?
- What patterns did we establish?

#### Step 3: Ask Claude A to Create a Skill

```
You: "Create a skill that captures this BigQuery analysis pattern we just used.
      Include the table schemas, naming conventions, and the rule about
      filtering test accounts."
```

Claude understands skill format natively - no special prompts needed.

#### Step 4: Review for Conciseness

Check that Claude A hasn't over-explained:

```
You: "Remove the explanation about what win rate means - Claude already knows that."
```

#### Step 5: Improve Information Architecture

```
You: "Organize this so the table schema is in a separate reference file.
      We might add more tables later."
```

#### Step 6: Test with Claude B

Use the skill with a **fresh Claude instance** on related tasks:
- Does Claude B find the right information?
- Does it apply rules correctly?
- Does it handle the task successfully?

#### Step 7: Iterate Based on Observation

If Claude B struggles:

```
You (to Claude A): "When Claude used this skill, it forgot to filter by date
                    for Q4. Should we add a section about date filtering patterns?"
```

### Iterating on Existing Skills

The same pattern continues for improvements:

1. **Use the skill in real workflows** with Claude B
2. **Observe behavior**: Note struggles, successes, unexpected choices
3. **Return to Claude A**: Share observations and ask for improvements
4. **Apply and test**: Update skill, test again with Claude B
5. **Repeat**: Continue the observe-refine-test cycle

### Example Observation

```
"When I asked Claude B for a regional sales report, it wrote the query
but forgot to filter out test accounts, even though the skill mentions
this rule."
```

Claude A might suggest:
- Making the rule more prominent
- Using stronger language ("MUST filter" instead of "always filter")
- Adding it to a checklist at the top

### Gathering Team Feedback

1. Share skills with teammates
2. Ask: Does it activate when expected? Are instructions clear?
3. Incorporate feedback to address blind spots

### Why This Works

- **Claude A understands agent needs**: It knows what information agents require
- **You provide domain expertise**: You know the actual requirements
- **Claude B reveals gaps**: Real usage exposes missing information
- **Iterative refinement**: Improves based on behavior, not assumptions

---

## Workflow Patterns

For complex tasks, use structured workflows with checklists and feedback loops.

### Checklist Pattern

Provide a checklist that Claude can copy and track:

````markdown
## Form Processing Workflow

Copy this checklist and track your progress:

```
Task Progress:
- [ ] Step 1: Analyze the form
- [ ] Step 2: Create field mapping
- [ ] Step 3: Validate mapping
- [ ] Step 4: Fill the form
- [ ] Step 5: Verify output
```

**Step 1: Analyze the form**

Run: `python scripts/analyze_form.py input.pdf`

**Step 2: Create field mapping**

Edit `fields.json` to add values for each field.

[... continue for each step ...]
````

**Benefits**:
- Prevents skipping critical steps
- Provides visibility into progress
- Works for both code and non-code tasks

### Feedback Loop Pattern

The validate → fix → repeat pattern catches errors early:

````markdown
## Document Editing Process

1. Make your edits
2. **Validate immediately**: `python scripts/validate.py`
3. If validation fails:
   - Review the error message
   - Fix the issues
   - Run validation again
4. **Only proceed when validation passes**
5. Finalize output
````

### Research Synthesis Workflow (Non-code)

````markdown
## Research Synthesis

Copy this checklist:

```
Research Progress:
- [ ] Step 1: Read all source documents
- [ ] Step 2: Identify key themes
- [ ] Step 3: Cross-reference claims
- [ ] Step 4: Create structured summary
- [ ] Step 5: Verify citations
```

**Step 1: Read all source documents**

Review each document. Note main arguments and supporting evidence.

**Step 2: Identify key themes**

Look for patterns. What themes repeat? Where do sources agree or disagree?

**Step 3: Cross-reference claims**

For each major claim, verify it appears in source material.

**Step 4: Create structured summary**

Organize findings by theme:
- Main claim
- Supporting evidence
- Conflicting viewpoints (if any)

**Step 5: Verify citations**

Check every claim references the correct source. If incomplete, return to Step 3.
````

### Conditional Workflow Pattern

Guide Claude through decision points:

```markdown
## Document Modification

1. Determine the modification type:

   **Creating new content?** → Follow "Creation workflow" below
   **Editing existing content?** → Follow "Editing workflow" below

2. Creation workflow:
   - Use docx-js library
   - Build document from scratch
   - Export to .docx format

3. Editing workflow:
   - Unpack existing document
   - Modify XML directly
   - Validate after each change
   - Repack when complete
```

### When to Use Workflows

- Multi-step processes with dependencies
- Operations where order matters
- Tasks with validation requirements
- Processes that benefit from progress tracking

---

## Multi-Model Testing

Skills act as additions to models, so effectiveness depends on the underlying model.

### Testing Considerations by Model

| Model | Consideration | Question to Ask |
|-------|--------------|-----------------|
| **Haiku** | Fast, economical | Does the skill provide enough guidance? |
| **Sonnet** | Balanced | Is the skill clear and efficient? |
| **Opus** | Powerful reasoning | Does the skill avoid over-explaining? |

### Model-Specific Behavior

**What works for Opus might need more detail for Haiku.**

```
Opus:   "Analyze the code structure" → Works well
Haiku:  "Analyze the code structure" → May need more specific steps
```

### Testing Process

1. **Test with your target model first**
2. **Then test with other models you might use**
3. **Adjust instructions to work across models**

### Aim for Universal Instructions

If you plan to use the skill across multiple models:
- Don't over-explain for Opus (wastes tokens)
- Don't under-explain for Haiku (causes failures)
- Find the balance that works for all

---

## Observing Skill Usage

As you iterate, pay attention to how Claude actually uses skills:

### What to Watch For

| Observation | What It Means | Action |
|------------|---------------|--------|
| **Unexpected file order** | Structure isn't intuitive | Reorganize or add clearer navigation |
| **Missed references** | Links aren't prominent enough | Make references more explicit |
| **Repeated file reads** | Content should be in SKILL.md | Move important content up |
| **Ignored files** | Content is unnecessary | Remove or improve signaling |

### Key Insight

**The `name` and `description` in metadata are critical.** Claude uses these to decide whether to trigger the skill. Make sure they clearly describe:
- What the skill does
- When it should be used

### Iterate Based on Behavior

Don't assume - observe:
- Watch how Claude navigates the skill
- Note where it succeeds and struggles
- Make changes based on real usage patterns

---

## Summary Checklist

Before considering a skill complete:

### Development Process
- [ ] Identified gaps by working without the skill first
- [ ] Created 3+ evaluation scenarios
- [ ] Established baseline performance
- [ ] Used Claude A (designer) and Claude B (tester) pattern
- [ ] Iterated based on observed behavior

### Workflows
- [ ] Complex tasks have step-by-step workflows
- [ ] Checklists provided for multi-step processes
- [ ] Feedback loops included for validation

### Testing
- [ ] Tested with target model
- [ ] Tested with other models you'll use
- [ ] Instructions work across model capabilities

### Observation
- [ ] Watched how Claude navigates the skill
- [ ] Adjusted based on actual usage patterns
- [ ] Team feedback incorporated (if applicable)
