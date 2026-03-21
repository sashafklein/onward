---
id: "TASK-062"
type: "task"
plan: "PLAN-007"
chunk: "CHUNK-017"
project: ""
title: "Remove files and acceptance from task frontmatter in split.py and cli_commands.py"
status: "open"
description: "In `src/onward/split.py`, function `prepare_task_writes` (around line 510–527): delete the two lines that put `\"files\": t_files` and `\"acceptance\": candidate[\"acceptance\"]` into the `metadata` dict. The body already renders both into markdown sections, so they belong in the body only. Keep the `t_files` and `acceptance_lines` local variables — they are still used to build the body string.\n\nIn `src/onward/cli_commands.py`, function `cmd_batch` (around line 802–818): delete the two lines `\"files\": file_list` and `\"acceptance\": acceptance` from the `metadata` dict. Keep the `file_list` and `acceptance` local variables if they are used to build the body template, otherwise remove them too — check whether `body_template` rendering uses them; if not, the parsing/normalisation of `files` and `acceptance` from the entry can also be removed.\n\nIn the same file, function `cmd_new_task` (around line 878–895): delete `\"files\": []` and `\"acceptance\": []` from the `metadata` dict.\n\nDo not change any body-building logic."
human: false
model: "sonnet"
executor: "onward-exec"
depends_on: []
files:
- "src/onward/split.py"
- "src/onward/cli_commands.py"
acceptance:
- "A task file written by `prepare_task_writes` does not contain `files:` or `acceptance:` keys in its YAML frontmatter"
- "A task file written by `cmd_batch` does not contain `files:` or `acceptance:` keys in its YAML frontmatter"
- "A task file written by `cmd_new_task` does not contain `files:` or `acceptance:` keys in its YAML frontmatter"
- "The markdown body of each written task still contains a '# Files to inspect' section and an '# Acceptance criteria' section"
created_at: "2026-03-21T20:25:46Z"
updated_at: "2026-03-21T20:25:46Z"
effort: "s"
---

# Context

In `src/onward/split.py`, function `prepare_task_writes` (around line 510–527): delete the two lines that put `"files": t_files` and `"acceptance": candidate["acceptance"]` into the `metadata` dict. The body already renders both into markdown sections, so they belong in the body only. Keep the `t_files` and `acceptance_lines` local variables — they are still used to build the body string.

In `src/onward/cli_commands.py`, function `cmd_batch` (around line 802–818): delete the two lines `"files": file_list` and `"acceptance": acceptance` from the `metadata` dict. Keep the `file_list` and `acceptance` local variables if they are used to build the body template, otherwise remove them too — check whether `body_template` rendering uses them; if not, the parsing/normalisation of `files` and `acceptance` from the entry can also be removed.

In the same file, function `cmd_new_task` (around line 878–895): delete `"files": []` and `"acceptance": []` from the `metadata` dict.

Do not change any body-building logic.

# Scope

- In `src/onward/split.py`, function `prepare_task_writes` (around line 510–527): delete the two lines that put `"files": t_files` and `"acceptance": candidate["acceptance"]` into the `metadata` dict. The body already renders both into markdown sections, so they belong in the body only. Keep the `t_files` and `acceptance_lines` local variables — they are still used to build the body string.

In `src/onward/cli_commands.py`, function `cmd_batch` (around line 802–818): delete the two lines `"files": file_list` and `"acceptance": acceptance` from the `metadata` dict. Keep the `file_list` and `acceptance` local variables if they are used to build the body template, otherwise remove them too — check whether `body_template` rendering uses them; if not, the parsing/normalisation of `files` and `acceptance` from the entry can also be removed.

In the same file, function `cmd_new_task` (around line 878–895): delete `"files": []` and `"acceptance": []` from the `metadata` dict.

Do not change any body-building logic.

# Out of scope

- None specified.

# Files to inspect

- `src/onward/split.py`
- `src/onward/cli_commands.py`

# Implementation notes

- Keep the change scoped to this task.

# Acceptance criteria

- A task file written by `prepare_task_writes` does not contain `files:` or `acceptance:` keys in its YAML frontmatter
- A task file written by `cmd_batch` does not contain `files:` or `acceptance:` keys in its YAML frontmatter
- A task file written by `cmd_new_task` does not contain `files:` or `acceptance:` keys in its YAML frontmatter
- The markdown body of each written task still contains a '# Files to inspect' section and an '# Acceptance criteria' section

# Handoff notes
