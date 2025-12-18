# Context Efficiency Guide

This guide explains how to write skills that use context efficiently. Understanding these principles is essential for creating effective skills.

## Contents

- [The Three-Level Loading Model](#the-three-level-loading-model)
- [Core Principle: Concise is Key](#core-principle-concise-is-key)
- [Degrees of Freedom](#degrees-of-freedom)
- [Progressive Disclosure Patterns](#progressive-disclosure-patterns)
- [Script Efficiency](#script-efficiency)
- [Reference File Best Practices](#reference-file-best-practices)
- [Anti-Patterns to Avoid](#anti-patterns-to-avoid)

## The Three-Level Loading Model

Skills load content in three distinct levels, each with different timing and token costs:

### Level 1: Metadata (Always Loaded)

**Content**: YAML frontmatter (`name` and `description`)
**When**: At startup, injected into system prompt
**Token Cost**: ~100 tokens per skill

```yaml
---
name: pdf-processing
description: Extract text and tables from PDF files. Use when working with PDFs.
---
```

**Implication**: You can install many skills without context penalty. Only metadata is pre-loaded.

### Level 2: Instructions (Loaded When Triggered)

**Content**: SKILL.md body
**When**: When skill matches user's request
**Token Cost**: Should be under 5k tokens (< 500 lines)

```markdown
# PDF Processing

## Quick start
Use pdfplumber for text extraction...
```

**Implication**: Keep SKILL.md concise. Every token competes with conversation history.

### Level 3+: Resources (Loaded As Needed)

**Content**: Reference files, templates, scripts
**When**: Only when Claude needs them
**Token Cost**: Zero until accessed

```
pdf-skill/
├── SKILL.md          # Level 2: loaded when triggered
├── FORMS.md          # Level 3: loaded if form-filling needed
├── REFERENCE.md      # Level 3: loaded if API details needed
└── scripts/
    └── fill_form.py  # Level 3: executed, output only
```

**Implication**: Bundle comprehensive resources freely. No context penalty until used.

## Core Principle: Concise is Key

The context window is a shared resource. Your skill competes with:
- System prompt
- Conversation history
- Other skills' metadata
- User's actual request

### Default Assumption: Claude is Already Smart

**Challenge each piece of information:**
- "Does Claude really need this explanation?"
- "Can I assume Claude knows this?"
- "Does this paragraph justify its token cost?"

### Good vs Bad Examples

**Good (concise, ~50 tokens):**
```markdown
## Extract PDF text

Use pdfplumber:
\`\`\`python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
\`\`\`
```

**Bad (verbose, ~150 tokens):**
```markdown
## Extract PDF text

PDF (Portable Document Format) files are a common file format that contains
text, images, and other content. To extract text from a PDF, you'll need to
use a library. There are many libraries available for PDF processing, but we
recommend pdfplumber because it's easy to use and handles most cases well.
First, you'll need to install it using pip...
```

The concise version assumes Claude knows what PDFs are and how libraries work.

## Degrees of Freedom

Match the level of specificity to the task's fragility and variability.

### High Freedom (Text-based instructions)

**Use when**: Multiple approaches are valid, decisions depend on context

```markdown
## Code review process

1. Analyze the code structure and organization
2. Check for potential bugs or edge cases
3. Suggest improvements for readability
4. Verify adherence to project conventions
```

### Medium Freedom (Pseudocode or scripts with parameters)

**Use when**: A preferred pattern exists, some variation acceptable

```markdown
## Generate report

Use this template and customize as needed:
\`\`\`python
def generate_report(data, format="markdown", include_charts=True):
    # Process data
    # Generate output in specified format
\`\`\`
```

### Low Freedom (Specific scripts, few parameters)

**Use when**: Operations are fragile, consistency is critical

```markdown
## Database migration

Run exactly this script:
\`\`\`bash
python scripts/migrate.py --verify --backup
\`\`\`

Do not modify the command or add additional flags.
```

### Analogy: Robot on a Path

- **Narrow bridge with cliffs**: Only one safe way forward → Low freedom, specific guardrails
- **Open field with no hazards**: Many paths lead to success → High freedom, general direction

## Progressive Disclosure Patterns

### Pattern 1: High-level Guide with References

```markdown
# PDF Processing

## Quick start
[Essential code example]

## Advanced features
**Form filling**: See [FORMS.md](FORMS.md) for complete guide
**API reference**: See [REFERENCE.md](REFERENCE.md) for all methods
```

Claude loads FORMS.md or REFERENCE.md only when needed.

### Pattern 2: Domain-specific Organization

For skills with multiple domains, organize by domain:

```
bigquery-skill/
├── SKILL.md (overview and navigation)
└── reference/
    ├── finance.md (revenue, billing)
    ├── sales.md (pipeline, opportunities)
    └── product.md (usage analytics)
```

When user asks about sales, Claude loads only `reference/sales.md`.

### Pattern 3: Conditional Details

```markdown
# DOCX Processing

## Creating documents
Use docx-js for new documents. See [DOCX-JS.md](DOCX-JS.md).

## Editing documents
For simple edits, modify the XML directly.

**For tracked changes**: See [REDLINING.md](REDLINING.md)
**For OOXML details**: See [OOXML.md](OOXML.md)
```

## Script Efficiency

**Key insight**: When Claude executes a script, the script code itself does NOT enter the context window. Only the output consumes tokens.

### Example

```markdown
## Validate project

Run the validation script:
\`\`\`bash
python scripts/validate.py project/
\`\`\`
```

- The 200-line `validate.py` script: 0 tokens (not loaded)
- The script output "✓ Valid": ~10 tokens

### When to Use Scripts

**Use scripts for** (high token efficiency):
- Validation and checking
- Data transformation
- Setup and initialization
- Complex logic hard to generate reliably

**Don't use scripts for** (no efficiency gain):
- User-specific customization
- Content-based file editing
- Analysis and decision-making

## Reference File Best Practices

### Keep References One Level Deep

Claude may only partially read deeply nested files.

**Bad (too deep):**
```markdown
# SKILL.md
See [advanced.md](advanced.md)...

# advanced.md
See [details.md](details.md)...

# details.md
Here's the actual information...
```

**Good (one level deep):**
```markdown
# SKILL.md

**Basic usage**: [instructions here]
**Advanced features**: See [advanced.md](advanced.md)
**API reference**: See [reference.md](reference.md)
```

### Add Table of Contents to Long Files

For reference files longer than 100 lines, include a ToC at the top:

```markdown
# API Reference

## Contents
- Authentication and setup
- Core methods (create, read, update, delete)
- Advanced features
- Error handling
- Code examples

## Authentication and setup
...
```

Claude can see the full scope even when previewing with partial reads.

### Structure Files by Section

Make it easy for Claude to navigate directly to relevant sections:

```markdown
# Reference

## Section A
[Content for A]

## Section B
[Content for B]
```

In SKILL.md, link to specific sections:
```markdown
For details on A, see [reference.md#section-a](reference.md#section-a)
```

## Anti-Patterns to Avoid

### 1. Monolithic SKILL.md

**Problem**: 800-line SKILL.md with everything
**Solution**: Split into SKILL.md (< 500 lines) + reference files

### 2. Explaining What Claude Already Knows

**Problem**: "JSON is a data format that..."
**Solution**: Assume Claude's base knowledge. Only add task-specific context.

### 3. Deeply Nested References

**Problem**: SKILL.md → advanced.md → details.md → specifics.md
**Solution**: Keep references one level deep from SKILL.md

### 4. Regenerating Code Instead of Using Scripts

**Problem**: Asking Claude to write validation logic every time
**Solution**: Bundle a validation script that Claude executes

### 5. Loading Everything Upfront

**Problem**: Including comprehensive API docs in SKILL.md
**Solution**: Put API docs in reference.md, load on-demand

### 6. Offering Too Many Options

**Problem**: "You can use pypdf, or pdfplumber, or PyMuPDF, or pdf2image, or..."
**Solution**: Provide a default with escape hatch: "Use pdfplumber. For scanned PDFs, use pdf2image with pytesseract."

## Quick Reference: Token Cost by Content Type

| Content | When Loaded | Token Cost |
|---------|-------------|------------|
| YAML frontmatter | Always (startup) | ~100 tokens/skill |
| SKILL.md body | When triggered | < 5k tokens (target) |
| Reference files | When needed | 0 until accessed |
| Script code | Never (executed) | 0 (only output loaded) |
| Script output | After execution | Variable |

## Summary

1. **Leverage the 3-level loading**: Metadata always, SKILL.md on trigger, resources on demand
2. **Be concise**: Every token competes with conversation history
3. **Assume Claude is smart**: Don't explain what Claude already knows
4. **Use scripts for efficiency**: Script code never enters context
5. **Keep references shallow**: One level deep from SKILL.md
6. **Add ToC to long files**: Helps Claude navigate large references
7. **Match freedom to fragility**: Specific for fragile operations, flexible for variable tasks
