# Brief: blind designer

Fill the three `{...}` slots and hand the result to one `architect` sub-agent. Paste
the needs document in whole; pass no path into the estate.

---

You are designing a set of prompt assets for one person's agentic coding setup, from
nothing. Prompt assets are the instruction files Claude Code loads: always-loaded
memory files, skills loaded on demand, sub-agent definitions, and the scripts and
reference files those bundle.

Intent: an existing setup is being reviewed, and the reviewer already knows it too
well to judge it. Your design is the independent baseline it will be compared against,
so its value comes from your not knowing the existing setup. A design that happens to
match the existing one is a fine result; a design copied from it is useless.

For that reason, do not open or list anything under these locations, and do not search
session history:

{OFF_LIMITS_PATHS}

Your own context may include a list of installed skills and agents. That list is the thing
under review. Design as if it were empty, and do not reuse its names or its
boundaries. You need no tools for this task: everything you may use is below.

<needs>
{NEEDS_DOCUMENT}
</needs>

<environment>
{ENVIRONMENT_FACTS}
</environment>

## What to design

The smallest set of assets that serves every job in the needs document well. For each
job, first ask whether a current model does it adequately with no asset at all; an
asset has to earn the context it costs on every load. Then decide where assets are
needed, how many, and where the boundaries between them fall. Prefer fewer, clearly
separated units over many overlapping ones, and a single place for each fact.

## Output

Return the design as text in exactly these sections.

```
## Units
### U1: <descriptive name>
- Kind: memory rule | skill | sub-agent definition | script | reference
- Jobs: <job ids from the needs document>
- Loads when: <the situation that should bring it into context>
- Owns: <the decisions and facts that live here and nowhere else>
- Does not own: <the nearest things a reader might expect here, and where they live>
- Inputs / outputs: <files or answers it consumes and produces>
- Delegates: <what it hands to a fresh context, and what kind of worker that needs
  (cheap mechanical, read-only collection, tool-free writing, hard reasoning), or "nothing">

## Flows
### F1: <name>
<the ordered stages for a job that spans units: which unit runs each stage, what file
or decision is handed to the next, and where the user is asked something>
- Coordination: <for each stage that needs more than one context: what a worker must
  learn from the others while it works (nothing, or which findings), what comes back
  to the lead, and the lightest shape that provides it: a lead with sub-agents that
  only return results, a checker loop with written criteria and a cap, a worker
  continued across tasks, or workers that exchange findings mid-run through messages
  or a shared file. "Single context" when the stage needs no dividing>

## Jobs that need no asset
- <job id>: <why the model's default behavior is enough>

## Open choices
- <a boundary you could have drawn two ways, the alternative, and what evidence
  would settle it>
```

Give every job in the needs document exactly one home: a unit, or the no-asset list.
If the needs document leaves a judgment call to you, make it and record it under
Open choices rather than asking.
