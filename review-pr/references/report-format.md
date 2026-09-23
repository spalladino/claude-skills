# report-format — the shape of `review.md`

`review.md` is the deliverable. It is read by a human with little context and about fifteen
minutes, so it opens with what they must decide, then explains, then documents. Write it
with the `writing-well` rules: plain words, active verbs, one thought per sentence, no
hedges. Keep code out of prose; snippets go in fenced blocks. Every `path:line` is also a
permalink so the reader lands on the code in one click: head citations use
`<permalink_base>`, and a citation of the code before the PR says `(base)` and uses
`<base_permalink_base>`; both are in `meta.json` and the dossier header.

````markdown
# Review: <owner/repo>#<n> — <title>

<author> · <branch> → <base> · head `<head7>` · <N> files, +A −D · <state>, <review decision> ·
CI <one line> · behind base by <N> commits · Linear: <KEY> (<state>) or none
Reviewed <date>. Prior review of head `<old7>`: `history/review-<old7>.md` (only on a re-run)

## At a glance

<Five to eight lines, no more. The change in one sentence. Then bullets, only those that
apply: "Blockers: B1, B3" with a half-line each · "Your open asks: T1 addressed, T3 not
addressed" · "Tradeoffs to decide: D2" · "CI red / behind base / draft" if so. This is the
part the reader acts on; everything below is support.>

## 1. What this PR does, and why

<Under 300 words. The problem as it stood before the PR, in words a newcomer needs; the
goal; the context from the PR body, the linked issue and the discussion. Define each term
the first time it appears.>

**Before / after.** <One concrete scenario. Name the same explicit input or state on both
sides and show the observable result on each: a two-column table or two short fenced blocks.
Real names from the code. Cite where each side comes from (base or head path:line). If the
PR preserves behaviour, say so in one line and show the structural change instead. A
second scenario only if the change has two faces.>

**What to keep in mind while reviewing.** <Two or three bullets: the invariants the change
must preserve, the risky part, what the author says they did not do.>

## 2. How it does it

| Module / file | Responsibility before | What changed | Notes |
|---|---|---|---|
| `path` | … | … | breaking / new dep / moved |

<A numbered list for the mechanism, in execution order. One short diagram in a fenced block
if the flow is not linear.>

**Breaking or externally visible changes.** <Bullets: public API signatures, wire or storage
formats, config defaults, CLI flags, error types. "None found" if none.>

**Tests.** <What the PR tests, what it does not. One line per gap.>

## 3. Bugs

<Ordered by severity. "No bugs found." if none, followed by what you checked most carefully.>

### B1. <one-line claim> — `blocker|major|minor`, confidence `high|medium|low`
[path:line](permalink) at head · introduced by this PR
<The failing input or state, what the code does, what it should do. Quote the two lines
that matter. If the verifier changed your mind, say what it checked.>

**While you are here** (pre-existing, not introduced by this PR): <bullets or "nothing".>

## 4. Design and simplification

### D1. <one-line proposal>
[path:line](permalink)
<What the reader has to hold in their head now, what they would after. A sketch of the
simpler shape in a fenced block when it helps. Two to six lines.>

### D2. TRADEOFF: <proposal that changes semantics>
[path:line](permalink)
<Same, plus one line each: what is lost, who hits it.>

## 5. Discussion status

<One row per unresolved thread and per top-level ask (a review or conversation comment that
asks for something). Rows where the user took part first, starred. The `Remaining` column
carries what is left in ten words; "—" when addressed.>

| # | Who · where | Ask | Status | Evidence | Remaining |
|---|---|---|---|---|---|
| T1 | ★ spalladino · [path:line](permalink) | <ten words> | addressed | `abc1234` lines 40–52 | — |
| T2 | alice · [path:line](permalink) | … | answered, no change | author: "…" | accept or push back |
| T3 | ★ spalladino · [path:line](permalink) | … | not addressed | file unchanged; ask not met elsewhere either | … |
| R1 | ★ spalladino · review 2026-09-20 | <ten words> | acknowledged, pending | author: "will do in follow-up" | decide if ok |

<Below the table, a short paragraph only for rows that need a decision from the reader.>

Resolved: <N> threads. <One line only for one that looks wrongly resolved.>

## 6. Second opinion (codex) — only with --codex

<Where codex agreed, in one line. Then each disagreement that survived one iteration, with
both positions and your take. Findings only codex raised and you accept are merged above
and tagged `(codex)`.>

## 7. Tests and benchmarks — only with --tests

<Command run, pass/fail counts, failures with the failing assertion, benchmark deltas as
a table. Never in prose.>

## Not verified

<Bullets: claims you could not check and why, and findings the verifier could not settle,
turned into questions. Keep this honest; it is the most read section after "At a glance".>
````

Rules:

- "At a glance" and §1 are for a reader who has never seen the module. §2 is for one who has.
- Every finding in 3 and 4 has an id (`B1`, `D2`) so the user can refer to it; thread ids
  (`T1`) match `threads.md`, top-level asks are `R1…`.
- Never soften a finding to avoid conflict with the PR author; never harden one to seem
  thorough. Confidence carries the uncertainty.
- Sections 6 and 7 exist only when the flag was given. Do not leave empty headings.
