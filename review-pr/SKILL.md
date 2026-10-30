---
name: review-pr
description: >-
  Review a GitHub PR for a human reviewer with little context — explain what it does and why, how it does it, the bugs found by reading the code, design and simplification opportunities, and the exact status of every unresolved discussion. Read-only by default — never posts, replies, resolves or edits; when the user names findings to post, drafts them via a sonnet and posts them as one signed GitHub review. Use when the user asks to review a PR ("review PR 123", "/review-pr 123 --codex") or, after a review, to post some of its findings. Flags: --codex (second opinion), --tests [pattern] (bootstrap and run tests or benchmarks), --html (publish an artifact), --fresh (ignore the last review of this PR and start over); "gc" cleans cached worktrees.
argument-hint: "<PR number> [--codex] [--tests [pattern]] [--html] [--fresh] | post <ids> as <comment|approve|request changes|pending> | gc"
disable-model-invocation: true
---

# review-pr

**You are the reviewer. Your context is for understanding the change, not for `gh` output,
raw diffs or markup.** Sonnet subagents do the clerical work; three forks of you judge in
parallel so the code is understood once; with `--codex`, codex builds its own understanding
alongside so a misreading of yours cannot hide a bug from everyone; a cold verifier then tries
to refute what they found.

## Ground rules

- **Read-only, everywhere.** Never post, reply, react, resolve, label, approve, merge, push,
  or edit Linear; never modify the worktree or the repo. The one exception is Step 8, which
  posts exactly what the user named, after they saw the drafts. `<read-only line>` in every
  prompt below stands for:
  > Read-only: do not post, reply, react, resolve or edit anything on GitHub or Linear; do
  > not modify files in the worktree or repo; do not install dependencies, build, or run
  > tests. Your only output is what this prompt asks you to write or return.
- **Judgments come back as text.** The harness discourages subagents from writing report
  files, so forks and the verifier return text that you save verbatim. Gather, render and the
  drafter write files that other tools consume.
- **Nothing runs unless asked.** No codex without `--codex`, no install, build or test without
  `--tests`, no HTML without `--html`.
- **Cite the head.** Every claim names `path:line` at the pinned head sha, as a permalink.
  What you could not verify is a question under "Not verified", never a finding.

## Paths

`$SKILL_DIR` = this file's directory, symlink resolved (subagents cannot guess it). `$WORK` =
`${XDG_CACHE_HOME:-~/.cache}/review-pr/<owner>-<repo>-pr-<n>/`, lower case, computed by
gather. It is stable across runs, so a re-review reuses the worktree and the last review.

```
$WORK/wt/                 # detached worktree at head, no deps installed (gc removes it)
$WORK/meta.json           # shas, state, permalink bases, mode (gather; gc.sh reads it)
$WORK/dossier.md, threads.md, threads-resolved.md, linear.md, decoherence.md, fix-history.md   # gather
$WORK/notes.md            # your understanding, written once before forking
$WORK/findings-{bugs,design,threads,codex}.md, verify.md   # returned as text, saved by you
$WORK/review.md           # the deliverable; review.done holds its head sha once finished
$WORK/interdiff.md        # incremental: what changed since the last reviewed head
$WORK/threads.prev.md     # same-head: threads.md as the last run left it
$WORK/post-plan.md, post.json   # Step 8
$WORK/history/<old7>/     # the last run's review.md, notes.md, findings, fix-history.md, verify.md
```

## Modes

Gather's `mode:` line decides how much of Steps 1b–6 runs. Thread ids are per run; the thread
url is the stable reference. In every mode "At a glance" opens with the prior-review line
and its delta (report-format.md).

| Mode | When | What runs |
|---|---|---|
| `full` | first run, `--fresh`, last run unfinished, old head gone, interdiff too big | every step as written, `<prior …>` slots empty |
| `incremental` | head moved by a small interdiff; last review in `history/<old7>/` | every step, `<prior …>` slots filled; §1–§2 start from the last review's text |
| `same-head` | head unchanged; the last review's understanding and §1–§4 stand | Step 2: read `notes.md`, `review.md`, `threads.md`, open code only where a new thread points. Step 3: THREADS fork only, and only if gather says `threads changed: yes`. Steps 1b/3b: only with `--codex` and no §6 in the last review; the challenge round pastes §3–§4 of `review.md` in place of fork findings and the match map uses those ids. Step 4: only if THREADS or codex ran. Step 5: only with `--tests` and no §7. Step 6: edit `review.md` in place (header, "At a glance", §5, and §3, §4, §6 if codex ran). |

`<prior …>` slot texts:

- `<prior codex>` (incremental): "The PR was reviewed before at <old sha>; focus on
  <$WORK>/interdiff.md and the code it interacts with."
- `<prior findings>` (incremental, BUGS and DESIGN): "Your prior findings are §3 (BUGS) or §4
  (DESIGN) of <$WORK>/history/<old7>/review.md, the verified set. For each prior id, state its
  status at head: fixed (cite the change), still present (re-cite at head), or moot (the code
  is gone). Then hunt for new ones in <$WORK>/interdiff.md and the code it interacts with; do
  not re-review code the interdiff leaves alone. Keep prior ids and number new ones after the
  highest prior id."
- `<prior threads>` (incremental): "The last review's §5 is in <$WORK>/history/<old7>/review.md.
  Match its rows to threads by url; for a row that was `not addressed` there, name the commit
  that addressed it, if any (its diff must show the change)."
  (same-head): "The last run's threads are in <$WORK>/threads.prev.md and its §5 in
  <$WORK>/review.md; re-judge only the threads that changed or are new, and carry the other
  rows over. Match a carried row to its thread by url and give it that thread's T id in this
  run's threads.md. End with one line `re-judged: <ids>`."
- `<prior verify>` (incremental): "Read <$WORK>/interdiff.md too, and check every fixed and
  still-present claim as well as the new findings."
  (same-head): "findings-bugs.md and findings-design.md are from the last run and already
  judged in verify.md; do not re-judge them. Read findings-codex.md, the re-judged rows of
  findings-threads.md, and for the B, P and D ids codex matches or challenges, §3–§4 of
  <$WORK>/review.md." Merge its reply into `verify.md`: replace the lines of the ids it
  judged, add new ones, keep the rest, renumber T lines to this run's ids.

## Step 1 — gather (sonnet subagent)

`Agent(subagent_type: "general-purpose", model: "sonnet")`:

```
Read <$SKILL_DIR>/references/gather.md and follow it exactly. You are the gather subagent.
Skill dir: <$SKILL_DIR>. Repo: <absolute repo root>. PR: <n>. Fresh: <yes if --fresh, else no>.
Work dir: compute the slug per gather.md and return it.
<read-only line> Exception: you manage the cache under the work dir — the worktree, the
files gather.md names, and the worktrees gc removes.
Return ONLY the summary block from §10.
```

Do not run `gh` yourself, not even for the repo name. If the summary says the dossier is
huge, still read it all; narrow only the code you open afterwards.

## Step 1b — dispatch codex (only with `--codex`)

Codex reviews bugs and design independently: it never sees `notes.md` or the forks' work and
does not judge threads. Dispatch it as soon as gather returns, so it runs while you read.

Load the `codex` skill and follow it: a fresh `mktemp` dir, `gpt-6-astra` at `high`,
`--sandbox read-only`, `-C <$WORK/wt>`, in the background. Keep the dir and session id for
Step 3b. Prompt, verbatim:

```
You are an independent reviewer of PR <n> in <owner/repo>. Your working directory is a
worktree at the PR head <sha>; the base is <sha> (`git show <base>:<path>` shows a file
before the PR, `git diff <base>...HEAD` shows the change). Read <$WORK>/dossier.md (PR body,
commits, every hunk with head line ranges), <$WORK>/linear.md (linked issues) and, if
present, <$WORK>/decoherence.md (flow signals and the 4-week fix history of the areas the PR
touches), then §Ground rules, §Bugs, §Contract claims, §Design, §Decoherence and §Leave
alone of <$SKILL_DIR>/references/checklist.md. Build your own understanding from the code:
what each touched module does, who calls it, what invariants the change must keep.

Then find (1) bugs this PR introduces: trace each to a failing input and the wrong output,
drop what you cannot trace or keep it at confidence low with the unverified assumption
named, open a callee's body before trusting any comment, catch or mock about it, and put
pre-existing defects under "While you are here"; (2) design and simplification
opportunities per §Design, TRADEOFF-labelled when semantics change, and special cases or
second ways added instead of fixing the model, naming the existing path and citing earlier
fixes from git log. Do not review discussion threads; another reviewer covers them.
<prior codex>

Be critical: try to break the change before you call it correct. Cite every claim as
path:line at head. Use the §3 and §4 formats of <$SKILL_DIR>/references/report-format.md,
with ids CB1… for bugs, CP1… for "While you are here" and CD1… for design; say so when a
section is empty. Return the findings as your final message and nothing else.
<read-only line>
```

## Step 2 — understand (you)

Read, in this order: `references/checklist.md`, `references/report-format.md`,
`$WORK/dossier.md`, `threads.md`, `linear.md`, `decoherence.md`. Then open code in `$WORK/wt`
to answer what a newcomer would ask: what each touched module does, who calls it, what
invariant the change leans on. Read whole functions around each hunk and the callers the
dossier lists; stop there unless a specific question sends you further. When a comment or
catch near a hunk says what a callee does, open the callee before repeating the claim. Three
forks inherit what you read, so read what all three need and nothing more.

Incremental: read `history/<old7>/notes.md` and `review.md`, `interdiff.md`, and the dossier
header plus the sections of the files the interdiff touches, instead of the whole dossier.
Open the code around each interdiff hunk and the callers of what it changes.

Write `$WORK/notes.md` (under ~80 lines): the goal in one sentence, the mechanism in
execution order, the modules and what changed in each, the invariants the change must keep,
the places that worried you, open questions. Incremental: the old memo brought up to the new
head, with what changed marked.

Load the `writing-well` skill if available (`Skill(skill: "writing-well")`); it governs every
sentence from here on. Without it, follow the prose rules in `report-format.md`.

## Step 3 — fork three judgments, write the explainer meanwhile

Dispatch all three in one message with `Agent(subagent_type: "fork")`. Save each reply
verbatim to its `findings-*.md` the moment it arrives; the verifier reads the files. Skip the
THREADS fork when `threads.md` has no unresolved thread and no top-level ask; §5 then says so
in one line with the resolved count.

```
You are the BUGS fork of review-pr. Using what you already understand plus the code in
<$WORK/wt> (head <sha>, base <sha>), hunt for defects introduced by this PR following
checklist.md §Bugs, and check every claim about a callee per §Contract claims by opening
the callee's body. Trace each candidate through the code until you can state the failing
input and the wrong output; drop what you cannot trace, or keep it as confidence low with
the unverified assumption named. Say for each whether the defect is new in this PR or
pre-existing (pre-existing ones go under "While you are here", ids P1…). <prior findings>
Write your findings in the §3 format of report-format.md (ids B1…, permalinks from
meta.json). <read-only line> Return the findings text and nothing else: no preamble, no
restatement of the PR; the main agent saves it as findings-bugs.md.
```

```
You are the DESIGN fork of review-pr. Using what you already understand plus the code in
<$WORK/wt> (head <sha>), look for design and simplification opportunities following
checklist.md §Design: responsibilities, size, duplication, naming, abstractions the change
did not need, and semantics-changing simplifications labelled TRADEOFF with what is lost
and who hits it. Also judge decoherence per checklist.md §Decoherence: does this PR add a
special case, a branch or a second way of doing something instead of fixing the model? Use
<$WORK>/decoherence.md and <$WORK>/fix-history.md when it exists. When you flag one, name
the existing path the new one should replace or extend, and cite the evidence (earlier
fixes by PR, the copied check). Anchor each on path:line and show the simpler shape in a
short sketch when it helps. <prior findings> Return your findings in the §4 format of
report-format.md (ids D1…) and nothing else; the main agent saves it as findings-design.md.
<read-only line>
```

```
You are the THREADS fork of review-pr. For every unresolved thread in <$WORK>/threads.md,
and every top-level review or conversation comment there that asks for something, decide
its status per checklist.md §Thread status: split the ask into obligations, check each at
head wherever it lives (git grep in <$WORK/wt> when the anchor file did not change), and
attribute to a commit only when its diff shows the change. Rows where <me> took part come
first. Fill the Remaining column for anything not addressed. Check the resolved list for a
thread that looks wrongly resolved. <prior threads> Return the §5 table and paragraphs of
report-format.md and nothing else; the main agent saves it as findings-threads.md.
<read-only line>
```

While they run, write `$WORK/review.md` itself per `report-format.md`: the header, a
placeholder for "At a glance", §1 and §2 in full, placeholders for §3–§5 and "Not verified".

## Step 3b — challenge codex (only with `--codex`)

Once the forks are in, wait for codex and save its final message verbatim to
`$WORK/findings-codex.md`. Match its findings to the BUGS and DESIGN findings, `P` items
included, by claim and location, not by id, and write the map at the top of the file under
`## Match`, one line per codex id: `CB2 = B3` (same finding), `CB1 ≠ B2` (same place,
opposite claims), `CD3 = none` (codex only).

Resume the **same** codex session once (codex skill, "Following up"). `codex exec resume`
takes no `-C` and `cd` does not persist between Bash calls, so run
`cd <$WORK/wt> && codex exec resume <session id> …` as one command. The follow-up opens with
"You are still in the worktree <$WORK/wt> at head <sha>." and pastes:
- the BUGS and DESIGN findings it did not raise: is each real or wrong? Cite path:line.
- each codex finding you doubt, with your evidence from the code: confirm or withdraw.

Append its reply to `findings-codex.md` under `## Challenge round`. Drop nothing yourself;
the verifier judges what survives.

## Step 4 — verify the findings cold (opus subagent)

`Agent(subagent_type: "general-purpose", model: "opus")`, a fresh agent, not a fork. Save its
reply verbatim to `$WORK/verify.md`.

```
You are the verify subagent for review-pr. Worktree: <$WORK/wt> at head <sha>; base sha
<sha> (`git -C <$WORK/wt> show <base>:<path>` shows the code before the PR). Read
<$WORK>/findings-bugs.md, findings-design.md and, if present, findings-threads.md, and for
each thread row the original comments in <$WORK>/threads.md (the row's ask is a paraphrase;
judge against the reviewer's words). Do not read the PR body or dossier first; judge the
code. A design item that cites earlier fixes or a copied check: confirm it with git log and
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
calls a B, P or D finding wrong, weigh its argument in that finding's verdict. <prior verify>
<read-only line> Return one line per id and nothing else; the main agent saves it as
verify.md: <id>: confirmed | refuted — <why, path:line> | unverifiable — <what you would
need>.
```

Then apply the verdicts:
- §3–§4 and "While you are here": confirmed → keep; unverifiable → out of the section, into
  "Not verified" as a question; refuted → drop. To keep a refuted finding, `SendMessage` the
  verifier your counter-evidence once and append its answer to `verify.md` as
  `<id> (round 2): …`; that verdict stands. Without that round, the finding goes to "Not
  verified" with both positions.
- §5: every row stays. A refuted `addressed` becomes `partially addressed` or `not addressed`
  with the verifier's evidence; a refuted `not addressed` (or pending, no change) becomes
  `addressed` or `partially addressed` with the head code it found; unverifiable becomes
  `unclear` with the reason.
- Codex: fork ids are final; an `=` pair stays one finding under the fork id. A confirmed
  codex-only finding joins §3–§4 tagged `(codex)` under the next free B, P or D number, after
  the highest fork id of this run; add it to its match line: `CD3 = none → D4`. §6 records
  the agreements in one line, then every surviving disagreement (a codex objection to a
  finding you kept, a `≠` pair, a codex finding the verifier refuted) with both positions,
  the verdict and your take.

## Step 5 — tests and benchmarks (only with `--tests`)

`Agent(subagent_type: "general-purpose", model: "sonnet")`; switch to opus if the bootstrap
fails twice. Results go in §7 exactly as the table; a failing test that matches a bug finding
is cross-referenced from it.

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

## Step 6 — assemble and report

Merge into `$WORK/review.md` per `report-format.md`: "At a glance" from the verified findings
and thread rows, §1–§2, the verified §3–§5, optional §6–§7, "Not verified". Read it once as
the reviewer would, with fifteen minutes: cut what does not help them decide.

Write the head sha to `$WORK/review.done`; the next run builds on this review only if it
finished. Reply with the path to `review.md` followed by its full content, no preamble.

## Step 7 — HTML artifact (only with `--html`)

Follow `references/html.md`: a sonnet subagent converts `review.md` into `$WORK/review.html`;
you publish it with the Artifact tool and give the URL.

## Step 8 — post comments (only when the user names what to post)

Follow `references/post.md`: the user picks the items and the review action; you write the
points, a sonnet drafts `post.json`, you check every sentence and show the dry-run; on their
go `scripts/post_review.py` posts **one** signed review pinned to the reviewed head.

## `gc`

`/review-pr gc` runs `bash $SKILL_DIR/scripts/gc.sh --keep 6 --days 7` and reports its
summary line. Gather runs the same command on every review, so the cache holds at most six
worktrees, none older than a week, none for a merged or closed PR. The markdown per slug is
kept. `gc.sh --all` empties every worktree.

## Feeding directions back into this skill

The one place this skill edits anything, only in the skill's own repo and only on a direction
from the user. When they adjust the output ("always list callers", "shorter §1"), apply it to
`review.md`, then ask: is this general? If so, edit the skill in the same turn
(`checklist.md` for what to look for, `report-format.md` for shape, `gather.md` for what to
collect, this file for process) and say which file changed.
