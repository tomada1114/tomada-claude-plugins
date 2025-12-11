---
name: code-analyzer
description: Analyze code structure, patterns, and complexity without making modifications. Use when reviewing code, planning refactoring, or conducting read-only code analysis.
allowed-tools: Read, Grep, Glob
---

# Code Analyzer (Read-Only)

This skill analyzes code structure and patterns in a **read-only** mode. It demonstrates the use of `allowed-tools` to restrict Claude's capabilities to only reading and searching, preventing any file modifications.

## When to Use This Skill

Use this skill when:
- Reviewing code before refactoring
- Analyzing code complexity and structure
- Searching for patterns or anti-patterns
- Conducting security reviews (read-only)
- Learning about a new codebase
- Documenting existing code

## Tool Restrictions

This skill uses `allowed-tools: Read, Grep, Glob` which means Claude can **only**:
- **Read**: View file contents
- **Grep**: Search for patterns in code
- **Glob**: Find files by pattern

Claude **cannot**:
- Edit files
- Write new files
- Execute bash commands
- Make any modifications

This ensures safe, read-only analysis without risk of accidental changes.

## Analysis Capabilities

### 1. Code Structure Analysis
- File and directory organization
- Module dependencies
- Import/export patterns
- Class hierarchies

### 2. Complexity Analysis
- Function length
- Nesting depth
- Cyclomatic complexity (estimated)
- Code duplication

### 3. Pattern Detection
- Design patterns used
- Common anti-patterns
- Naming conventions
- Code smells

### 4. Security Review
- Potential security issues
- Hardcoded secrets (patterns)
- SQL injection risks
- XSS vulnerabilities

## Instructions

When analyzing code, I will:

1. **Understand the request**: Clarify what you want analyzed
2. **Explore the codebase**: Use Glob to find relevant files
3. **Search for patterns**: Use Grep to find specific patterns
4. **Read files**: Use Read to examine file contents
5. **Provide analysis**: Deliver findings with recommendations

## Examples

### Example 1: Find Long Functions

**Request**: "Find all functions longer than 50 lines"

**Analysis Process**:
```
1. Use Glob to find all TypeScript files: **/*.ts
2. Use Grep to find function definitions
3. Read files with many functions
4. Analyze and report functions > 50 lines
```

**Report**:
```
=== Functions Longer Than 50 Lines ===

1. src/services/auth.ts:15 - authenticateUser() (78 lines)
   - Consider breaking into smaller functions
   - Complexity: High
   - Suggestion: Extract validation, token generation, and logging

2. src/utils/data-processor.ts:42 - processData() (65 lines)
   - Multiple responsibilities detected
   - Suggestion: Extract data validation and transformation

Recommendations:
- Apply Single Responsibility Principle
- Extract helper functions for each logical step
- Consider using strategy pattern for processing logic
```

### Example 2: Analyze Import Structure

**Request**: "Analyze how modules are importing each other"

**Analysis Process**:
```
1. Glob: Find all source files
2. Grep: Search for import statements
3. Read: Examine import patterns
4. Map: Create dependency graph
```

**Report**:
```
=== Import Analysis ===

Circular Dependencies Detected:
- auth.ts → user.ts → auth.ts
- services/api.ts → models/user.ts → services/api.ts

Import Patterns:
✓ Good: Barrel exports in index.ts files
✗ Issue: Deep imports bypassing index files
✗ Issue: 15 files importing from utils (god module)

Recommendations:
1. Break circular dependencies:
   - Extract shared types to types.ts
   - Use dependency injection

2. Refactor utils module:
   - Split into focused modules (date-utils, string-utils, etc.)
   - Use barrel exports for cleaner imports

3. Enforce import rules:
   - Always import from index files
   - Consider using path aliases (@/components, @/utils)
```

### Example 3: Security Pattern Search

**Request**: "Check for potential security issues"

**Analysis Process**:
```
1. Grep: Search for common security anti-patterns
   - Hardcoded credentials
   - SQL string concatenation
   - eval() usage
   - Unsafe regex

2. Read: Examine suspicious files
3. Report: List findings with severity
```

**Report**:
```
=== Security Analysis ===

🔴 HIGH SEVERITY:
- src/db/queries.ts:45 - Potential SQL injection
  `query = "SELECT * FROM users WHERE id = " + userId`
  Recommendation: Use parameterized queries

- config/secrets.ts:12 - Hardcoded API key
  `const API_KEY = "sk_live_abc123..."`
  Recommendation: Use environment variables

🟡 MEDIUM SEVERITY:
- src/utils/validator.ts:23 - ReDoS vulnerability
  Complex regex without timeout
  Recommendation: Simplify regex or add timeout

🟢 LOW SEVERITY:
- Multiple files using console.log (information disclosure)
  Recommendation: Remove in production build
```

### Example 4: Code Duplication Detection

**Request**: "Find duplicated code blocks"

**Analysis Process**:
```
1. Glob: Find all files of specific type
2. Read: Examine file contents
3. Analyze: Identify similar patterns
4. Report: List duplicates with refactoring suggestions
```

**Report**:
```
=== Code Duplication Analysis ===

Similar Code Blocks Found:

1. User Authentication Flow (3 occurrences)
   - src/routes/login.ts:34-52
   - src/routes/register.ts:28-46
   - src/routes/reset-password.ts:19-37

   Similarity: 85%
   Suggestion: Extract to shared `authenticateAndGenerateToken()` function

2. Data Validation Pattern (5 occurrences)
   - src/validators/user.ts:15-30
   - src/validators/product.ts:22-37
   - src/validators/order.ts:18-33
   [...]

   Similarity: 92%
   Suggestion: Create generic validator factory

Potential Savings:
- ~200 lines of duplicated code could be reduced to ~50 lines
- Improved maintainability
- Reduced bug surface area
```

## Best Practices

### For Users:
- Be specific about what you want analyzed
- Provide context about the codebase
- Specify if you want recommendations or just findings
- Indicate priority areas to focus on

### Analysis Guidelines:
- Always explain the methodology
- Provide actionable recommendations
- Include code examples for suggestions
- Prioritize findings by severity/impact
- Consider the project's existing patterns

## Read-Only Benefits

The `allowed-tools` restriction provides:

1. **Safety**: No risk of accidental file modifications
2. **Confidence**: You can review suggestions before implementing
3. **Audit Trail**: All changes require explicit user action
4. **Collaboration**: Safe for exploring unfamiliar codebases
5. **Security**: Ideal for sensitive codebases

## AI Assistant Instructions

When this skill is activated:

### Analysis Workflow:

1. **Clarify Scope**:
   - What type of analysis? (structure, complexity, security, patterns)
   - Which files/directories to analyze?
   - Any specific concerns or focus areas?

2. **Explore Systematically**:
   - Use Glob to find relevant files
   - Use Grep to search for patterns
   - Read files to examine details
   - Never attempt to modify anything

3. **Analyze Thoroughly**:
   - Identify issues, patterns, or opportunities
   - Categorize findings by type and severity
   - Consider context and existing patterns

4. **Report Clearly**:
   - Start with summary
   - Organize findings by category/severity
   - Provide specific file locations and line numbers
   - Include actionable recommendations
   - Show code examples for suggestions

### Always:
- Use file paths with line numbers (e.g., `src/utils/auth.ts:45`)
- Explain why something is an issue
- Provide concrete examples
- Suggest specific refactorings
- Respect existing code style and patterns

### Never:
- Attempt to edit or write files (you can't with this skill)
- Make vague recommendations
- Ignore context
- Criticize without constructive suggestions
- Assume bad intent (explain trade-offs instead)

### Output Format:

```
=== [Analysis Type] ===

[Summary paragraph]

[Findings organized by category/severity]

🔴 Critical Issues:
- [Issue with location and recommendation]

🟡 Improvements:
- [Suggestion with location and recommendation]

🟢 Observations:
- [Notes and patterns]

Recommendations:
1. [Prioritized action item]
2. [Next priority]
3. [...]
```

## When NOT to Use This Skill

Don't use this read-only skill if you need to:
- Actually implement fixes (use regular mode)
- Run tests or execute code
- Generate new files
- Make modifications

For those tasks, use Claude Code's regular capabilities instead.

## Related Skills

This skill works well with:
- Code review skills (for implementation)
- Testing skills (for validation)
- Refactoring skills (for making changes)

First analyze with this skill (read-only), then switch to other skills for implementation.
