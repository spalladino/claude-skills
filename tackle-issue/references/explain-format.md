# explain-format — the shape of `explain.md`

`explain.md` is read by someone who knows the codebase in general but has never opened this
module, and who must decide what to do about the issue. It opens with the verdict, then
explains, then argues. Write it with the `writing-well` rules: plain words, active verbs,
one thought per sentence, no hedges. Keep code out of prose; snippets go in fenced blocks.
Every `path:line` names the commit it was read at (`origin/main` by default) and is a
GitHub permalink (`https://github.com/<owner>/<repo>/blob/<sha>/<path>#L<n>`), so the reader
lands on the code in one click.

````markdown
# <A-NNN> — <issue title>

<reporter> · <team> · reported <date> · priority <P> · <state> · read at `origin/main`
`<sha7>`<, and at `<tag>` where the reporter ran it>

## At a glance

<Five to eight lines. The verdict first, one of: **confirmed** · **confirmed, already
fixed on main** (by #N; live on <release>) · **partly right** (the symptom is real, the
diagnosis is not) · **not a bug** · **cannot tell** (what would settle it). Then the root
cause in one sentence, the severity you would assign against the reporter's, the fix you
recommend in one line, and any overlap from Step 1 (duplicate issue, conflicting PR).
This is the part the reader acts on.>

## 1. The problem

<The reader has not read the issue and will not open the code. Everything they need is
here, in plain words, with no identifiers they must look up. Three parts, in this order:>

### Background

<Bullets: each fact about the system the story below depends on, one term per bullet,
defined in a sentence. Include when and how often the component runs (what triggers it,
its polling or batch cadence) and the stages it goes through, since bugs usually live
between stages. Name a function only alongside a plain description of what it does.>

### The trigger

<What the reporter (or attacker) does, as a numbered timeline of concrete events. Give
every actor and artifact a short name the first time it appears (e.g. "CP2-bad") and use
that name throughout. Never use a term like "re-post" or "the batch" before defining it.>

### What goes wrong

<A numbered walk through what the system does with that input, step by step, in plain
words: what it checks, what answer it gets, why that answer is wrong. End with the
visible outcome and why nothing recovers. Then who is NOT affected and why, if that
bounds the bug. No path:line here; code references go in §2.>

**Before / after.** <One concrete scenario with the same explicit input or state on both
sides: what happens today, and what should happen. A two-column table or two short fenced
blocks, with real names and values from the code and the report (slot numbers, addresses,
config values, log lines). Cite where today's behavior comes from (path:line). A second
scenario only if the bug has two faces, e.g. a trigger and a consequence that show up in
different places.>

## 2. Root cause

<Two or three plain sentences: the flaw in design terms (which stage assumes what, and
why that assumption fails), understandable from §1 alone. Whether the reporter's diagnosis
matches yours, and where it goes wrong if not. Then a "Where this lives in the code, for
reference" list: one bullet per §1 step that maps it to path:line, each bullet saying in
words what that code does. Say when the bug was introduced if git blame shows it cleanly
(commit and PR).>

## 3. Severity

<The reporter's severity, and yours, with the case for yours. Judge each of these in a
line, from the code:>

- **Who can trigger it**: anyone remote (a p2p peer, a tx sender, an L1 caller) · a
  staked actor (a proposer or validator, bounded by stake and slashing) · the node's own
  operator, by misconfiguration · only in tests or dev setups.
- **Preconditions**: what must already be true, and how often it is true on a live network.
- **Impact**: safety (wrong state, invalid block or proof accepted, funds at risk) ·
  liveness (chain halts, missed slots, honest validators slashed) · one node degraded or
  down · operator confusion (misleading logs, metrics or alerts) · developer experience.
- **Detection and recovery**: does anyone notice, and does it heal by itself, need a
  restart, or need a manual fix or an upgrade?

<Then one line: "Reported as <P>; I would put it at <P'> because …". Disagree when the
code supports it, in either direction. Never soften to match the reporter or harden to
seem thorough.>

## 4. The suggested fix

<What the reporter or a commenter proposed, in two lines. Then: does it fix the root
cause or only the symptom; what else it changes (callers, invariants, wire or storage
formats, config); what it misses. A short sketch of the change in a fenced block.>

## 5. Other fixes

### F1. <one-line approach>

<Where it lives (path:line), what changes, a sketch when it helps. One line each for: what
it fixes that the suggested fix does not, what it costs (size, risk, breaking change,
migration), and who notices.>

### F2. …

<Two or three real options; the suggested fix is F0 when comparing. Close with a
recommendation in two lines: which option, and why over the others. If the right fix is
bigger than the issue, say so and propose the small fix now plus a follow-up issue.>

**Tests.** <The test that should fail today and pass after the fix: where it would live
and what it asserts. Say whether an existing test should already have caught this, and
why it did not.>

## Not verified

<Bullets: claims you could not check and why (needs a build, a live network, logs you do
not have, a link that would not open), each as a question the user can answer or a check
that would settle it.>
````

Rules:

- "At a glance" and §1 are for a reader who has never seen the module, has not read the
  issue, and will not open the code. Define terms; do not lean on the reporter's shorthand
  or on function names. Test: could the reader explain the bug to a colleague from §1
  alone? If a step only makes sense after reading the code ("a checkpoint that passes is
  only pushed to a local array"), rewrite it as what the system does and why it matters.
- Every fix has an id (`F1`) so the user can refer to it. The suggested fix is `F0`.
- Before/after scenarios use the same input on both sides. A scenario that changes the
  input between the columns does not show the bug.
- Keep it scaled to the issue. A one-line config bug gets a short §1, a three-step §2 and
  one alternative at most; do not pad it into the full template.
