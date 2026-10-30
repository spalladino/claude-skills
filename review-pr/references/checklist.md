# checklist — what the review looks for, and what it leaves alone

Read by the main agent before forking, so every fork inherits it. Codex gets the same list.

## Ground rules for every finding

- **Cite the head.** `path:line` at the pinned head sha and the one or two lines that matter.
  A finding without a location is a hunch; keep it out or mark it `unverified`.
- **Show the failure, not the smell.** Bug: the concrete input or state, what the code does,
  what it should do. Design: what a reader holds in their head today and after the change.
- **Confidence:** `high` (traced the path, sure it fails), `medium` (likely, one assumption
  unverified, say which), `low` (worth a look, could be wrong; read as a question).
- **Severity for bugs:** `blocker` (wrong result, data loss, security, consensus or
  cryptographic error), `major` (real failure in a reachable case), `minor` (edge case,
  degraded behaviour, robustness).
- **Pre-existing vs introduced.** Say which and how you know. Pre-existing problems in touched
  code go in the "while you are here" list, not among the PR's bugs.
- **Skipped files.** The dossier lists lockfiles and generated files without hunks. Snapshot,
  fixture and gas-report diffs are behaviour evidence, not noise.

## Bugs — look for

- Off-by-one and boundaries: inclusive/exclusive ranges, empty inputs, first and last
  element, zero, overflow, negative numbers, unsigned wraparound.
- Ordering and atomicity: state written before a check, partial writes on failure, missing
  rollback, two writes that must be one transaction.
- Async and concurrency: unawaited promises, check-then-use races, shared mutable state,
  cancellation and timeouts, non-idempotent retries.
- Error handling: swallowed errors, catch blocks that continue with bad state, errors that
  change type across a boundary, missing propagation.
- Resource lifecycle: handles, listeners, timers, subscriptions, temp files, locks, cursors
  not released on every path.
- Contracts between modules: callers not updated for a changed signature, defaults that
  silently change meaning, serialised formats or storage keys changed without migration.
- Type and null safety: casts that hide a narrowing, `!` assertions, `any`, unchecked
  `undefined`, enum cases not handled after an enum grew.
- Wrong variable, copy-paste errors, inverted conditions, `&&`/`||` mixups.
- Security and consensus (a blockchain stack): validation moved or removed, trust
  assumptions changed, replay, unbounded input, gas or proof size, anything that changes
  what an honest node accepts.
- Tests: does the test test the change? Assertions that cannot fail, mocks that mask the
  path under test, snapshot updates that hide a behaviour change, tests deleted or skipped.
- Config, feature flags and defaults: changed defaults, env vars read in new places,
  migrations and rollout order.

## Contract claims — look for

Part of the BUGS remit. A comment, catch or mock that misstates what a callee does compiles
and passes, and the next change made on trust in it is silently wrong. Check every such claim
in code the PR adds or touches and in the lines around its hunks:

- **Claims in prose.** A comment, jsdoc or log message saying what a callee does: throws X,
  returns Y, never returns null, always runs after Z.
- **Handling for outcomes that cannot happen.** A catch, error-type check, `?? fallback` or
  `=== undefined` guard for an outcome the callee cannot produce (a catch for
  `NoCommitteeError` around `isInCommittee()`, which returns `false` instead). In tests, a
  mock that makes a dependency throw or return what the real one never does.
- **A changed contract with stale callers.** The PR makes a callee return a sentinel instead
  of throwing, or changes its nullability, and a caller's comment, catch or mock still
  describes the old contract. Find callers with `git grep`.

How to check: open the callee's body at head (each implementation an interface can reach)
and follow the path this call takes to where the claimed outcome would come from. The name,
the claim itself, or a grep hit for the error type elsewhere in the file is not evidence; the
throw or return must be on that path. Body out of reach (external package): use its type and
doc, confidence `low`. Report a contradicted claim as a bug citing the claim and the callee
line. Severity `major` when the PR's code or tests rely on the false claim, else `minor`. A
pre-existing claim the PR's change relies on counts as introduced; one it merely sits next to
goes under "while you are here".

## Design — look for

- Functions over ~60 lines or classes over ~400 that do more than one thing. A flat sequence
  is fine; call it out only when it hides branches.
- A module that gained a second responsibility, or logic far from the data it works on.
- Duplicated logic that could be one helper, especially when the PR added the second copy.
- Deep nesting, boolean parameters that select behaviour, long parameter lists, names that
  no longer say what the function does.
- Leaky abstractions: callers reaching into internals, types that expose implementation.
- Naming a newcomer would misread. Comments that say what instead of why, or are now wrong
  (a wrong claim about a callee belongs to §Contract claims).
- Complexity the PR could have avoided: an abstraction for one use, a config knob no one
  asked for, a generalisation with a single instance.
- **Semantics-changing simplifications.** When dropping a branch, fallback or edge case would
  make the code clearly simpler, propose it labelled `TRADEOFF:` with exactly what is lost
  and who would hit it. Never present one as a pure refactor.

## Decoherence — look for

Part of the DESIGN remit. Decoherence is redundant or incompatible models piling up until
changes cost mostly translation between them; fixes cause it when they patch around the model
instead of changing it. Evidence comes from `decoherence.md` and `fix-history.md`; the code
decides.

- **A special case instead of a model fix.** A new guard, exception, reason or fallback in a
  function that earlier fixes already patched the same way, or a fix that "adds without
  replacing" in an area whose 4-week score is high. Ask what single change to the model would
  make this case and the earlier ones unnecessary.
- **A second way.** A new helper, type, mapper or branch beside an existing one that does the
  same job, a fallback wrapped around an existing call, a reason defined in another map. The
  new path must name what it replaces and when the old one goes; say whether the PR should
  extend, replace or schedule removal of the old path.
- **Inline translation.** A consumer turning a result type back into an older shape
  (`x.state === 'a' ? x.value : []`) instead of handling the type or using the existing mapper.
- **Not decoherence:** an entry the compiler forces in an exhaustive typed map or `switch`; a
  new feature in new code; a fix that shrinks or replaces existing code; a catch or fallback
  for an outcome the callee cannot produce (that is §Contract claims). `decoherence.md`
  signals are prompts to look, never findings by themselves.

## Leave alone

- Formatting, import order, quote style, anything a linter or formatter enforces.
- Personal taste with no reader benefit you can name.
- Performance speculation without a reason the hot path is hot.
- Anything you did not check against the code. Turn it into a question for the reviewer.

## Thread status — how to judge

Cover every unresolved thread in `threads.md` **and** every top-level review or conversation
comment that asks for something (no line; `R` ids). A thread is the user's when they took
part in it, not only when they started it.

1. **Split the ask into obligations.** "Rename this and add a test" is two; "update the
   callers too" is one per place.
2. **Check each obligation at head, wherever it lives.** The `file changes since the comment`
   diff is where to start, not where to stop: the fix may sit in a caller, a helper, a test or
   a doc. `git grep` in the worktree when the anchor file did not change.
3. **Attribute separately.** "Met at head" is one fact; "introduced by commit `abc1234`" is
   another. After a rebase the commit list includes rewritten commits, so name a commit only
   when its diff shows the change.

Statuses:

- `addressed` — every obligation met at head. Cite the head lines always, the commit when
  you can.
- `partially addressed` — some met; name the missing ones.
- `acknowledged, pending` — the author agreed and nothing landed. Say whether a follow-up
  issue exists.
- `answered, no change` — the author explained why not. Quote the reply in one line.
- `not addressed` — no reply and no obligation met.
- `unclear` — you could not tell (original commit unfetchable, comment ambiguous); say why.

A force push is not evidence; only the code is. Threads GitHub marks `outdated` still need
this judgment, and a thread with no current line may be a file-level comment rather than
removed code.
