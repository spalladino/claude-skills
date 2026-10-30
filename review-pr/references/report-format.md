# report-format — the shape of `review.md`

`review.md` is read by a human with little context and about fifteen minutes: it opens with
what they must decide, then explains, then documents. Prose rules (the `writing-well` skill
when installed): plain words, active verbs, one thought per sentence, no hedges; code in
fenced blocks, not prose. Every `path:line` is a permalink: head citations use
`<permalink_base>`, citations of the code before the PR say `(base)` and use
`<base_permalink_base>` (both in `meta.json` and the dossier header).

````markdown
# Review: <owner/repo>#<n> — <title>

<author> · <branch> → <base> · head `<head7>` · <N> files, +A −D · <state>, <review decision> ·
CI <one line> · behind base by <N> commits · Linear: <KEY> (<state>) or none
Reviewed <date>.

## At a glance

<When gather's `prior:` line is not `none`, open with: "You reviewed this before: <STATE> on
<date> at `<sha7>`, <K> commits since. Last review-pr run: <date> at `<old7>`
(`history/<old7>/review.md`)." Keep only the parts that exist. On a re-run add the delta:
incremental "Since `<old7>`: B1 fixed, B2 still open, D1 moot; new: B4.", same-head "Same
head as the last run: §1–§4 carried over, §5 refreshed."

Then five to eight lines: the change in one sentence, and bullets only where they apply:
"Blockers: B1, B3" with a half-line each · "Your open asks: T1 addressed, T3 not addressed" ·
"Tradeoffs to decide: D2" · "CI red / behind base / draft". This is what the reader acts on.>

## 1. What this PR does, and why

<Under 300 words, for someone who has never opened the module. The problem before the PR,
the goal, the context from the PR body, the linked issue and the discussion. Define each
term the first time it appears.>

**Before / after.** <One concrete scenario: the same explicit input or state on both sides
and the observable result on each, as a two-column table or two short fenced blocks, with
real names from the code and a citation for each side (base or head path:line). If the PR
preserves behaviour, say so in one line and show the structural change instead.>

**What to keep in mind while reviewing.** <Two or three bullets: the invariants the change
must preserve, the risky part, what the author says they did not do.>

## 2. How it does it

<The design, not the diff, in three to six sentences as the author would explain it at a
whiteboard: the new piece or concept, which existing piece takes on the work and why there,
how data flows, what deliberately stays as it was. No file names here.>

| Part | Job | Lives in |
|---|---|---|
| <a responsibility, named as a concept> | <one clause: what it does for the whole> | `path` |

<Three to seven rows, one per responsibility, never one per file; a row that reads like a
commit message gets rewritten or cut. Then one line for everything mechanical: "Mechanical:
11 call sites updated, generated CLI reference, one test moved." A numbered flow of at most
five steps only when the order is not obvious from the paragraph.>

**Breaking or externally visible changes.** <Bullets: public API signatures, wire or storage
formats, config defaults, CLI flags, error types. "None found" if none.>

**Tests.** <What the PR tests, what it does not. One line per gap.>

## 3. Bugs

<Ordered by severity. "No bugs found." if none, followed by what you checked most carefully.>

### B1. <one-line claim> — `blocker|major|minor`, confidence `high|medium|low`
[path:line](permalink) at head · introduced by this PR
<The failing input or state, what the code does, what it should do. Quote the two lines
that matter. If the verifier changed your mind, say what it checked.>

### B2. Stale claim: <what the comment, catch or mock assumes> — `major|minor`, confidence …
[claim path:line](permalink) · callee: [path:line](permalink) · introduced by this PR
<A §Contract claims item. Quote the claim and the callee line that contradicts it; say what
a reader who trusts the claim gets wrong and, when the PR relies on it, the input that takes
the wrong branch.>

**While you are here** (pre-existing, not introduced by this PR): <bullets, each opening with
its id (`P1.`) and a permalink, or "nothing".>

## 4. Design and simplification

### D1. <one-line proposal>
[path:line](permalink)
<What the reader holds in their head now and after. A sketch of the simpler shape in a
fenced block when it helps. Two to six lines.>

### D2. TRADEOFF: <proposal that changes semantics>
[path:line](permalink)
<Same, plus one line each: what is lost, who hits it.>

### D3. Second way: <new path> beside <existing path>
[path:line](permalink) · existing: [path:line](permalink)
<A §Decoherence item, still advisory. Name the existing path the new one duplicates, wraps
or bypasses, and what the PR should do: extend it, replace it, or say when the old one goes.
One line of evidence: earlier fixes to the same function by PR, or where the same check was
added before. A special case instead of a model fix uses `### Dn. Special case: <what>` with
the same shape, naming the model change that would cover it.>

## 5. Discussion status

<One row per unresolved thread and per top-level ask. Rows where the user took part first,
starred. `Remaining` carries what is left in ten words; "—" when addressed.>

| # | Who · where | Ask | Status | Evidence | Remaining |
|---|---|---|---|---|---|
| T1 | ★ spalladino · [path:line](permalink) | <ten words> | addressed | `abc1234` lines 40–52 | — |
| T2 | alice · [path:line](permalink) | … | answered, no change | author: "…" | accept or push back |
| R1 | ★ spalladino · review 2026-09-20 | <ten words> | acknowledged, pending | author: "will do in follow-up" | decide if ok |

<Below the table, a short paragraph only for rows that need a decision from the reader.>

Resolved: <N> threads. <One line only for one that looks wrongly resolved.>

## 6. Second opinion (codex) — only with --codex

<Where codex agreed, in one line. Then each disagreement that survived the challenge round
and the verifier (a codex objection to a kept finding, a `≠` pair, a codex finding the
verifier refuted): both positions, the verdict, your take. Confirmed codex-only findings are
merged above under the next free id, tagged `(codex)`.>

## 7. Tests and benchmarks — only with --tests

<Command run, pass/fail counts, failures with the failing assertion, benchmark deltas, as a
table. Never in prose.>

## Not verified

<Bullets: claims you could not check and why, and findings the verifier could not settle,
turned into questions. The most read section after "At a glance".>
````

Rules:

- Every finding in §3 and §4 has an id (`B1`, `P1`, `D2`) so the user can refer to it, the
  same id `verify.md` judges. Thread ids (`T1`) match this run's `threads.md` (a row carried
  from an earlier run takes the id of its thread url there); top-level asks are `R1…`.
- Incremental re-run: §1 and §2 start from the last review's text and change only what the
  interdiff changes. A carried finding keeps its id and adds "· open since `<old7>`" to its
  location line; new ones number after the highest prior id. §3 and §4 each close with
  "Fixed since `<old7>`: B1 (`abc1234`), …" and "Moot: …" when there are any.
- Never soften a finding to avoid conflict with the author; never harden one to seem
  thorough. Confidence carries the uncertainty.
- §6 and §7 exist only when the flag was given. No empty headings.
