---
name: review-pr
description: >-
  Review a GitHub PR for a human reviewer with little context — explain what it does and why, how it does it, the bugs found by reading the code, design and simplification opportunities, and the exact status of every unresolved discussion. Read-only by default — never posts, replies, resolves or edits; when the user names findings to post, drafts them via a sonnet and posts them as one signed GitHub review. Use when the user asks to review a PR ("review PR 123", "/review-pr 123 --codex") or, after a review, to post some of its findings. Flags: --codex (second opinion), --tests [pattern] (bootstrap and run tests or benchmarks), --html (publish an artifact), --fresh (ignore the last review of this PR and start over); "gc" cleans cached worktrees.
argument-hint: "<PR number> [--codex] [--tests [pattern]] [--html] [--fresh] | post <ids> as <comment|approve|request changes|pending> | gc"
disable-model-invocation: true
---

# review-pr

**You are the reviewer. Your context is for understanding the change, not for `gh` output,
raw diffs or markup.** Clerical work goes to Sonnet subagents; the three judgment passes run
as forks of you, so the code is understood once and judged in parallel; with `--codex`, codex
builds its own understanding alongside, so a misreading of yours cannot hide a bug from
everyone; a cold verifier then tries to refute what the forks and codex found.

## Ground rules

- **Read-only, everywhere.** Never post a comment or review, never react, resolve, label,
  approve, merge, push, or edit Linear. Never modify the worktree or the repo. The single
  exception is Step 8, which posts exactly the items the user named, as one review, after
  they have seen the drafts. Every subagent and codex prompt repeats the line below; keep it
  there:
  > Read-only: do not post, reply, react, resolve or edit anything on GitHub or Linear; do
  > not modify files in the worktree or repo; do not install dependencies, build, or run
  > tests. Your only output is what this prompt asks you to write or return.
- **Judgments come back as text.** The harness tells subagents not to write report or
  findings files; a file another tool consumes is fine. So gather writes the cache files
  (`fix-history.md` among them), the render subagent `review.html` and the drafter
  `post.json`; the forks and the verifier return text that you save verbatim; the tests
  subagent returns its table.
- **Nothing runs unless asked.** No install, build, test or benchmark without `--tests`.
  No codex without `--codex`. No HTML without `--html`.
- **Cite the head.** Every claim about the code names `path:line` at the pinned head sha,
  as a permalink. A claim you could not verify is a question under "Not verified", never a
  finding.

## Paths

`$SKILL_DIR` = the absolute directory holding this file (resolve the symlink once; subagents
cannot guess it). `$WORK` = `${XDG_CACHE_HOME:-~/.cache}/review-pr/<slug>/`, slug
`<owner>-<repo>-pr-<n>` lower-case, stable across runs so a re-review reuses the worktree and
builds on the last review (see Re-runs).

```
$WORK/wt/                 # detached worktree at head, no deps installed (a cache; gc removes it)
$WORK/meta.json           # shas, state, permalink base, paths — read by gc.sh
$WORK/dossier.md          # PR body, commits, stat, every hunk with head line ranges
$WORK/threads.md          # every discussion, resolution state, per-thread diff since the comment
$WORK/threads-resolved.md # resolved threads in full
$WORK/linear.md           # linked Linear issues
$WORK/decoherence.md      # flow signals and 4-week area fix history (decoherence script, run by gather)
$WORK/fix-history.md      # older fixes and checks around the touched functions, for the DESIGN fork (gather)
$WORK/notes.md            # your understanding, written once before forking
$WORK/findings-{bugs,design,threads}.md   # returned by the forks as text, saved by you
$WORK/findings-codex.md   # --codex only: codex's findings and its challenge-round reply, saved by you
$WORK/verify.md           # verdicts from the cold verifier, returned as text, saved by you
$WORK/review.md           # the deliverable
$WORK/review.done         # head sha of the last finished review, written at the end of Step 6
$WORK/interdiff.md        # incremental re-runs: what changed since the last reviewed head
$WORK/threads.prev.md     # same-head re-runs: threads.md as the last run left it
$WORK/post-plan.md, post.json  # Step 8 only: what to post, and the drafted comments
$WORK/history/<head7>/    # an earlier run's review.md, notes.md, findings, fix-history.md and verify.md
```

## Step 1 — gather (sonnet subagent)

```
Read <$SKILL_DIR>/references/gather.md and follow it exactly. You are the gather subagent.
Skill dir: <$SKILL_DIR>. Repo: <absolute repo root>. PR: <n>. Fresh: <yes if --fresh, else no>. Work dir: compute the
slug per gather.md and return it.
<read-only line> Exception: you manage the cache under the work dir — the worktree, the
files gather.md names, and the worktrees gc removes.
Pin shas, check out the worktree, write meta.json, dossier.md, threads.md, linear.md,
decoherence.md and fix-history.md, run gc. Return ONLY the summary block from §7.
```

`Agent(subagent_type: "general-purpose", model: "sonnet")`. Do not run `gh` yourself, not
even to find the repo name for the slug; gather returns the work dir. If the summary says
the dossier is huge, still read it all; narrow only the code you open afterwards.

The summary's `mode:` line decides how much of Steps 1b–6 runs; for `same-head` and
`incremental` read Re-runs below before Step 1b.

## Step 1b — dispatch codex (only with `--codex`)

Codex reviews bugs and design independently: it never sees `notes.md` or the forks' work,
so it can catch what a wrong understanding of yours hides from all three forks. It does not
judge threads; the THREADS fork owns them. Dispatch it as soon as gather returns, before
Step 2, so it runs while you read.

Load the `codex` skill and follow it: a fresh `mktemp` dir, `gpt-6-astra` at `high`,
`--sandbox read-only`, `-C <$WORK/wt>`, run in the background. Write this prompt verbatim,
filling the brackets:

```
You are an independent reviewer of PR <n> in <owner/repo>. Your working directory is a
worktree at the PR head <sha>; the base is <sha> (`git show <base>:<path>` shows a file
before the PR, `git diff <base>...HEAD` shows the change). Read <$WORK>/dossier.md (PR body,
commits, every hunk with head line ranges), <$WORK>/linear.md (linked issues) and, if
present, <$WORK>/decoherence.md (flow signals and the 4-week fix history of the areas the PR
touches), then §Bugs, §Contract claims, §Design and §Decoherence of
<$SKILL_DIR>/references/checklist.md. Build your own understanding from the code: what each
touched module does, who calls it, what invariants the change must keep.

Then find:
1. Bugs this PR introduces. Trace each through the code to a failing input and the wrong
   output; drop what you cannot trace, or keep it at confidence low with the unverified
   assumption named. Open a callee's body before trusting any comment, catch or mock about
   what it does. Pre-existing defects go under "While you are here".
2. Design and simplification opportunities: responsibilities, size, duplication, naming,
   abstractions the change did not need; semantics-changing simplifications labelled
   TRADEOFF with what is lost and who hits it; special cases or second ways added instead
   of fixing the model, naming the existing path and citing earlier fixes from git log.
Do not review discussion threads or reviewer comments; another reviewer covers them.

Be critical: try to break the change before you call it correct. Cite every claim as
path:line at head. Use the §3 and §4 formats of <$SKILL_DIR>/references/report-format.md,
with ids CB1… for bugs, CP1… for "While you are here" and CD1… for design; say so when a
section is empty. Return the
findings as your final message and nothing else.
<read-only line>
```

Keep the codex dir and session id for Step 3b.

## Step 2 — understand (you)

Read, in this order: `references/checklist.md`, `references/report-format.md`,
`$WORK/dossier.md`, `$WORK/threads.md`, `$WORK/linear.md`, `$WORK/decoherence.md`. Then open
code in `$WORK/wt` to answer the questions a newcomer would ask: what does each touched module do, who calls it,
what invariant does the change lean on. Read whole functions around each hunk, and the
callers the dossier lists; stop there unless a specific question sends you further. When a
comment or catch near a hunk says what a callee does, open the callee before you repeat the
claim in `notes.md`. What you read here, and what you believe, is inherited by three forks,
so read what all three need and nothing more.

Write `$WORK/notes.md` (under ~80 lines): the goal in one sentence, the mechanism in
execution order, the modules and what changed in each, the invariants you believe the
change must keep, the places that worried you, and open questions. This is your own memo
and the forks' starting point.

If the `writing-well` skill is available, load it now (`Skill(skill: "writing-well")`); it is
optional, and without it follow the plain-prose rules in `report-format.md`. It governs every sentence you write
from here on.

## Step 3 — fork three judgments, write the explainer meanwhile

Dispatch all three in one message with `Agent(subagent_type: "fork")`. Forks inherit everything you have read, so the prompts are short. **Forks return their findings as
text** (Ground rules). Save each reply verbatim to its `findings-*.md` the moment it arrives;
the verifier reads the files.

Skip the THREADS fork only when `threads.md` has no unresolved threads and no top-level
review or comment that asks for something; §5 then says so in one line with the resolved
count.

```
You are the BUGS fork of review-pr. Using what you already understand plus the code in
<$WORK/wt> (head <sha>, base <sha>), hunt for defects introduced by this PR following
checklist.md §Bugs, and check every claim about a callee per §Contract claims by opening
the callee's body. Trace each candidate through the code until you can state the failing
input and the wrong output; drop what you cannot trace, or keep it as confidence low with
the unverified assumption named. Say for each whether the defect is new in this PR or
pre-existing (pre-existing ones go under "While you are here", ids P1…). Write
your findings in the §3 format of report-format.md (ids B1…, permalinks from meta.json).
<read-only line> Return the findings text and nothing else: no preamble, no restatement of
the PR; the main agent saves it as findings-bugs.md.
```

```
You are the DESIGN fork of review-pr. Using what you already understand plus the code in
<$WORK/wt> (head <sha>), look for design and simplification opportunities following
checklist.md §Design: responsibilities, size, duplication, naming, abstractions the change
did not need, and semantics-changing simplifications labelled TRADEOFF with what is lost
and who hits it. Also judge decoherence per checklist.md §Decoherence: does this PR add a
special case, a branch or a second way of doing something instead of fixing the model? Use
<$WORK>/decoherence.md (the PR's flow signals and the 4-week fix history of the areas it
touches) and <$WORK>/fix-history.md when it exists. When you flag one, name the existing
path the new one should replace or extend, and cite the evidence (earlier fixes by PR, the
copied check). Anchor each on path:line and show the simpler shape in a short sketch
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

While they run, in `full` and `incremental` mode, write `$WORK/review.md` itself, not a
scratch file: the header, a placeholder line for "At a glance", sections 1 and 2 in full, and
placeholder lines for §3–§5 and "Not verified" that Step 6 replaces (`same-head` edits the
last review in place; see Re-runs). Follow `report-format.md`. Section 1 speaks to someone who has never opened
the module: define terms, give one before/after scenario with the same explicit input on
both sides and real names from the code. Section 2 is the module table, the mechanism in
order, breaking changes, tests.

## Step 3b — challenge codex (only with `--codex`)

Once the forks are in, wait for codex and save its final message verbatim to
`$WORK/findings-codex.md`. Match its findings to the BUGS and DESIGN findings, `P` items
included, by claim and location, not by id. Write the match at the top of the file under
`## Match`, one line per codex id: `CB2 = B3` (same finding), `CB1 ≠ B2` (same place,
opposite claims), `CD3 = none` (codex only).

Then resume the **same** codex session once (codex skill, "Following up"). `codex exec
resume` takes no `-C` and a `cd` does not persist between Bash calls, so run it as one
command: `cd <$WORK/wt> && codex exec resume <session id> …`. The follow-up opens with "You
are still in the worktree <$WORK/wt> at head <sha>." and pastes:
- the BUGS and DESIGN findings it did not raise, from `findings-bugs.md` and
  `findings-design.md`: is each real or wrong? Cite path:line either way.
- each codex finding you doubt, with your evidence from the code: confirm or withdraw.

Append its reply to `findings-codex.md` under `## Challenge round`. Drop nothing yourself
here; the verifier judges what survives.

## Step 4 — verify the findings cold (opus subagent)

A reader who did not write the findings catches the confident misreads. Fresh agent, not
a fork:

```
You are the verify subagent for review-pr. Worktree: <$WORK/wt> at head <sha>; base sha
<sha> (use `git -C <$WORK/wt> show <base>:<path>` to see the code before the PR). Read
<$WORK>/findings-bugs.md, findings-design.md and findings-threads.md, and for each thread
row the original comments in <$WORK>/threads.md (the row's ask is a paraphrase; judge
against the reviewer's words). Do not read the PR body or dossier first; judge the code. A design
item that cites earlier fixes or a copied check: confirm it with git log and
<$WORK>/fix-history.md. For each bug and each "While you are here" item (P…): is the path
reachable, is the input possible, does a guard elsewhere prevent it, and did the PR
introduce it or was it already there at base. For a stale-claim bug: open the cited callee
line and confirm the claimed outcome cannot happen on the path the call takes. For each
design item: is the simpler shape equivalent, and for a TRADEOFF, is the stated loss the
whole loss. For each thread row (T…, R…): if it says addressed or partially addressed, does
the cited head code meet the ask; if it says nothing landed (not addressed, acknowledged,
pending, answered, no change), is the ask met anywhere at head (git grep: the fix may sit in
another file). If <$WORK>/findings-codex.md exists, it holds an independent reviewer's
findings (CB…, CP…, CD…), a `## Match` map to the fork ids, and a challenge round. Judge
every codex id it did not withdraw the same way. Give each `=` pair one verdict on one line
(`B3 = CB2: …`); for a `≠` pair, say which claim the code supports. Where the challenge round
calls a B, P or D finding wrong, weigh its argument in that finding's verdict.
<read-only line> Return one line per id and nothing else; the main agent saves it as
verify.md: <id>: confirmed | refuted — <why, path:line> | unverifiable — <what you would
need>.
```

`Agent(subagent_type: "general-purpose", model: "opus")`. Save its reply verbatim to
`$WORK/verify.md`. Then, for §3–§4 and "While you are here": confirmed → keep; unverifiable
→ out of the section and into "Not verified" as a question; refuted → drop. To keep a
refuted finding, send the verifier your counter-evidence once (`SendMessage` to the same
agent) and append its answer to `verify.md` as `<id> (round 2): …`; that verdict stands.
Without that round, the finding goes to "Not verified" with both positions. For §5 every row
stays: a refuted `addressed` becomes `partially addressed` or `not addressed` with the
verifier's evidence, a refuted `not addressed` (or pending, no change) becomes `addressed` or
`partially addressed` with the head code it found, an unverifiable one becomes `unclear` with
the reason.

Codex findings follow the same rules. Fork ids are final. An `=` pair stays one finding
under the fork id. A confirmed codex-only finding joins §3–§4 tagged `(codex)` under the next
free B, P or D number, after the highest fork id of this run (in `incremental`, fork ids
already number after the prior ones); add the new id to its match line: `CD3 = none → D4`.
§6 records the agreements in one line, then every disagreement that survived: a codex
objection to a finding you kept, a `≠` pair, or a codex finding the verifier refuted, with
both positions, the verifier's verdict and your take.

## Step 5 — tests and benchmarks (only with `--tests`)

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

## Step 6 — assemble and report

Merge into `$WORK/review.md` per `report-format.md`: "At a glance" (now filled from the
verified findings and thread rows), your §1–§2, the verified §3–§5, optional §6–§7, and
"Not verified". Read it once as the reviewer would, with fifteen minutes: cut what does not
help them decide.

Last, write the head sha to `$WORK/review.done`; the next run builds on this review only if it
finished. Your reply to the user is the path to `review.md` followed by its full content. No
preamble. If the user only wants a summary, they will say so.

## Step 7 — HTML artifact (only with `--html`)

Follow `references/html.md`: a sonnet subagent converts `review.md` mechanically into
`$WORK/review.html`; you publish it with the Artifact tool and give the URL.

## Step 8 — post comments (only when the user names what to post)

Follow `references/post.md`. The user picks the items and the review action (`comment`,
`approve`, `request changes`, `pending`); if the action is missing, ask. You write the
points, a sonnet drafts the wording into `post.json`, you check every sentence, show the
dry-run, and on their go run `scripts/post_review.py`, which posts everything as **one**
review pinned to the reviewed head and signs each comment `_Written by Claude_`. `pending` leaves the review open for them
to submit from the web.

## `gc`

`/review-pr gc` runs `bash $SKILL_DIR/scripts/gc.sh --keep 6 --days 7` and reports its
summary line. Gather runs the same command on every review after creating this run's
worktree, so the cache holds at most six worktrees, none older than a week, none for a
merged or closed PR. The markdown per slug is kept. `gc.sh --all` empties every worktree.

## Re-runs

The user often re-reviews a PR they reviewed before. Gather's `mode:` line says how much of
the last run to reuse. `full` runs Steps 1b–6 as written; `--fresh` forces it, and gather
falls back to it when the last run did not finish or the interdiff is too big. In every
mode, "At a glance" opens with the prior-review line and its delta (report-format.md).
Thread ids are per run; the thread url is the stable reference.

**`same-head`.** The code has not moved, so the last review's understanding and §1–§4
stand.
- Step 2: read `notes.md`, `review.md` and `threads.md`. Open code only where a new thread
  points.
- Step 3: no BUGS or DESIGN fork. Run the THREADS fork only when gather says
  `threads changed: yes`, and add to its prompt: "The last run's threads are in
  <$WORK>/threads.prev.md and its §5 in <$WORK>/review.md; re-judge only the threads that
  changed or are new, and carry the other rows over. Match a carried row to its thread by
  url and give it that thread's T id in this run's threads.md. End with one line
  `re-judged: <ids>`."
- Steps 1b and 3b: only when `--codex` was given and the last review has no §6. The
  challenge round pastes §3–§4 of `review.md` in place of the fork findings, and the match
  map uses its ids.
- Step 4: skip it when neither the THREADS fork nor codex ran. Otherwise verify only the
  rows on the fork's `re-judged:` line, and the codex findings if
  codex ran. Tell the verifier: "findings-bugs.md and findings-design.md are from the last
  run and already judged in verify.md; do not re-judge them. Read findings-codex.md, the
  re-judged rows of findings-threads.md, and for the B, P and D ids codex matches or
  challenges, §3–§4 of <$WORK>/review.md." Merge its reply into `verify.md`: replace the
  lines of the ids it judged, add new ones, keep the rest, and renumber T lines to this
  run's ids.
- Step 5: only when `--tests` was given and the last review has no §7.
- Step 6: edit `review.md` in place: the header (date, CI, state), "At a glance", §5, and
  §3, §4 and §6 if codex ran.

**`incremental`.** The head moved by a small interdiff. Start from the last run's
understanding, then re-check its findings at the new head. The last review lives in
`$WORK/history/<old7>/`.
- Step 1b: add to the codex prompt: "The PR was reviewed before at <old sha>; focus on
  <$WORK>/interdiff.md and the code it interacts with."
- Step 2: read checklist.md, report-format.md, `history/<old7>/notes.md` and `review.md`,
  `interdiff.md`, `threads.md`, `linear.md`, `decoherence.md`, and the dossier header plus the
  dossier sections of the files the interdiff touches. Open the code around each interdiff hunk and the
  callers of what it changes. Write `notes.md` as the old memo brought up to the new head,
  with what changed marked.
- Step 3: all three forks run. Add to the BUGS and DESIGN prompts: "Your prior findings are
  §3 (BUGS) or §4 (DESIGN) of <$WORK>/history/<old7>/review.md, the verified set. For each
  prior id, state its status at head: fixed (cite the change), still present (re-cite at
  head), or moot (the code is gone). Then hunt for new ones in <$WORK>/interdiff.md and in the
  code it interacts with; do not re-review code the interdiff leaves alone. Keep prior ids
  and number new ones after the highest prior id." The THREADS fork runs as in `full`; add to
  its prompt: "The last review's §5 is in <$WORK>/history/<old7>/review.md. Match its rows
  to threads by url; for a row that was `not addressed` there, name the commit that
  addressed it, if any (its diff must show the change)."
- Step 4: add to the verifier prompt that it reads `interdiff.md` too, and checks every
  fixed and still-present claim as well as the new findings.
- Step 6: per report-format.md: §1–§2 start from the last review's text, carried findings
  say since when they are open, and each section ends with what got fixed.

## Feeding directions back into this skill

This is the one place this skill edits anything, and only in the skill's own repo, only
when the user gives a direction. When the user adjusts the output ("always list callers",
"shorter §1", "skip minor bugs"), apply it to `review.md`, then ask: is this general? If it
would improve the next review, edit the skill in the same turn — `checklist.md` for what to
look for, `report-format.md` for shape, `gather.md` for what to collect, this file for
process — and say which file changed. Requests about one PR only stay in that `review.md`.
