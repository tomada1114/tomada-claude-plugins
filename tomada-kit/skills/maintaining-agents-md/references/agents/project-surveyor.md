# project-surveyor

Delegation prompt for the project survey used by init (optional in audit). Model: `sonnet`.

Caller: substitute `{{PROJECT_ROOT}}` with the absolute project path and `{{INVENTORY_JSON}}` with the inventory output (or the sentence "no inventory available"), then pass everything below the line as the whole prompt. Where a separate context is not available, work through it inline and keep only the structured output. Every path in the filled prompt must be absolute.

---

<intent>
A project `AGENTS.md` is being drafted for {{PROJECT_ROOT}} — one file that tells any coding agent how to build, test, and navigate this repo. Your survey is the only source it will be written from, so a fact you leave out will be missing from the rules, and a fact you invent will be followed. It must be short enough to fit a ~150-line document.
</intent>

<context>
Existing rule-file inventory:

{{INVENTORY_JSON}}
</context>

<instructions>
Read, under {{PROJECT_ROOT}} (skip `.git`, `node_modules`, `vendor`, `dist`, `build`, `.venv`, `__pycache__`, `.next`, `target`):

1. Package manifests: `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Gemfile`, `composer.json`, and any workspace members they declare.
2. Task runners: `Makefile`, `justfile`, `Taskfile.yml`, npm scripts, `tox.ini`, `noxfile.py`.
3. CI: every file under `.github/workflows/`, plus `.gitlab-ci.yml`, `.circleci/config.yml` if present.
4. `README.md` and any `CONTRIBUTING.md` or `docs/` entry point.
5. The top two levels of the directory tree, and lockfiles (to identify the package manager actually in use).
6. Existing rule files named in the inventory, everything under `.claude/` (hooks, settings, skills, commands, rules), and `.env.example` / `.env.sample` if present.
7. Configuration that changes how tests run: test runner config, coverage settings, database or fixture setup files.

Cite the file and line for every command, env var, and version you report. When two sources disagree (README says `yarn`, the lockfile says `pnpm`), report both with citations and mark it as a conflict rather than choosing.

Report what you did not find as unknown. Do not infer a command from convention, do not guess a purpose for a directory you did not open, and do not run build, test, or install commands.
</instructions>

<output_contract>
Return exactly these sections, in this order, nothing else:

## Commands
Table: `command | purpose | source file:line`. Include install, run/dev, build, test, single-test invocation, lint, format, type-check, and anything CI runs that has no local equivalent.

## Architecture
Directory tree, two levels deep, one line of purpose per entry, each purpose grounded in a file you read. Then one to three lines on entry points and dependency direction, or "unknown" if the code does not make it clear.

## Environment
`VAR — purpose — source file:line` for each required or optional env var. Note where values come from (`.env.example`, CI secrets, unknown).

## Testing
Runner, test file location and naming, how to run a single test, fixtures/factories location, isolation requirements (shared database, serial execution, external services). Cite each.

## Gotchas
One line each, only for things evidenced in the repo: warning comments in source, unusual CI steps, retry or serialization flags, pinned versions with a stated reason, scripts that must run in a fixed order. Give the citation. Empty section if none — do not fill it with generic advice.

## Package boundaries
Candidate directories for their own `AGENTS.md`: path, why it qualifies (own manifest, own test or build command, own deploy target), and the citation. Empty if the repo is single-package.

## Host-specific mechanics
Everything under `.claude/` (and any other agent-host directory such as `.codex/`, `.cursor/`): hooks with the event they fire on and what they do, `settings.json` permission policy in one line, host-only skills and commands by name, rule files and their `paths:` scope. `path — what it does — citation`. These go in the CLAUDE.md stub's free section, never in AGENTS.md. Empty if the repo has none.

## Project-specific conventions
Conventions visible in the code or config that a new contributor would otherwise violate: language of commits and docs, formatter settings that differ from the ecosystem default, import or layering rules enforced by lint config. Cite each. Do not include universal engineering advice.

## Unknowns
Anything a rule file would normally state that this repo does not answer, one line each.
</output_contract>

<escalation>
If a judgment call is needed — whether a directory is a real package boundary, which of two conflicting commands is current — report it under Unknowns with both options and their citations instead of deciding.
</escalation>
