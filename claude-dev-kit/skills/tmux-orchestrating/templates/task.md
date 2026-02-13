# Task: {TASK_DESCRIPTION}

## Instructions

{DETAILED_INSTRUCTIONS}

## Completion

When done, write results to `queue/reports/pane{N}_report.md` with the following format:

```
status: done
summary: (1-line summary of what was accomplished)
files_modified:
  - path/to/file1
  - path/to/file2
```

If the task failed:

```
status: failed
summary: (1-line description of what went wrong)
error: (detailed error description)
```
