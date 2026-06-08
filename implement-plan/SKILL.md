---
name: implement-plan
description: Implement a written plan phase-by-phase using sequential subagents, logging each phase's outcome back into the plan, then verifying and running a final code review.
argument-hint: "[model: opus|sonnet|haiku]"
disable-model-invocation: false 
---

# Implement Plan

Drive a plan from start to finish: one phase per fresh subagent, log each phase's outcome back into the plan, verify, then review.

## Step 0: Locate the plan and check baseline

1. Find the plan. Try in this order:
   - A plan file path provided in `$ARGUMENTS` or earlier in the conversation
   - The most recent file in `~/.claude/plans/`
   - Otherwise, ask the user where the plan lives
2. Verify the environment, in parallel:
   - In a git repo
   - Working tree is clean — if not, ask the user to commit/stash before continuing
   - Not on `main` / `master` — if so, confirm with the user before proceeding
3. Capture the starting commit: `START_REF=$(git rev-parse HEAD)`. You'll use this to identify files modified during the run.
4. Baseline check: run `yarn build`. If any fail at baseline, surface to the user — we can't tell our breakage from preexisting breakage otherwise.

## Step 1: Confirm parameters

Use `AskUserQuestion` to ask, in a single call, anything not already answered by `$ARGUMENTS`:

1. **Model for implementation agents** — `opus`, `sonnet`, or `haiku`? Default to `$ARGUMENTS` if it names a valid model.
2. **Per-phase strictness gate**:
   - **strict** — modified tests + build + lint must pass after each phase
   - **build-only** — build + lint must pass after each phase; tests can break mid-run
   - **loose** — anything goes; only the final state must be green
3. **Commit strategy** — one commit per phase, or a single commit at the end, or no commits (let the user commit)?

Wait for the answers before continuing.

## Step 2: Parse phases

Split the plan into discrete phases. Numbered headings (`## Phase 1`, `## Step 1`) are the typical markers. If structure is ambiguous, list what you found and confirm with the user before kicking off.

## Step 3: Run phases sequentially

For each phase, in order. **Never run two phases in parallel.**

1. **Spawn one fresh Agent** with `subagent_type: "general-purpose"` and `model: <chosen-model>`. Prompt must include:
   - The **full plan** (with whatever logs prior phases have already added — so the agent sees what's already been done).
   - The **specific phase** to implement, quoted.
   - The **strictness gate** so the agent runs the right local checks before reporting back.
   - Instruction to **report back** with: files changed, summary of what was done, any deviations from the plan and why, and any followups it noticed but didn't do.
   - The **BLOCKED protocol** (see below): if stuck or unsure, don't guess and don't make destructive changes — return a message starting with `BLOCKED:` followed by specific questions, and stop. The parent will answer and resume the same agent via `SendMessage`, so context is preserved.
2. **Wait** for the agent to finish before doing anything else. Do not start the next phase early.
3. **Handle BLOCKED returns**: if the agent's return message starts with `BLOCKED:`, treat it as a clarification request rather than a completion.
   - Try to answer from the plan and conversation context first.
   - If the answer requires a user decision, ask via `AskUserQuestion`.
   - **Resume the same agent** via `SendMessage` (use the agent's ID or name as the `to` field) with the answers — do **not** spawn a new agent, since that throws away its context.
   - Loop until the agent returns a real completion (no `BLOCKED:` prefix).
4. **Run the gate** yourself to verify (don't trust the agent's self-report alone):
   - strict → `yarn build && yarn lint`, plus the test files for any modified test sources (`git diff --name-only $START_REF -- '*.test.*' '*.spec.*'`)
   - build-only → `yarn build && yarn lint`
   - loose → no check
5. If the gate fails, **stop and ask the user** how to proceed (retry the phase, hand-edit, abort). Do not silently retry.
6. **Update the plan file**: append an `### Implementation log` block under that phase containing the agent's summary, list of changed files, and any deviations. Save so progress is durable.
7. If commit-per-phase is selected, commit now with a message naming the phase.
8. Move on to the next phase.

## Step 4: Final verification

After the last phase, regardless of the per-phase gate:

- `yarn build`
- `yarn format` (write fixes)
- `yarn lint`
- For each unit test suite whose source was modified during the run (`git diff --name-only $START_REF`), run that suite

Fix anything broken. If the fix is non-trivial, spawn another subagent of the same model.

## Step 5: Reviews (in parallel)

Kick off both reviewers in a single message:

1. **Opus review subagent** — `Agent` with `model: "opus"`, `subagent_type: "general-purpose"`. Brief on:
   - Plan path
   - Diff scope: `git diff $START_REF...HEAD` (or working-tree diff if no commits)
   - Ask for: correctness, missed plan items, regressions, risky changes, code quality. Tell it to be critical.
2. **Codex review** — invoke the `/codex` skill (this skill explicitly authorizes that). Prompt should include the plan path, the diff scope, the strictness mode chosen, and a critical-review ask.

## Step 6: Triage feedback

Combine feedback from both reviewers. For each item:

- **Clearly correct, low-risk** → fix it directly, or spawn a small subagent to fix.
- **Wrong / out of scope / hallucination** → note why and discard.
- **Debatable / judgment call** → add to a summary for the user.

If the summary is non-empty, present it: each item with reviewer source, your assessment, and a recommendation. Then ask the user how to proceed. Don't merge or push anything without explicit instruction.

## Notes

- Logging each phase's outcome into the plan file means the file doubles as a resume point if the run is interrupted.
- If an implementation subagent reports it couldn't finish a phase, treat it the same as a gate failure: stop and ask.
- Build/lint commands are written for yarn projects. If the repo uses npm, pnpm, cargo, go, etc., adapt the commands accordingly — the gate semantics stay the same.
