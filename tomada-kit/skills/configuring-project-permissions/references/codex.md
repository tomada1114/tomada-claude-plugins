# Codex CLI project rules

Step 6 of the skill. The facts about Codex's layers, trust, and the rule language
live in the `codex-cli-config` skill — read
`../codex-cli-config/references/rules-execpolicy.md` (syntax, layering, measured
limits) and `../codex-cli-config/references/config-files-and-precedence.md`
(§ "Personal, uncommitted project overrides") before writing a rule. This file is only
the procedure.

## The shape of a project's Codex setup

- `~/.codex/config.toml` — the sandbox and approval policy, and
  `[projects."<absolute repo path>"] trust_level = "trusted"`. Without trust, nothing
  under the repository's `.codex/` loads, the rules file included. Adding the trust
  entry is a user-level change: ask first, back the file up, append the table.
- `~/.codex/rules/default.rules` — the user layer: forbidden for the unrecoverable,
  prompt for publishing and irreversible operations, allow for everyday tools. A
  command no rule matches runs inside the sandbox and only prompts when the sandbox
  stops it.
- `<repo>/.codex/rules/local.rules` — this skill's output, gitignored by its exact path.

A project rule can only tighten: forbidden > prompt > allow across layers, so a
project `allow` never relaxes a user-level `prompt`. A git worktree does not contain
the ignored file, so a rule that must hold everywhere (hook bypass, force push) belongs
in the user layer, not here.

## Translating the Claude Code decisions

| Claude Code project rule | Codex |
|---|---|
| `ask` on a recipe or subcommand (`Bash(just run*)`, `Bash(cargo add*)`) | `prefix_rule(pattern = ["just", ["run", "dev", …]], decision = "prompt", …)` in `local.rules` |
| `allow` on a project script (`Bash(.agents/skills/*/scripts/*)`) | an `allow` rule listing each script path literally — no globs exist; only for scripts that need to run outside the sandbox (they call `gh`, push, or write outside the workspace) |
| user-level `allow` on a toolchain (`Bash(cargo *)`) with no Codex counterpart | propose an `allow` for that program in `~/.codex/rules/default.rules`, next to the other package managers, with a one-line reason (it writes outside the workspace) | <!-- neutrality-ignore: N2 -->
| `deny` on editing a file (`Edit(/src-tauri/Entitlements.plist)`) | no rule can express it — Codex rules see argv, not file edits. Leave it to the repository's instructions and the sandbox, and say so in the report |
| a hook (`PostToolUse` format-on-edit) | out of scope here; Codex hooks are a separate `.codex/hooks.json` |

Write `match` and `not_match` examples on every rule: they are checked when the file
loads, and a bad one makes the whole file fail to load. Put a short header comment on
the file stating that it is gitignored, loads only while trusted, and only tightens.

```python
prefix_rule(
    pattern = ["just", ["dev", "run", "install-app"]],
    decision = "prompt",
    justification = "Opens the app on the developer's Mac; run only when asked.",
    match = ["just run", "just dev"],
    not_match = ["just check", "just smoke"],
)
```

## Verify statically

Never verify by running the guarded command. Check both layers together:

```bash
G=~/.codex/rules/default.rules; L=<repo>/.codex/rules/local.rules
for c in "just run" "just check" "cargo add serde" "cargo build"; do
  printf '%-30s ' "$c"
  codex execpolicy check -r "$G" -r "$L" -- $c | python3 -c 'import json,sys; print(json.load(sys.stdin).get("decision", "(no match)"))'
done
```

Under zsh, word-split the command with `${=c}` instead of `$c`. Probe every prompt rule,
two or three commands that must stay allowed, and one user-level forbidden command
(`git push --force origin x`) to confirm both files loaded. Put the table in the report.

Whether every `*.rules` file in one `rules/` directory loads in a real session is not
confirmed from source (see the `codex-cli-config` reference) — `execpolicy check` only
evaluates the files passed to it. Say so when reporting, and suggest the user confirm
once in a Codex session in the repository.
