<!-- platform-annex -->

# Rules (.rules / prefix_rule) — the execpolicy layer

Rules govern whether a command may run **outside the sandbox** without prompting.
They sit alongside `sandbox_mode` / permission profiles (see
`references/permissions-and-sandbox.md`) but answer a different question: not "what is this
command allowed to touch," but "does this specific command prefix need a human
in the loop at all." Status: **experimental** — the docs state Rules may still
change, but they are current and safe to document as-is.

## Why teams reach for Rules

Under `workspace-write`, Codex still prompts for commands that write to
protected paths inside a writable root — most commonly `git commit`, because
`.git` stays read-only even when the rest of the workspace is writable (see
`references/permissions-and-sandbox.md` for the full protected-path list and why
`--add-dir` doesn't help). Rules are the documented fix: a narrow `allow` rule
for the exact command prefixes you trust removes the repeated prompt without
widening the sandbox.

The same mechanism doubles as a safety net in the other direction. A team that
shares `<repo>/.codex/rules/*.rules` in version control applies the same
command boundary to everyone who opens the project as trusted — junior
contributors included — by marking destructive prefixes (`git push --force`,
`rm -rf`, `sudo`) `forbidden` or `prompt` instead of leaving them to
`workspace-write`'s default judgment.

## Starlark syntax

`.rules` files are Starlark (a Python-like, safe-to-run subset — no imports, no
arbitrary I/O). A file is a sequence of `prefix_rule(...)` calls:

```python
prefix_rule(
    pattern = ["gh", "pr", "view"],
    decision = "prompt",
    justification = "Viewing PRs is allowed with approval",
    match = [
        "gh pr view 7888",
        "gh pr view --repo openai/codex",
    ],
    not_match = [
        "gh pr --repo openai/codex view 7888",
    ],
)
```

## `prefix_rule()` parameters — all 5

| Parameter | Required | Meaning |
|---|---|---|
| `pattern` | yes | Non-empty list defining the command prefix to match. Each element is a literal string (`"pr"`) or a list of literal alternatives at that position (`["view", "list"]`). |
| `decision` | no — **defaults to `"allow"`** | `"allow"` \| `"prompt"` \| `"forbidden"`. |
| `justification` | no | Human-readable reason; may surface in prompts or rejection messages. |
| `match` | no, default `[]` | Example invocations Codex validates against the pattern **at load time**. |
| `not_match` | no, default `[]` | Example invocations that must **not** match, also validated at load time. |

`decision` meanings:
- `allow` — run the matched command outside the sandbox without prompting.
- `prompt` — ask for approval before each matching invocation.
- `forbidden` — block the command without prompting.

`match` / `not_match` are not documentation-only comments — a bad example in
either list makes the entire `.rules` file **fail to load**. Treat them as
compile-time assertions on your own pattern, and expect a rule with no
`match`/`not_match` entries to load but go unverified.

Because `decision` defaults to `allow`, `prefix_rule(pattern = ["git", "commit"])`
alone is a valid, working allow-rule — but omitting `decision` reads as
ambiguous to a reviewer. Write it explicitly.

## Three layers and their paths

| Layer | Path | Loaded when |
|---|---|---|
| User | `~/.codex/rules/*.rules` | Always, regardless of trust state. |
| Project | `<repo>/.codex/rules/*.rules` | Only when the project's `.codex/` layer is trusted (see `references/config-files-and-precedence.md` for the trust gate). |
| Admin | `requirements.toml` → `[rules] prefix_rules = [...]` | Always, in managed/organization environments. |

Codex scans `rules/` under every active config layer at startup, including any
Team Config locations plus the user layer.

The TUI's approval picker can persist a rule for you: approving a command
in-session writes an `allow` rule to `~/.codex/rules/default.rules` by default
(rule writeback).

### Admin syntax differs from user/project syntax

`requirements.toml` rules are **TOML, not Starlark**:

```toml
[[rules.prefix_rules]]
pattern = [{ token = "rm" }, { any_of = [{ token = "-rf" }, { token = "-fr" }] }]
decision = "forbidden"
justification = "Recursive delete requires human review"
```

Admin rules must specify `decision` explicitly, and it must be `"prompt"` or
`"forbidden"` — **never `"allow"`**. `{ any_of = [...] }` is the TOML
equivalent of Starlark's list-of-alternatives position in `pattern`.

## Precedence: strictest wins, no override

When more than one rule matches a command, across any combination of layers,
Codex applies the most restrictive decision: **`forbidden` > `prompt` > `allow`**.
There is no mechanism to override a stricter rule from a looser one — a user or
project `allow` can never win against an admin `prompt`/`forbidden` on the same
prefix, because admin rules can only ever be `prompt` or `forbidden` in the
first place.

Practical consequence: if your organization's `requirements.toml` sets
`git commit` to `prompt`, your own `~/.codex/rules/default.rules` `allow` rule
for `git commit` still gets you a prompt — Rules composes safety upward only.

## Shell command splitting

Codex parses shell wrappers (`bash -lc`, `bash -c`, `sh`, and `zsh` equivalents)
with tree-sitter before matching patterns.

- A **linear chain of plain words** joined by `&&`, `||`, `;`, or `|` is split
  into individual commands, and each is evaluated against Rules separately
  (strictest-wins still applies across the set). `git add . && git commit -m x`
  is evaluated as two commands: `git add .` and `git commit -m x`.
- Anything with **redirection, command substitution, environment-variable
  assignment, wildcards, or control flow** (`if`, loops, subshells) is treated
  as a single opaque invocation — the full argv becomes
  `["bash", "-lc", "<entire script>"]` — and a narrow `pattern` targeting the
  inner command will not match it.

Write patterns assuming the simple case is what gets matched, and expect
anything scripted or piped through redirection to fall through to whatever
decision applies to `bash`/`sh` itself (or to a prompt, if none matches).

## Testing rules

```bash
codex execpolicy check --pretty --rules ~/.codex/rules/default.rules -- gh pr view 7888
```

`--rules` (short `-r`) is repeatable — pass it once per `.rules` file to test
against a combined rule set before relying on it live.

## Bypassing rules for one run

```bash
codex exec --ignore-rules "..."
```

Skips user and project `.rules` for that single invocation only. It does not
touch admin `requirements.toml` rules — those still apply.

## The headline recipe: let git write without full access

The following is an illustrative pattern — a shape to adapt, not a specific
user's configuration.

```python
# ~/.codex/rules/default.rules
# (or <repo>/.codex/rules/*.rules for a project-scoped version, shared in git)

prefix_rule(
    pattern = ["git", ["add", "commit", "status", "diff", "log"]],
    decision = "allow",
    justification = "Local git operations are trusted in this workspace.",
    match = ["git commit -m msg", "git add .", "git status"],
)

# Safety complement: prompt before pushing, forbid the destructive variants
prefix_rule(
    pattern = ["git", "push"],
    decision = "prompt",
    justification = "Pushing to a remote should get a human look first.",
)

prefix_rule(
    pattern = ["git", "push", "--force"],
    decision = "forbidden",
    justification = "Force-pushing can destroy remote history.",
)

prefix_rule(
    pattern = ["git", "reset", "--hard"],
    decision = "forbidden",
    justification = "Hard reset discards uncommitted work.",
)

prefix_rule(
    pattern = ["sudo"],
    decision = "forbidden",
    justification = "Privileged commands are never auto-approved.",
)

prefix_rule(
    pattern = ["rm", "-rf"],
    decision = "forbidden",
    justification = "Recursive delete requires a narrower, explicit command.",
)
```

Caveats worth keeping in mind when adapting this:

- `pattern = ["git", "push", "--force"]` and `pattern = ["git", "push"]` both
  match `git push --force` (a more specific pattern doesn't exempt a command
  from a broader one) — strictest-wins resolves the overlap in `forbidden`'s
  favor automatically, so ordering the two rules doesn't matter.
- The `git add/commit/status/diff/log` allow-rule only ever removes prompts for
  local, non-destructive git operations; it says nothing about network access
  or sandbox boundaries — those are still governed by `sandbox_mode` or the
  active permission profile.
- An admin `requirements.toml` `prompt` or `forbidden` entry on `git commit`
  overrides this `allow` for anyone in a managed environment — the user cannot
  loosen an admin-imposed restriction from `~/.codex/rules/` or
  `<repo>/.codex/rules/`.

For why `.git` needs an escape hatch at all under `workspace-write`, see
`references/permissions-and-sandbox.md`.

## Measured limits of the pattern language (0.153.4)

The Starlark builtins the policy parser exposes are exactly `prefix_rule`,
`network_rule`, `paths` and `host_executable`. There is **no regex, glob or
substring matching on arguments** — a pattern is a positional list where
each position is a literal token or a list of literal alternatives. Three
consequences worth stating plainly whenever someone asks "why didn't my
rule fire":

**1. A shell wrapper defeats every rule.** Anything with a redirect, pipe,
substitution or control structure arrives as one `["bash","-lc","<whole
line>"]` invocation, and no rule written against the inner command matches:

```
$ codex execpolicy check -r default.rules -- rm -rf /
{"decision":"forbidden"}
$ codex execpolicy check -r default.rules -- bash -lc "rm -rf /"
{"matchedRules":[]}
```

Same for `bash -lc "cat .env"`, `bash -lc "sudo …"`, `bash -lc "git commit
--no-verify"`. Only the built-in dangerous-`rm` heuristic (a separate code
path, invisible to `execpolicy check`) unwraps `sudo` / `env` / `bash -c` /
`for` loops at all. Rules are a speed limit, not a wall.

**2. Position is fixed, so a flag that moves is a flag that escapes.**

```
find . -delete               -> prompt      (matches ["find",".","-delete"])
find . -name '*.py' -delete  -> NO MATCH
rsync --delete src dst       -> prompt
rsync -a --delete src dst    -> NO MATCH
```

**3. Only the argv *shape* is visible, never the intent.** `cat .env` is
blockable; `grep -r KEY .env` and `python3 -c "open('.env').read()"` are
not. A file-level guarantee has to come from the permission profile's
`filesystem` deny (which applies to every reader), not from rules — and a
disabled sandbox gives that up.

### `any_of` works at position 0 too

The alternatives list is not special-cased to later positions, so a whole
family of readers collapses into one rule:

```python
SECRET_READERS = ["cat", "bat", "head", "less", "xxd", "cp", "open", "vim"]
SECRET_FILES   = [".env", "./.env", "~/.netrc"]

prefix_rule(
    pattern = [SECRET_READERS, SECRET_FILES],
    decision = "forbidden",
    justification = "Reading or copying a secret file is not allowed.",
    match = ["cat .env", "cp .env /tmp/x", "open ~/.netrc"],
    not_match = ["cat .env.example", "cp src/a.ts src/b.ts"],
)
```

Verified against 0.153.4. Note that `match`/`not_match` examples are
checked when the file loads, so a rules file that `codex execpolicy check`
parses at all has already self-tested every example in it.
