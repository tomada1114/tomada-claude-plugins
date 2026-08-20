# Review lens prompt

One template for every lens in the Improving playbook. Fill the placeholders, then hand the text to a fresh context — a parallel sub-agent where the environment supports it; otherwise work through it inline, one lens at a time, in the order SKILL.md lists them, reading the checklist before the skill each time.

| Placeholder | Fill with |
|---|---|
| `{{LENS_NAME}}` | `prose` / `neutrality` / `structure` / `scripts` / `orchestration` |
| `{{LENS_FOCUS}}` | the "Looks for" cell of that lens in SKILL.md |
| `{{CHECKLIST_PATH}}` | absolute path of the reference holding this lens's `## Review checklist` |
| `{{SKILL_DIR}}` | absolute path of the skill under review |
| `{{SCRIPT_FINDINGS}}` | the P0 findings (code, location, message) relevant to this lens, or "none" |
| `{{OUTPUT_PATH}}` | absolute path of `lens-{{LENS_NAME}}.md` in the audit directory |

---

You are reviewing the skill at {{SKILL_DIR}} through one lens: {{LENS_NAME}} — {{LENS_FOCUS}}.

Intent: the main agent merges several lenses into a prioritized change list for the skill's author. Your report is one input to that merge; ranking and filtering happen there, not here.

Step 1 — read {{CHECKLIST_PATH}} completely. Its "Review checklist" section defines the item IDs you report against.
Step 2 — read {{SKILL_DIR}}/SKILL.md in full, then every file under {{SKILL_DIR}}/references/. For scripts under {{SKILL_DIR}}/scripts/, read the `--help` output or docstring; read the source only if your lens is `scripts`.
Step 3 — for each checklist item, report PASS / FAIL / N-A with a file:line citation and a one-line reason. These script findings are already known — do not repeat them, but do report what they miss: {{SCRIPT_FINDINGS}}
Step 4 — list every FAIL as a finding, including low-severity and uncertain ones, with a confidence (high / medium / low) and a severity (high / medium / low). Where the fix is concrete, give old → new text. Where you would need a judgment call the checklist does not settle, put it under Unresolved with both readings instead of deciding.

Write the report to {{OUTPUT_PATH}} and return it as your final message, in exactly this shape:

## {{LENS_NAME}}
### Checklist
- <ID> PASS|FAIL|N-A — <reason> (<file>:<line>)
### Findings
- <ID> [<severity>/<confidence>] <file>:<line> — <what is wrong> → <proposed change>
### Unresolved
- <item> — <reading A> / <reading B>
