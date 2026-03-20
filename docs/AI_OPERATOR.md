# AI operator quickstart

This guide is for **people and agents** who already have Onward installed and wired into their workflow. It is the short path: what to run, how to recover, and what **not** to do. Authoritative lifecycle rules live in **[LIFECYCLE.md](LIFECYCLE.md)**; if anything here disagrees, trust **LIFECYCLE** and the CLI.

**Also read:** [CAPABILITIES.md](CAPABILITIES.md) (what calls the model), [WORK_HANDOFF.md](WORK_HANDOFF.md) (executor payload), [INSTALLATION.md](../INSTALLATION.md) (paste blocks and first-run).

---

## The minimal loop

Use this every session:

1. **`onward report`** — see plans, chunks, tasks, blockers, and recent activity.
2. **`onward next`** — pick a suggested open item (optional: filter with `--project <key>`).
3. **`onward start TASK-###`** — optional; marks `in_progress` for visibility before you do anything else.
4. **`onward work TASK-###`** — runs hooks + executor; on **success** the task is already **`completed`**.
5. **`onward report`** again — hand off cleanly to the next session or agent.

Chunk-sized execution: **`onward work CHUNK-###`** drains ready tasks in dependency order, then runs the chunk post hook. Details: [LIFECYCLE.md](LIFECYCLE.md).

---

## `onward work` vs `onward complete`

| Situation | Command |
| --------- | ------- |
| You are using the configured executor to do the task (normal path) | **`onward work TASK-###`** |
| You finished the work **outside** `onward work` (editor-only, different tool, emergency) and want to mark it done | **`onward complete TASK-###`** |
| You want to show “I’m on this” before running the executor | **`onward start TASK-###`** *(optional)* |
| You are abandoning the item | **`onward cancel TASK-###`** |

**Do not** run **`onward complete`** after a **successful** **`onward work`** on the same task — the task is already **`completed`**; `complete` will error.

---

## Project flags and metadata

- **`--project <key>`** on `list`, `report`, `next`, `tree`, etc. scopes views to one project stream. Use a stable key your team agrees on. **`onward tree`** (and the report’s **Active work tree** section) list only **open** plans and **open / in_progress** chunks and tasks — not completed or canceled leaves.
- **`--blocking`** — tasks/chunks that block others (good for “what stops the train?”).
- **`--human`** — work that needs a human decision; agents should not silently steamroll these.

In artifact frontmatter:

- **`human: true`** — mark tasks that require a person (reviews, secrets, policy).
- **`blocked_by: [TASK-###, …]`** — encode real dependencies; keeps `next` and chunk ordering honest.

When you discover new work during a run, **create a new task** (with `blocked_by` / `human` / `project` as appropriate) — do not leave it only in chat.

---

## Sync (optional)

If **`sync.mode`** in `.onward.config.yaml` is **`branch`** or **`repo`**, you can mirror `.onward/plans/` to another checkout with **`onward sync status`**, **`onward sync push`**, **`onward sync pull`**. Default **`local`** mode has no remote target — **`onward sync status`** still succeeds (exit 0); **`onward sync push`** / **`pull`** exit **1** with a hint (not a silent no-op). Full semantics: [README.md](../README.md) (sync section) and [INSTALLATION.md](../INSTALLATION.md).

---

## Anti-patterns and recovery

### 1. Planning and todos only in chat

**Symptom:** No files under `.onward/plans/`, or plans exist but status never updates.

**Recovery:** Run **`onward init`** / **`onward doctor`**. Create or update artifacts with **`onward new plan`**, **`onward new chunk`**, **`onward new task`**. Paste the repo’s **AGENTS.md** / install instructions so the agent must use Onward as the sole plan store.

---

### 2. Skipping **`onward doctor`**

**Symptom:** Mysterious errors later (invalid config, bad `sync` combo, duplicate IDs).

**Recovery:** Run **`onward doctor`** from the workspace root. Fix every reported issue (config keys, JSON files, git requirements for sync). Re-run until it passes.

---

### 3. Treating **`onward split`** as always model-backed

**Symptom:** Expecting an LLM to decompose the plan during `split`; surprise when behavior is purely local.

**Recovery:** Read [CAPABILITIES.md](CAPABILITIES.md). **`onward split`** is **heuristic** (markdown sections → candidates) in the default path; it does **not** call the executor. Use **`onward review-plan`** when you want model-backed scrutiny of a plan. For decomposition, edit artifacts or use split as a starting point and refine files.

---

### 4. Running **`onward complete`** after **`onward work`** succeeded

**Symptom:** Error about invalid transition from **`completed`**.

**Recovery:** None needed for that task — it is already done. Run **`onward report`** and pick the next open item. See [LIFECYCLE.md](LIFECYCLE.md).

---

### 5. Using **`start`** as mandatory before every task

**Symptom:** Extra friction; agents think `start` → manual work → `complete` is the only valid path.

**Recovery:** **`onward start`** is optional. You may run **`onward work`** directly from **`open`**. Use **`start`** when you want visible “claimed” state before execution.

---

### 6. Ignoring **`human`** and **`blocked_by`**

**Symptom:** Agents pick tasks that need a person, or run work out of dependency order.

**Recovery:** Use **`onward list --human`** and **`onward list --blocking`** (with **`--project`** as needed). Fix frontmatter on tasks so **`blocked_by`** reflects real order; mark **`human: true`** where appropriate.

---

### 7. Expecting sync push/pull in **`local`** mode

**Symptom:** CLI refuses push/pull with a message about `sync.mode` (exit code **1**).

**Recovery:** Either stay in **`local`** and use git on your main repo only, or configure **`branch`** / **`repo`** in `.onward.config.yaml` as described in INSTALLATION/README, then **`onward sync push`** once the target exists. Do not expect exit **0** for push/pull in **`local`** mode — that would hide a misconfiguration in scripts.

---

### 8. Ending a session without **`onward report`**

**Symptom:** Next session or agent has no snapshot of status or recent runs.

**Recovery:** Run **`onward report`** (and commit `.onward/plans/` if your team tracks plans in git). Make **`report`** the last step in your operating loop.

---

## Executor preflight

When `ralph.enabled` is true, **`onward work`** and **`onward review-plan`** (and the **`post_chunk_markdown`** hook) verify that `ralph.command` exists on `PATH` or as an executable file path **before** starting a run. If it fails, fix `ralph.command`, install the binary, or for automated tests use command **`true`**. **`onward split`** does not use the executor today, so it does not run this check. Details: [CAPABILITIES.md](CAPABILITIES.md).

## Related docs

| Doc | Use |
| --- | --- |
| [LIFECYCLE.md](LIFECYCLE.md) | Status rules, `work` vs `complete`, chunk behavior |
| [CAPABILITIES.md](CAPABILITIES.md) | Executor vs local commands |
| [WORK_HANDOFF.md](WORK_HANDOFF.md) | Stdin payload, runs, hooks |
| [INSTALLATION.md](../INSTALLATION.md) | Install, agent paste blocks, sync troubleshooting |
| [CONTRIBUTION.md](CONTRIBUTION.md) | Local dev and tests |
