---
name: bootstrapping-from-templates
description: >-
  Cut a new GitHub repository from one of the user's template repositories and bring it
  to a clean first commit: create it from the template (public by default) with
  scripts/create_from_template.py, clone it under ghq, follow the template's own
  starting-an-app procedure for the rename or bootstrap (a script, a just recipe, or a
  placeholder inventory), write AGENTS.md's Product section from signed-off
  requirements, copy kickoff drafts into docs/, run the template's checks, sync its
  labels, and push. Use when creating a repository from a template, running a
  template's bootstrap or rename, a placeholder survived a rename, or as stage 4 of
  kicking-off-apps.
argument-hint: "--template-path DIR | --template OWNER/NAME, --repo OWNER/NAME"
metadata:
  platforms: claude-code
---

# Bootstrapping From Templates

Each template repository already knows how it is turned into an app — its
`starting-an-app` skill names the rename mechanism, the placeholders, the order, and
which steps are a human's. This skill is the generic driver around that: it creates the
repository, gets a clone, and then executes the template's procedure rather than
improvising a rename. Improvising is what leaves `MyApp` in a bundle identifier or
deletes a CI job the template's own smoke test expects.

## Contract

**Input:** the template (a local checkout path or `OWNER/NAME`), the new `OWNER/NAME`,
visibility (public unless the user said otherwise), and the identity values the
template's bootstrap asks for — display name, slug, bundle identifier, author, email.
Author and email default to `git config user.name` / `user.email`. Optionally a drafts
directory and a draft→repository path map (from `kicking-off-apps`).

**Output:** a clone at `$(ghq root)/github.com/<owner>/<name>` whose `main` on GitHub
holds the bootstrap commit, plus a list of the human-only steps the template reserves.

**Authorization.** Creating the repository, pushing `main`, and syncing labels are
remote writes. Run them only after the user approved that list (the kickoff gate counts;
standalone, ask once with AskUserQuestion). A step the template marks as a human's —
typically the bootstrap itself — runs only when the approval names it.

## 1. Create and clone

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/create_from_template.py \
  --template-path <template-dir> --repo <owner>/<name> [--visibility private] --dry-run
```

Read the warnings: a local template ahead of its upstream means the new repository will
not contain those commits — ask whether to push the template first. Then run it again
without `--dry-run`, with `--json`, and keep the output (`kicking-off-apps` saves it as
`init.json`). It waits for GitHub to finish copying the template before cloning, and a
re-run reuses what already exists.

## 2. Follow the template's procedure

Read `<clone>/.claude/skills/starting-an-app/SKILL.md` (or the `.agents/skills/` copy)
by absolute path, plus every reference it marks REQUIRED for the rename. Execute its
order inside the clone, with these boundaries:

- **Do here:** toolchain setup it names (`mise trust`, the install recipe), the rename or
  bootstrap with the identity values, the leftover check it prescribes, and the
  **Product section** of `AGENTS.md` — the template's order puts it right after the
  rename, and its checks fail while a `TODO:` remains. Draft it only from the signed-off
  requirements: what the app is and for whom, the core interaction, the non-goals
  verbatim, and where the decisions are recorded (`docs/product/requirements.md`). Show
  the draft to the user before writing.
- **Leave for later stages:** the roadmap, the design lock and token edits, the app
  shape and sandbox ADRs, removing the sample code (`designing-architecture` and the
  issue backlog own these). Note each so nothing is dropped.
- **Collect, never run:** steps the template reserves for a human or an admin — branch
  ruleset, repository security settings, signing and release secrets. Return them as
  the human-only list.

No `starting-an-app` in the template: read `README.md`'s template section, search the
tree for the template's own name, owner, and obvious placeholders
(`rg -i '<template-name>|my-?app|com\.example|your-username'`), replace them, and ask
the user about any hit whose right value is not obvious.

## 3. Drafts, checks, commit

1. Copy the drafts to their repository paths (create `docs/product/`, `docs/design/` as
   needed). Where the template already has a document for the same subject, merge into
   it instead of adding a second one.
2. Run the verification command the template names (`just check`, `pnpm check`, …). A
   first build can take many minutes: run it in the background and do step 3 meanwhile.
   A failure is fixed, not skipped — and never by weakening a check, which the templates
   forbid.
3. Sync labels with the template's recipe (`just labels`, `pnpm repo:labels`, or
   whatever `triaging-issues` names). Without it, issue forms and `planning-tickets`
   silently lose labels.
4. Once the checks pass, commit in two steps so history stays readable —
   `chore: bootstrap <App> from <template>` (rename and Product section), then
   `docs: add kickoff requirements and UX drafts` — and push `main`. The pre-commit hook
   runs; never bypass it.

## Report

Repository URL, clone path, the identity values used, checks run with their result,
the steps deferred to later stages, and the human-only list.
