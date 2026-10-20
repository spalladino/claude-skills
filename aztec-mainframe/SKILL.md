---
name: aztec-mainframe
description: Run heavyweight aztec-packages or aztec-node work on Santiago's mainframe build box (santiago-box) over SSH instead of locally. Use for full bootstraps, compiling protocol circuits or Noir/L2 contracts, building barretenberg, regenerating verification keys, VK trees, generated types or rollup sample inputs, generating rollup or other real proofs, real-prover tests and benchmarks, or whenever the user mentions santiago-box or the mainframe.
argument-hint: "[aztec-packages|aztec-node] [branch or commit] [task]"
---

# Heavyweight Aztec Work on Santiago's Mainframe

Run resource-heavy aztec-packages and aztec-node work on `santiago-box` without disturbing an
existing checkout. Keep the work attached to an exact commit, preserve logs, and bring the result
back for review before landing it.

## Decide whether the mainframe is needed

Default to the mainframe for heavyweight work in either repository, unless the user asks to run it
locally:

- full or near-full bootstraps (`./bootstrap.sh`, `make fast`, `make labs-fast`, `make labs-full`);
- building barretenberg C++ or the Noir compiler;
- compiling protocol circuits, protocol contracts, aztec-nr, or the Noir/L2 contracts;
- regenerating VKs, the VK tree, generated types, genesis constants, or rollup sample inputs;
- generating rollup or other real proofs, real-prover tests, and benchmarks.

Edits, reading code, typechecks, and ordinary unit tests stay local. When unsure whether a task is
heavy enough, ask the user rather than starting a long local build.

## Delegate the remote operation

Delegate all SSH setup checks, remote worktree creation, building, monitoring, and result
collection to one `Agent` with `subagent_type: "general-purpose"` and `model: "sonnet"`. Give it
this entire skill, the target repository, exact commit, the requested task and outputs, and the
local worktree status. The parent agent resolves user decisions, reviews the returned result, and
independently checks it. Resume the same agent if it is blocked or the build needs diagnosis.

Do not have multiple subagents operate on the same remote worktree or tmux session.

## Establish the exact input

Determine the repository, branch, and exact commit from the request. Do not build an ambiguous
branch tip. Ensure the commit is reachable by the mainframe, normally through `origin`; if it is
only local, ask the user how they want to make it reachable before pushing or copying unpublished
work.

Inspect the local worktree first. Never overwrite local changes when importing generated output.

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
alias. Once connected, verify the machine with `hostname`, `nproc`, `free -g`, and `uptime`. The box
is shared: if it is already heavily loaded, tell the user before starting another large build.

## Create an isolated remote worktree

The canonical checkouts live under `/mnt/user-data/santiago/code/`:

- aztec-packages (`git@github.com:AztecProtocol/aztec-packages.git`): `aztec`.
- aztec-node (`git@github.com:aztec-labs-eng/aztec-node.git`): `aztec-node`. If it is absent,
  clone it there.

If a path is absent, list the directory and check each checkout's `origin` rather than assuming
a location. Never build in a canonical checkout itself; other sessions may be using it.

Fetch the target ref in the canonical checkout and verify that its resolved SHA equals the
expected commit. Create a uniquely named detached worktree under
`/mnt/user-data/santiago/code/worktrees/`, and initialize submodules if the build needs them. Use
that literal worktree path in later commands because shell variables do not persist between tool
calls. Before creating it, confirm the path and tmux session name are unused. Older worktrees may
still sit in `regen-worktrees/`; leave them alone.

Record the starting SHA and `git status --short` in the new worktree. If it is not clean, stop and
diagnose the collision.

## Choose the commands

Build targets move between versions, so read the `CLAUDE.md` or `AGENTS.md` in the remote
worktree, at the target commit, before choosing commands. Use the repository's documented
`make` targets, `bootstrap.sh` commands, and regeneration scripts; do not hand-edit generated
outputs those scripts own. If the right command is unclear, ask the user rather than guessing.

### Regenerating VKs

A change to `constants.nr` changes `BB_HASH`, so a cold VK recomputation is expected. Choose only
the requested modes, and confirm the build targets against the repository docs first:

- `artifacts`: build the yarn-project target, including protocol-circuit artifacts, VKs, VK tree,
  and generated TypeScript types (historically `./bootstrap.sh build yarn-project`).
- `sample-inputs`: after the artifact build, regenerate rollup `Prover.toml` inputs (historically
  `AZTEC_GENERATE_TEST_DATA=1 yarn --cwd yarn-project workspace @aztec/prover-client test
  src/test/regenerate_rollup_sample_inputs.test.ts`).
- `cache-seed`: prefix the build with `S3_FORCE_UPLOAD=1` to intentionally seed or replace entries
  in the shared S3 VK cache. Use this only when the user requested cache seeding or already
  authorized it.

## Run and monitor

Run long commands in a uniquely named detached tmux session and tee output to a unique log under
`/tmp`. Make the tmux command write the final exit code to a companion status file. Poll the tmux
session and tail the log at intervals; do not hold one blocking SSH command for the full build.

Do not infer success merely because tmux exited. Read the recorded exit status and inspect the end
of the log. On failure, preserve the worktree and log, report the failing command and useful error
context, and diagnose before retrying.

## Review and return the result

On success, collect the exact SHA, the commands and exit codes, `git status --short`,
`git diff --stat`, and the full changed-file list. For tasks that produce numbers rather than
files, such as proofs or benchmarks, collect the relevant log excerpts and measurements. Check that
any changes match the requested scope and that no source edits or unrelated files appeared.

Bring output back without touching the user's worktree first: copy the changed files or a binary
diff into a fresh local temporary directory, then compare it against the same starting SHA. Apply
it to the user's worktree only after checking for overlapping local changes. Do not commit, push,
or open a PR unless the user requested that action.

The parent agent must inspect the result and run proportionate local checks that do not repeat
the heavyweight work. Report the remote commit, commands and exit codes, changed files or
measurements, validation, and the retained log and worktree locations. Remove the isolated remote
worktree and temporary files only after the result has been safely retrieved and no further
diagnosis is needed.

## Local fallback

When the user asks to run VK generation locally, try the relevant build with
`HARDWARE_CONCURRENCY=8`; the historical local failure came from thread-dependent Pippenger arena
sizing. Remove the gitignored `barretenberg/ts/bb.js/src/cbind/generated` directory before a
bootstrap that rebuilds bb-ts if stale generated bindings make its formatting step fail.
