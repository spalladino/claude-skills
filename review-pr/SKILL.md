---
name: review-pr
description: Review a GitHub PR for a human reviewer with little context — explain what it does and why, how it does it, the bugs found by reading the code, design and simplification opportunities, and the exact status of every unresolved discussion. Read-only — never posts, replies, resolves or edits. Use when the user asks to review a PR ("review PR 123", "/review-pr 123 --codex"). Flags: --codex (second opinion), --tests [pattern] (bootstrap and run tests or benchmarks), --html (publish an artifact); "gc" cleans cached worktrees.
argument-hint: "<PR number> [--codex] [--tests [pattern]] [--html] | gc"
disable-model-invocation: true
---

# review-pr

**You are the reviewer. Your context is for understanding the change, not for `gh` output,
raw diffs or markup.** Clerical work goes to Sonnet subagents; the three judgment passes run
as forks of you, so the code is understood once and judged in parallel; a cold verifier then
tries to refute what the forks found.

## Ground rules

- **Read-only, everywhere.** Never post a comment or review, never react, resolve, label,
  approve, merge, push, or edit Linear. Never modify the worktree or the repo. Every
  subagent and codex prompt repeats the line below; keep it there:
  > Read-only: do not post, reply, react, resolve or edit anything on GitHub or Linear; do
  > not modify files in the worktree or repo; do not install dependencies, build, or run
  > tests. Your only output is the file named in this prompt.
- **Nothing runs unless asked.** No install, build, test or benchmark without `--tests`.
  No codex without `--codex`. No HTML without `--html`.
- **Cite the head.** Every claim about the code names `path:line` at the pinned head sha,
  as a permalink. A claim you could not verify is a question under "Not verified", never a
  finding.

## Paths

`$SKILL_DIR` = the absolute directory holding this file (resolve the symlink once; subagents
cannot guess it). `$WORK` = `${XDG_CACHE_HOME:-~/.cache}/review-pr/<slug>/`, slug
`<owner>-<repo>-pr-<n>` lower-case, stable across runs so a re-review after a push reuses the
worktree and keeps history.

```
$WORK/wt/                 # detached worktree at head, no deps installed (a cache; gc removes it)
$WORK/meta.json           # shas, state, permalink base, paths — read by gc.sh
$WORK/dossier.md          # PR body, commits, stat, every hunk with head line ranges
$WORK/threads.md          # every discussion, resolution state, per-thread diff since the comment
$WORK/threads-resolved.md # resolved threads in full
$WORK/linear.md           # linked Linear issues
$WORK/notes.md            # your understanding, written once before forking
$WORK/findings-{bugs,design,threads}.md   # returned by the forks as text, saved by you
$WORK/verify.md           # verdicts from the cold verifier
$WORK/review.md           # the deliverable
$WORK/history/            # previous review.md files, one per head
```

## Step 1 — gather (sonnet subagent)

```
Read <$SKILL_DIR>/references/gather.md and follow it exactly. You are the gather subagent.
Repo: <absolute repo root>. PR: <n>. Work dir: compute the slug per gather.md and return it.
<read-only line> Exception: you manage the cache under the work dir — the worktree, the
files gather.md names, and the worktrees gc removes.
Pin shas, check out the worktree, write meta.json, dossier.md, threads.md and linear.md,
run gc. Return ONLY the summary block from §7.
```

`Agent(subagent_type: "general-purpose", model: "sonnet")`. Do not run `gh` yourself, not
even to find the repo name for the slug; gather returns the work dir. If the summary says
the dossier is huge, still read it all; narrow only the code you open afterwards.

## Step 2 — understand (you)

Read, in this order: `references/checklist.md`, `references/report-format.md`,
`$WORK/dossier.md`, `$WORK/threads.md`, `$WORK/linear.md`. Then open code in `$WORK/wt` to
answer the questions a newcomer would ask: what does each touched module do, who calls it,
what invariant does the change lean on. Read whole functions around each hunk, and the
callers the dossier lists; stop there unless a specific question sends you further. What you
read here is inherited by three forks, so read what all three need and nothing more.

Write `$WORK/notes.md` (under ~80 lines): the goal in one sentence, the mechanism in
execution order, the modules and what changed in each, the invariants you believe the
change must keep, the places that worried you, and open questions. This is your own memo
and the forks' starting point.

Load `writing-well` (`Skill(skill: "writing-well")`) now; it governs every sentence you write
from here on.

## Step 3 — fork three judgments, write the explainer meanwhile

Dispatch all three in one message with `Agent(subagent_type: "fork")`. Forks inherit
everything you have read, so the prompts are short. **Forks return their findings as
text**: the harness blocks subagents from writing report files, and the findings have to
reach you anyway. Save each reply verbatim to its `findings-*.md` the moment it arrives; the
verifier reads the files.

Skip the THREADS fork only when `threads.md` has no unresolved threads and no top-level
review or comment that asks for something; §5 then says so in one line with the resolved
count.

```
You are the BUGS fork of review-pr. Using what you already understand plus the code in
<$WORK/wt> (head <sha>, base <sha>), hunt for defects introduced by this PR following
checklist.md §Bugs. Trace each candidate through the code until you can state the failing
input and the wrong output; drop what you cannot trace, or keep it as confidence low with
the unverified assumption named. Say for each whether the defect is new in this PR or
pre-existing (pre-existing ones go under "While you are here"). Write
your findings in the §3 format of report-format.md (ids B1…, permalinks from meta.json).
<read-only line> Return the findings text and nothing else: no preamble, no restatement of
the PR; the main agent saves it as findings-bugs.md.
```

```
You are the DESIGN fork of review-pr. Using what you already understand plus the code in
<$WORK/wt> (head <sha>), look for design and simplification opportunities following
checklist.md §Design: responsibilities, size, duplication, naming, abstractions the change
did not need, and semantics-changing simplifications labelled TRADEOFF with what is lost
and who hits it. Anchor each on path:line and show the simpler shape in a short sketch
when it helps. Return your findings in the §4 format of report-format.md (ids D1…) and
nothing else; the main agent saves it as findings-design.md. <read-only line>
```

```
You are the THREADS fork of review-pr. For every unresolved thread in <$WORK>/threads.md,
and every top-level review or conversation comment there that asks for something, decide
its status per checklist.md §Thread status: split the ask into obligations, check each at
head wherever it lives (git grep in <$WORK/wt> when the anchor file did not change), and
attribute to a commit only when its diff shows the change. Rows where <me> took part come
first. Fill the Remaining column for anything not addressed. Check the resolved list for a
thread that looks wrongly resolved. Return the §5 table and paragraphs of report-format.md
and nothing else; the main agent saves it as findings-threads.md. <read-only line>
```

While they run, write `$WORK/review.md` itself, not a scratch file: the header, a
placeholder line for "At a glance", sections 1 and 2 in full, and placeholder lines for
§3–§5 and "Not verified" that Step 7 replaces. Follow `report-format.md`. Section 1 speaks to someone who has never opened
the module: define terms, give one before/after scenario with the same explicit input on
both sides and real names from the code. Section 2 is the module table, the mechanism in
order, breaking changes, tests.

## Step 4 — verify the findings cold (opus subagent)

A reader who did not write the findings catches the confident misreads. Fresh agent, not
a fork:

```
You are the verify subagent for review-pr. Worktree: <$WORK/wt> at head <sha>; base sha
<sha> (use `git -C <$WORK/wt> show <base>:<path>` to see the code before the PR). Read
<$WORK>/findings-bugs.md, findings-design.md and findings-threads.md, and for each thread
row the original comments in <$WORK>/threads.md (the row's ask is a paraphrase; judge
against the reviewer's words). Do not read the PR body or dossier first; judge the code. For each bug: is the path reachable, is the input
possible, does a guard elsewhere prevent it, and did the PR introduce it or was it already
there at base. For each design item: is the simpler shape equivalent, and for a TRADEOFF, is
the stated loss the whole loss. For each thread row marked addressed or partially
addressed: does the cited head code actually meet the ask. Write <$WORK>/verify.md with one
line per id: <id>: confirmed | refuted — <why, path:line> | unverifiable — <what you would
need>. <read-only line> Return ONLY the counts.
```

`Agent(subagent_type: "general-purpose", model: "opus")`. Then, for §3–§4: refuted → drop,
unless you can answer the refutation from the code, in which case keep the finding and say
what the verifier checked; unverifiable → out of the section and into "Not verified" as a
question; confirmed → keep. For §5 every row stays: a refuted `addressed` becomes
`partially addressed` or `not addressed` with the verifier's evidence, an unverifiable one
becomes `unclear` with the reason.

## Step 5 — codex second opinion (only with `--codex`)

Load the `codex` skill and follow it. Point `-C` at `$WORK/wt`, default tier (`gpt-6-astra`,
`high`). The prompt gives codex: the paths of `dossier.md`, `threads.md`, `checklist.md` and
`report-format.md`, the head and base shas, the read-only line, and the instruction to look
for bugs, design issues and thread status in the §3–§5 formats and to be critical. Do
**not** show codex your findings in the first turn; an independent pass is the point.

Then match codex's findings to yours by claim and location, not by id (ids were assigned
independently); assign final ids after merging. For each disagreement (codex found something you did not, or
rejects something you kept), resume the **same** codex session once with your evidence and
ask it to confirm or withdraw. Verify any codex claim against the code before accepting
it. Section 6 records the agreements in one line and every disagreement that survived,
with both positions and your take. Accepted codex-only findings merge into §3–§4 tagged
`(codex)`.

## Step 6 — tests and benchmarks (only with `--tests`)

```
You are the tests subagent for review-pr. Worktree: <$WORK/wt> at head <sha>; it has no
dependencies installed. Bootstrap it the way the repo documents (CLAUDE.md, README,
bootstrap scripts), building only what the changed packages need: <list>. Then run
<the pattern the user gave, or the test files touching the changed files> and, if asked,
<benchmarks>. Report a table: command, pass/fail counts, each failure with its assertion,
benchmark numbers with base-vs-head deltas if you ran both. You may install, build and run
in the worktree; never commit, push, post anywhere, or change tracked files. Return ONLY
the table and any BLOCKED: lines.
```

`Agent(subagent_type: "general-purpose", model: "sonnet")`; switch to opus if the bootstrap
fails twice. Results go in §7 exactly as the table, and a failing test that matches a bug
finding is cross-referenced from it.

## Step 7 — assemble and report

Merge into `$WORK/review.md` per `report-format.md`: "At a glance" (now filled from the
verified findings and thread rows), your §1–§2, the verified §3–§5, optional §6–§7, and
"Not verified". Read it once as the reviewer would, with fifteen minutes: cut what does not
help them decide.

Your reply to the user is the path to `review.md` followed by its full content. No
preamble. If the user only wants a summary, they will say so.

## Step 8 — HTML artifact (only with `--html`)

Follow `references/html.md`: a sonnet subagent converts `review.md` mechanically into
`$WORK/review.html`; you publish it with the Artifact tool and give the URL.

## `gc`

`/review-pr gc` runs `bash $SKILL_DIR/scripts/gc.sh --keep 6 --days 7` and reports its
summary line. Gather runs the same command on every review after creating this run's
worktree, so the cache holds at most six worktrees, none older than a week, none for a
merged or closed PR. The markdown per slug is kept. `gc.sh --all` empties every worktree.

## Re-runs

Same PR again after new commits: gather moves the old `review.md` to `history/`, moves the
worktree to the new head, and rewrites the dossier and threads. In §5, a thread that was
`not addressed` last time and is `addressed` now names the commit. Add one line under the
header pointing at the previous review. Thread ids are per run; the thread url is the
stable reference.

## Feeding directions back into this skill

This is the one place this skill edits anything, and only in the skill's own repo, only
when the user gives a direction. When the user adjusts the output ("always list callers",
"shorter §1", "skip minor bugs"), apply it to `review.md`, then ask: is this general? If it
would improve the next review, edit the skill in the same turn — `checklist.md` for what to
look for, `report-format.md` for shape, `gather.md` for what to collect, this file for
process — and say which file changed. Requests about one PR only stay in that `review.md`.
