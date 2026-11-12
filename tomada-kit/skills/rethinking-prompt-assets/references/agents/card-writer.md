# Brief: card writer

Fill the `{...}` slots and hand one copy per slice to a `scout` sub-agent. Slices are
disjoint lists of asset directories or files, sized at roughly 3,000 lines each.

---

You are extracting facts from prompt assets (skills, sub-agent definitions, memory
files) so that a reviewer can compare them without reading every file.

Intent: the reviewer will look across all cards for overlap, contradiction and waste
between assets. The cards must therefore record what each asset says, in its own
words where the wording matters, and leave every judgment to the reviewer. If
something is ambiguous, quote it and mark it `unclear` rather than resolving it.

Read every markdown file of each asset below, in full. Change nothing.

{ASSET_PATHS}

Names of the sub-agent tiers in this setup, for the Delegations field: {TIER_NAMES}

## Output

One card per asset, in exactly this shape, with a `path:line` after every item.

```
## <asset name>
- Claims to own: <the job it says it does, from its description and opening>
- Explicitly not its job: <boundaries it states, and the asset it points to for each>
- Triggers: <situations it says should load it>
- Inputs: <files, arguments or prior artifacts it reads>
- Outputs: <files it writes and where; remote writes it makes>
- Steps: <its phases or stages in order, one line each; for each, who runs it
  (this asset, another named asset, a sub-agent) and what is handed on>
- Asks the user: <each point where it stops for an answer or an approval>
- Delegations: <each hand-off to a fresh context: the tier or model named, the cap, the brief file>
- Coordination: <for each step that uses more than one context: what each worker
  returns and to whom; whether workers see each other's output before the end, and
  through what (messages, a task list, a named shared file); whether a worker is
  continued across tasks or spawned fresh each time; any check-and-fix loop with
  its criteria and its cap on rounds; any mention of agent teams or teammates;
  where the step is said to run (interactive, unattended, scheduled, another runtime)>
- Names other assets: <each other skill or agent it mentions, and what for>
- Restates: <facts or rules it states that it also attributes to another asset>
- Cautions: <each prohibition, warning or "always/never" rule, quoted, with the reason
  it gives, or "no reason given">
- Model-specific text: <each line naming a model, a model version, an effort level, or
  a behavior of a particular model, quoted>
```

Report every item you find for every field, including ones that look minor; the
reviewer filters. Write "none" for an empty field. Do not summarize an asset's quality
or suggest changes.
