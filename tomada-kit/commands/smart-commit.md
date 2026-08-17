---
description: "Analyze the working tree, group related changes, and create commits at a sensible granularity"
---

# Smart Commit Command

Analyze the current changes, group related ones together, and create appropriately scoped commits.

## Task

1. **Survey the changes**
   - `git status` for the changed files
   - `git diff` for staged/unstaged content
   - If anything is already staged, handle it first
   - **Exclude only secret-bearing files; treat everything else as committable**

2. **Group the changes**
   Group by content and file type, using these rules:

   - **Tests** (`__tests__/`, `.test.ts`, `.test.tsx`):
     - Prefix: `test:`
     - New tests → "test: add ..."
     - Test fixes → "test: fix ..."
     - Test improvements → "test: improve ..."

   - **Documentation** (`.md`, `docs/`, `CLAUDE.md`, `README.md`):
     - Prefix: `docs:`
     - New → "docs: add ..."
     - Updated → "docs: update ..."

   - **Configuration** (`.json`, `.config.js`, `tailwind.config.js`, `.claude/`):
     - Prefix: `chore:`
     - "chore: update ..." or "chore: configure ..."

   - **UI / components** (`src/components/`, `src/app/`, `.tsx`):
     - New feature → `feat:` (add, implement)
     - Change to existing code → `refactor:` (update, improve, refactor)
     - Bug fix → `fix:` (fix)

   - **Business logic** (`src/domain/`, `src/application/`, `src/infrastructure/`):
     - New feature → `feat:`
     - Refactoring → `refactor:`
     - Bug fix → `fix:`

   - **Styles / design** (`src/ui/`, `tokens.ts`, style-related changes):
     - `style:`, or `feat:` for design-system updates

3. **Commit and push**
   For each group:
   - Stage the related files with `git add`
   - Write a short, clear commit message (English, one line)
   - Describe *what* changed, not *why*
   - Commit with the one-line form `git commit -m "message"` (no HEREDOC)
   - Run `git push`

4. **Final check**
   - After every commit, run `git status` to see what remains
   - If files are still uncommitted, explain why (secret-bearing files are the expected case)

## Important notes

- **One group = one commit**: related changes belong in a single commit
- **Atomic commits**: each commit must stand on its own
- **Secret check**: never commit these files
  - Environment files such as `.env`, `.env.local`, `.env.production`
  - Explicit secret files such as `**/credentials.json`, `**/secrets.json`, `**/private-key.json`
  - Filename patterns implying secrets, such as `**/*password*`, `**/*secret*`, `**/*key*.pem`
- **Default policy**: everything other than the secret files above **is committable**
  - Configuration (`.claude/`, `*.json`, `*.md`)
  - Documentation (`*.md`, `CLAUDE.md`, `README.md`)
  - Source code (`*.ts`, `*.tsx`, `*.js`, `*.jsx`)
  - Tests (`*.test.*`, `__tests__/`)
  - Commit work-in-progress files freely
- **Report state first**: show the current branch and change set before doing anything
- **Error handling**: if a commit fails, explain why and move on to the next group

## Example

```bash
# Usage
/smart-commit

# Sample run:
# Group 1: test: add tests for design-system components
#   - src/components/ui/list-item/__tests__/list-item.test.tsx
#   - src/components/ui/typography/__tests__/typography.test.tsx
#
# Group 2: feat: improve design-system components
#   - src/components/ui/list-item/index.tsx
#   - src/components/ui/typography/index.tsx
#
# Group 3: chore: update design tokens and Tailwind config
#   - src/ui/tokens.ts
#   - tailwind.config.js
```

## Getting started

Follow the rules above: analyze the changes, group them, and create the commits.

## Note

- Commit files even when they look like work in progress.
