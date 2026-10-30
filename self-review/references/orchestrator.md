# orchestrator — run the self-review (opus subagent recipe)

You are the **orchestrator** of `self-review`. You never saw this change being built, and the
agent that built it is not part of the review. Have the change gathered, reviewed by three
independent reviewers and settled by a cold verifier, then hand back one report. You do not
judge findings and never reword the verifier's text.

## Rules

- **Prompts are verbatim.** Fill only the bracketed slots, with facts: paths, shas, agent ids,
  the issue key, the user's focus words. Add no context of your own.
- **`<read-only line>`** in every prompt below stands for:
  > Read-only: do not modify files in the repo or the working copy; do not commit, stash,
  > reset, check out or touch the index; do not post or edit anything on GitHub or Linear; do
  > not install, build or run tests. Your only output is what this prompt asks you to write
  > or return.
- **Files.** Gather writes under `$WORK`. Reviewers and the verifier return text; save each
  reply verbatim to the file named below. Everything you and codex write stays under `$WORK`.
- **Never hand back early.** After any spawn, background command or SendMessage you wait on,
  end your turn with the single word `WAITING`; the completion or reply wakes you. Return
  only once the verifier has returned and §7 has passed.
- **Nesting.** You spawn two levels below the main agent; the verifier may spawn one more. If
  spawning fails (depth limit, Agent unavailable), return `BLOCKED: <the error>` and stop.
  Never review the change yourself instead.

`$SKILL_DIR`, `$REVIEW_PR_DIR`, the repo and the base come from your prompt; `$WORK` from
gather.

## 1. Gather (sonnet)

`Agent(subagent_type: "general-purpose", model: "sonnet")`:

```
You are the gather subagent of self-review. Read <$SKILL_DIR>/references/gather.md and follow
it exactly. Repo: <root> (<owner/repo>). Branch: <branch>. Base: origin/<base_ref>, merge-base
<base sha>. PR: <number or none>. review-pr dir: <$REVIEW_PR_DIR>. Linear issue: <KEY or none>.
Fresh: <yes|no>.
<read-only line> Exception: you write the files gather.md names under the work dir, and you
create the snapshot commit object gather.md describes (no ref, no index change).
Return ONLY the summary block from gather.md §9.
```

Take `work`, `snap`, `base`, `mode`, `prev`, `commits` and the `files` line from its summary.

Mode `unchanged`: reply with the line `No changes since the last review (snapshot <prev7>).
To review again anyway, for instance with a new focus or codex toggled, re-run with --fresh.`,
then `report: <$WORK>/report.md` and that report verbatim. Write nothing and stop.

## 2. The change, and the slots

`<the change>` in the prompts below stands for this block, verbatim:

```
The change under review is snapshot commit <snap> against merge-base <base>, in the repo at
<root>. `git -C <root> diff <base> <snap>` shows it, `git -C <root> show <snap>:<path>` a file
as reviewed, `git -C <root> show <base>:<path>` a file before the change. Where the working
copy differs from the snapshot, the snapshot is what is under review. The review-pr files you
are pointed at were written for pull requests: read "this PR" as "this change" and "head" as
"the snapshot", and cite path:line at the snapshot without permalinks.
```

The other slots, empty unless their condition holds:
- `<decisions>`, when `$WORK/decisions.md` exists: "The author already decided on some
  findings; they are listed in <$WORK>/decisions.md with their location and claim. Match them
  by location and claim, not by id. Do not raise them again unless the code changed in a way
  that breaks the stated reason."
- `<incremental>`, in mode `incremental`: "This change was reviewed before, at snapshot
  <prev7>; that review is <$WORK>/history/<prev7>/report.md, and <$WORK>/interdiff.md shows what
  changed since. For each of its <B and P ids, including those tagged (codex) | D ids>, state
  its status now: fixed (cite the change), still present (re-cite it), moot (the code is
  gone), or decided (listed in decisions.md as won't fix; do not re-argue it). Then hunt for
  new ones in the interdiff and the code it interacts with; do not re-review code the
  interdiff leaves alone. Keep prior ids and number new ones after the highest prior id."
  For DESIGN add: "The previous fix history is <$WORK>/history/<prev7>/fix-history.md."
  For codex, instead: "This change was reviewed before; focus on <$WORK>/interdiff.md and the
  code it interacts with."
- `<focus>`, when the user gave one: "The author asks for extra attention on: <focus>. Look
  there, and elsewhere too."

## 3. Reviewers, in parallel

Start codex first, then BUGS and DESIGN in one message. Save each filled prompt before
spawning (`$WORK/prompt-bugs.md`, `$WORK/prompt-design.md`, `$WORK/codex/prompt.md`); the
verifier may need them. Keep each agent's id from its spawn result.

### Codex

Skip when the prompt says `Codex: no`. Otherwise empty `$WORK/codex/`, write the prompt
there, and run in the background:

```bash
codex exec -m gpt-6-astra -c model_reasoning_effort=high --sandbox read-only \
  --skip-git-repo-check -C "<root>" -o "<$WORK>/codex/response.md" \
  - < "<$WORK>/codex/prompt.md" > "<$WORK>/codex/log.txt" 2>&1
```

When it ends, take the UUID from `grep -m 1 -oE 'session id: [0-9a-f-]{36}' <$WORK>/codex/log.txt`
(none → session id `none`; the verifier then settles codex disputes without asking) and save
`response.md` verbatim to `$WORK/findings-codex.md`.

```
You are an independent reviewer of a change in <owner/repo>; someone else wrote it. Your
working directory is the repo. <the change>
Read <$WORK>/dossier.md (commits, every hunk with line ranges at the snapshot), <$WORK>/linear.md
(the goal, in the requester's words) and, if present, <$WORK>/decoherence.md (flow signals and
the 4-week fix history of the areas touched), then §Ground rules, §Bugs, §Contract claims,
§Design, §Decoherence and §Leave alone of <$REVIEW_PR_DIR>/references/checklist.md. Build your
own understanding from the code first: what each touched module does, who calls it, what
invariants the change must keep.

Then find (1) bugs this change introduces: trace each to a failing input and the wrong
output, drop what you cannot trace or keep it at confidence low with the unverified
assumption named, open a callee's body before trusting any comment, catch or mock about it,
and put pre-existing defects under "While you are here"; (2) design and simplification
opportunities per §Design, TRADEOFF-labelled when semantics change, and special cases or
second ways added instead of fixing the model, naming the existing path and citing earlier
fixes from git log. For each finding add "Fix options": one to three ways to fix it, a line
each with its cost, and which one you recommend.
<decisions> <incremental> <focus>

Be critical: try to break the change before you call it correct. Use the §3 and §4 formats of
<$REVIEW_PR_DIR>/references/report-format.md, with ids CB1… for bugs, CP1… for "While you are
here" and CD1… for design; say so when a section is empty. Return the findings as your final
message and nothing else.
<read-only line>
```

### BUGS

`Agent(subagent_type: "general-purpose", model: "opus")`; save the reply to `$WORK/findings-bugs.md`.

```
You are the BUGS reviewer of self-review. Someone else wrote this change; find what is wrong
with it. <the change>
Read <$WORK>/dossier.md (commits, every hunk with line ranges at the snapshot),
<$WORK>/linear.md (the goal, in the requester's words), and §Ground rules, §Bugs, §Contract
claims and §Leave alone of <$REVIEW_PR_DIR>/references/checklist.md.
Build your own understanding first: what each touched module does, who calls it, what
invariants the change must keep. Read whole functions around each hunk, and their callers.
Then hunt for defects this change introduces, and check every claim about a callee per
§Contract claims by opening the callee's body. Trace each candidate until you can state the
failing input and the wrong output; drop what you cannot trace, or keep it at confidence low
with the unverified assumption named. Pre-existing defects in touched code go under "While you
are here", ids P1….
For each finding add "Fix options": one to three ways to fix it, a line each with its cost or
risk, and which one you recommend.
<decisions> <incremental> <focus>
Write the findings in the §3 format of <$REVIEW_PR_DIR>/references/report-format.md (ids B1…,
P1…).
After you return, the verifier of this review may message you to challenge a finding. Answer
it: hold the finding with evidence (path:line), amend it, or withdraw it, then end your turn.
<read-only line> Return the findings text and nothing else.
```

### DESIGN

`Agent(subagent_type: "general-purpose", model: "opus")`; save the reply to `$WORK/findings-design.md`.

```
You are the DESIGN reviewer of self-review. Someone else wrote this change; judge its shape.
<the change>
Read <$WORK>/dossier.md, <$WORK>/linear.md (the goal, in the requester's words),
<$WORK>/decoherence.md and <$WORK>/fix-history.md (older fixes and checks around the touched
functions), and §Ground rules, §Design, §Decoherence and §Leave alone of
<$REVIEW_PR_DIR>/references/checklist.md.
Build your own understanding first: what each touched module does, who calls it, what the
change leans on. Then look for design and simplification opportunities: responsibilities,
size, duplication, naming, abstractions the change did not need, and semantics-changing
simplifications labelled TRADEOFF with what is lost and who hits it. Judge decoherence: does
the change add a special case, a branch or a second way of doing something instead of fixing
the model? When you flag one, name the existing path the new one should replace or extend, and
cite the evidence (earlier fixes, the copied check).
For each finding add "Fix options": one to three shapes, a sketch when it helps, each with its
cost, which one you recommend, and whether it belongs in this change or a follow-up.
<decisions> <incremental> <focus>
Write the findings in the §4 format of <$REVIEW_PR_DIR>/references/report-format.md (ids
D1…).
After you return, the verifier of this review may message you to challenge a finding. Answer
it: hold the finding with evidence (path:line), amend it, or withdraw it, then end your turn.
<read-only line> Return the findings text and nothing else.
```

## 4. Challenge mode

Run `echo "$CLAUDE_CODE_ENTRYPOINT"`. `cli` (interactive session): the verifier resumes a
reviewer with SendMessage and gets the reply (mode `resume`). Anything else, such as `sdk-cli`
under `claude -p`, routes a resumed agent's reply to the session's main agent, so the verifier
spawns a stand-in as its own child (mode `respawn`). Codex is resumed by session id in both.

## 5. Verifier (opus)

Once all reviewers are in, `Agent(subagent_type: "general-purpose", model: "opus")`; save its
reply verbatim to `$WORK/verify.md`.

```
You are the verifier of self-review: a cold judge of the findings three independent reviewers
made about a change. <the change>
Read <$WORK>/findings-bugs.md, findings-design.md and, if present, findings-codex.md. Judge the
code: do not read commit messages, linear.md or the top of dossier.md before you have judged.
Use only the `### Files` section of dossier.md, to find line ranges, and fix-history.md and git
log to check claims about earlier fixes.
<in incremental mode: "This change was reviewed before, at snapshot <prev7>
(<$WORK>/history/<prev7>/report.md); <$WORK>/interdiff.md shows what changed since. Check every
fixed, still-present, moot and decided claim as well as the new findings.">

1. Match the codex findings (CB, CP, CD) to the others by claim and location: `CB2 = B3`
   (same finding), `CB1 ≠ B2` (they contradict), `CD3 = none` (codex only).
2. Judge each finding. Bug: is the path reachable, is the input possible, does a guard
   elsewhere prevent it, did this change introduce it or was it there at base. Stale claim:
   open the callee and confirm the claimed outcome cannot happen on that path. Design item: is
   the simpler shape equivalent; for a TRADEOFF, is the stated loss the whole loss. Fix
   options: would each actually fix it, and is the recommended one the right call.
3. Challenge before you refute. When you would refute a finding or call it overstated, ask
   the reviewer that raised it first, once, with the id and your evidence (path:line). For a
   ≠ pair, ask both. Batch all challenges for one reviewer into one message.
   Challenge mode: <resume | respawn>.
   - resume: SendMessage to <BUGS agent id> for B and P ids, to <DESIGN agent id> for D ids.
     If the send fails, use respawn for that reviewer.
   - respawn: spawn one general-purpose opus agent per reviewer you challenge, with: "You are
     standing in for the <BUGS|DESIGN> reviewer of self-review. Its instructions were exactly
     the prompt in <$WORK>/prompt-<bugs|design>.md, and its findings are in
     <$WORK>/findings-<bugs|design>.md. The verifier challenges these findings: <your
     challenges>. Check the code and answer each: hold it with evidence (path:line), amend it,
     or withdraw it. <read-only line>"
   - codex ids, either mode (skip when the codex session id is none): write the challenge to
     <$WORK>/codex/followup-1.md and run, from <root>,
     `codex exec resume <codex session id> -m gpt-6-astra -c model_reasoning_effort=high -o <$WORK>/codex/response-1.md - < <$WORK>/codex/followup-1.md >> <$WORK>/codex/log.txt 2>&1`
     (if `pwd` is not <root>, prefix `cd <root> && `), then read response-1.md.
   After any SendMessage or spawn, end your turn with the single word WAITING; the reply wakes
   you. Never return while a challenge is unanswered. One round per reviewer; then decide.
4. Return exactly these sections and nothing else:
   ## Verdicts
   One line per id: `<id>: confirmed | refuted — <why, path:line> | unverifiable — <what
   would settle it>`, and for prior ids in incremental mode also `fixed — <change>`, `moot`
   or `decided`. Codex lines carry their match, and a codex-only finding you confirm takes the
   next free B, P or D id: `CB2 = B3: confirmed`, `CD3 = none → D4: confirmed`.
   ## Bugs
   Every confirmed or still-present B and P finding, codex-only ones under their new id tagged
   `(codex)`, in the §3 format of <$REVIEW_PR_DIR>/references/report-format.md with its Fix
   options, ordered by severity. Where the debate changed a finding, give the amended text
   and say in one line what changed. "No bugs found." if none, and what was checked most
   carefully. In incremental mode end with "Fixed since `<prev7>`: …", "Moot: …" and
   "Decided (won't fix): …" lines, for those that have entries.
   ## Design
   The same for D, in the §4 format.
   ## Disagreements
   Each point where a reviewer held its position against your verdict, or two reviewers
   contradict: both positions in a line each, and your verdict. "None." if none.
   ## Not verified
   Unverifiable findings, and reviewer questions about intent, as questions for the author.
<read-only line> Exceptions: in respawn mode you may spawn the stand-ins, and you may write
the codex follow-up files and run codex exec resume as above.
```

## 6. Report

Write `$WORK/report.md`:

````markdown
# Self-review: <branch> → <base_ref>

snapshot `<snap7>` · merge-base `<base7>` · <commits> commits, uncommitted edits <yes|no>, <U>
untracked · <F> files, +A −D · Linear: <KEY or none> · codex: <yes|no>
Reviewed <date>. Mode: <full | full (<reason>) | incremental from `<prev7>`>.

## At a glance

<At most six lines, taken from verify.md, adding no claim of your own. Incremental first:
"Since `<prev7>`: B1 fixed, B2 still open, D1 moot, D2 decided; new: B4." Then: "Bugs: N
(blockers B1, B3)", "Design: N (tradeoffs to decide: D2)", "Disagreements: N", "Questions for
you: N".>

## Bugs
<verify.md ## Bugs, verbatim>

## Design
<verify.md ## Design, verbatim>

## Disagreements
<With codex, open with one line: "Codex agreed on <ids from `=` matches>." Then verify.md
## Disagreements, verbatim. Drop the section when both are empty.>

## Questions for you
<verify.md ## Not verified, verbatim. Drop the section when empty.>
````

## 7. Sanity check

Every id in the report has a line in `## Verdicts` (a codex-only one through its `→` id), and
every confirmed or still-present id is in the report. If not: in resume mode ask the verifier
once by SendMessage, save its corrected reply over `verify.md` and rebuild §6; in respawn
mode, put one line naming the gap at the top of `report.md`. Do not fix it yourself.

## 8. Finish and return

Write the snapshot sha to `$WORK/report.done`. Reply with `report: <$WORK>/report.md`, then the
report verbatim. Nothing else.
