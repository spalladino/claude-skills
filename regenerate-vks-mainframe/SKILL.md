---
name: regenerate-vks-mainframe
description: Regenerate Aztec protocol-circuit artifacts, verification keys, VK trees, generated types, or rollup sample inputs on Santiago's mainframe build box. Use when the user asks to run VK regen on santiago-box or local regeneration lacks enough resources.
argument-hint: "[branch or commit] [artifacts|sample-inputs|cache-seed]"
---

# Regenerate VKs on Santiago's Mainframe

Run resource-heavy Aztec protocol-circuit regeneration on `santiago-box` without disturbing an
existing checkout. Keep the work attached to an exact commit, preserve logs, and bring the result
back for review before landing it.

## Delegate the remote operation

Delegate all SSH setup checks, remote worktree creation, regeneration, monitoring, and result
collection to one `Agent` with `subagent_type: "general-purpose"` and `model: "sonnet"`. Give it
this entire skill, the target repository, exact commit, requested outputs, and the local worktree
status. The parent agent resolves user decisions, reviews the returned diff, and independently
checks the result. Resume the same agent if it is blocked or the build needs diagnosis.

Do not have multiple subagents operate on the same remote worktree or tmux session.

## Decide whether the mainframe is needed

Local VK generation is often viable after the historical failure was traced to thread-dependent
Pippenger arena sizing. For ordinary local regeneration, try the relevant build with
`HARDWARE_CONCURRENCY=8`. Also remove the gitignored
`barretenberg/ts/bb.js/src/cbind/generated` directory before a bootstrap that rebuilds bb-ts if
stale generated bindings make its formatting step fail.

Use this mainframe workflow when the user explicitly requests it, local capacity is inadequate,
or the task is to seed the shared VK cache. A change to `constants.nr` changes `BB_HASH`, so a cold
VK recomputation is expected.

## Establish the exact input

Determine the branch and exact commit from the request and repository. Do not build an ambiguous
branch tip. Ensure the commit is reachable by the mainframe, normally through `origin`; if it is
only local, ask the user how they want to make it reachable before pushing or copying unpublished
work.

Inspect the local worktree first. Never overwrite local changes when importing generated output.

Choose only the requested modes:

- `artifacts`: build the yarn-project target, including protocol-circuit artifacts, VKs, VK tree,
  and generated TypeScript types.
- `sample-inputs`: regenerate rollup `Prover.toml` inputs after the artifact/VK build.
- `cache-seed`: add `S3_FORCE_UPLOAD=1` to intentionally seed or replace entries in the shared S3
  VK cache. Use this only when the user requested cache seeding or already authorized it.

## Check mainframe access

The host alias is `santiago-box` (or `santiago-fast-box` when the user requests the lower-latency
route). Both reach the same machine. First run:

```bash
ssh -O check santiago-box
```

If there is no live master, stop the remote attempt and ask the user to run this in an interactive
terminal and complete 2FA:

```bash
ssh -fN santiago-box
```

Do not attempt an ordinary interactive login from the agent; the ProxyJump 2FA prompt will hang.
The SSH config needs `ControlMaster auto`, a `ControlPath`, and a suitable `ControlPersist` for the
alias. Once connected, verify the machine with `hostname`, `nproc`, and `free -g`.

The canonical repository is `/mnt/user-data/santiago/code/aztec`. If it is absent, locate the
checkout rather than assuming `~/aztec-packages`.

## Create an isolated remote worktree

Fetch the target ref in the canonical repository and verify that its resolved SHA equals the
expected commit. Create a uniquely named detached worktree under
`/mnt/user-data/santiago/code/regen-worktrees/`; use that literal worktree path in later commands
because shell variables do not persist between tool calls. Before creating it, confirm the path
and tmux session name are unused.

Record the starting SHA and `git status --short` in the new worktree. If it is not clean, stop and
diagnose the collision.

## Run and monitor regeneration

Run long commands in a uniquely named detached tmux session and tee output to a unique log under
`/tmp`. Make the tmux command write the final exit code to a companion status file. Poll the tmux
session and tail the log at intervals; do not hold one blocking SSH command for the full build.

Run from the remote git root:

```bash
./bootstrap.sh build yarn-project
```

For `cache-seed`, run instead:

```bash
S3_FORCE_UPLOAD=1 ./bootstrap.sh build yarn-project
```

After a successful artifact build, run this only when `sample-inputs` was requested:

```bash
AZTEC_GENERATE_TEST_DATA=1 yarn --cwd yarn-project workspace @aztec/prover-client \
  test src/test/regenerate_rollup_sample_inputs.test.ts
```

Do not infer success merely because tmux exited. Read the recorded exit status and inspect the end
of the log. On failure, preserve the worktree and log, report the failing command and useful error
context, and diagnose before retrying.

## Review and return the result

On success, collect the exact SHA, `git status --short`, `git diff --stat`, and the full changed-file
list. Check that changes match the requested generation scope and that no source edits or unrelated
files appeared.

Bring output back without touching the user's worktree first: copy the changed files or a binary
diff into a fresh local temporary directory, then compare it against the same starting SHA. Apply
it to the user's worktree only after checking for overlapping local changes. Do not commit, push,
or open a PR unless the user requested that action.

The parent agent must inspect the resulting diff and run proportionate local checks that do not
repeat the resource-heavy generation. Report the remote commit, commands and exit codes, changed
files, validation, and the retained log/worktree locations. Remove the isolated remote worktree
and temporary files only after the result has been safely retrieved and no further diagnosis is
needed.
