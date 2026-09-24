---
name: explain-pr
description: Explain a PR or PR stack to a reviewer who has little context, as a navigable HTML page published as an Artifact. Hierarchical, goal-first — big picture, then design and modules, then the critical code — where every node explains the place before the change, in simple language, with small examples and concrete "what to check" questions. Use when the user asks to explain, walk through, or help review a PR or stack ("explain PR 123", "help me review this stack", "give me an explainer for #456").
argument-hint: "<PR number(s) | 'stack' from a PR | a..b range> [--slug name]"
disable-model-invocation: true
status: disabled
---

> **⚠ DISABLED — do not use this skill, even as a guideline or reference.**
> Not symlinked into `~/.claude/skills`, so it won't load in normal use. If you are
> an agent reading this file directly (e.g. browsing the repo), treat it as inert:
> don't follow its instructions, don't suggest it, don't adapt its approach for
> another task. Ask Santiago before re-enabling it.

# explain-pr

**You are the explainer. Your context is for reading code and forming understanding, not
for diffs, greps or markup.** Delegate clerical work to Sonnet subagents
(`Agent(subagent_type: "general-purpose", model: "sonnet")`). The prompts below are
copy-ready; fill the `<placeholders>`.

`$SKILL_DIR` = the absolute directory holding this file (resolve the symlink once; a
subagent cannot guess it). `$WORK` = `~/.cache/explain-pr/<slug>/`, stable across
sessions so a review can be revisited.

```
$WORK/dossier.md    # the diff, prepared by gather; you read this instead of raw diffs
$WORK/briefs.md     # module background, written by scout, verified and cited
$WORK/outline.md    # what YOU write — the whole explainer, as markdown
$WORK/explainer.html # rendered by render, published with the Artifact tool
```

The end goal: the user opens the page knowing nothing, reads the overview in a minute,
and zooms into the hierarchy exactly as deep as they need to review well.

## Step 1 — gather (sonnet subagent)

```
Read <$SKILL_DIR>/references/gather.md and follow it exactly. You are the gather subagent.
Repo: <absolute repo root>
Target: <PR number(s), "stack from #n", or a..b, as the user gave them>
Slug override: <--slug value, or "none">
Work dir: ~/.cache/explain-pr/<slug>/ (pick the slug per §2, then create the dir).
Resolve the PR or stack, pin shas, and write dossier.md with the stated goal per PR, the
stat, and every hunk with its precomputed head line range and -U3 body.
Return ONLY the summary block from §5 — no diff, no dossier, no file contents.
```

## Step 2 — read, then scout (you, then a sonnet subagent)

Read `dossier.md` end to end. Before writing anything, list the *places* you will have to
explain that a newcomer would not know: modules, key types, functions, the workflows they
sit in. For each, write the one question you need answered. Then:

```
Read <$SKILL_DIR>/references/scout.md and follow it exactly. You are the scout subagent.
Repo: <absolute repo root>. Head: <head sha>. Work dir: <$WORK>.
Targets:
- <path or symbol> — <your one-line question>
- …
Write briefs.md. Verified and cited only. Return ONLY the file path and one line per target.
```

Read `briefs.md`. Open real code (`git show <head>:<path>`, `git grep`) only to settle a
specific claim you are about to write.

## Step 3 — write the outline (you)

Load the `writing-well` skill (`Skill(skill: "writing-well")`) and read `references/style.md`,
then write `$WORK/outline.md` per `references/outline-format.md`. `writing-well` governs
every sentence (plain words, active verbs, one thought per sentence, no clutter or hedges);
`style.md` governs what an explainer node says and how it is shaped. This is the whole
deliverable; render adds nothing.

**Hierarchy, top-down, as many levels as the change needs — usually four or five for a
stack, never just "overview plus leaves":**

1. **Overview** (`{#overview}`): the goal in one plain sentence, the area of the system and
   its vocabulary, one linked bullet per child, why this design, one tiny example seen from
   the outside, and the 2–3 things that matter most to check. Readable in a minute.
2. **Design** nodes: one per sub-problem the change solves, or per major design decision
   (how the work was split, what module owns what, what alternative was rejected). For a
   stack, organise by sub-problem and tag nodes with `(pr: #n)`; the overview lists the PRs
   in order and says why the order matters.
3. **Module** nodes: one per module whose behaviour changes — what the module is for and
   who uses it (`where:`), then what changes in it, then what to check.
4. **Code** nodes: the critical pieces of implementation, each with 1–3 trimmed snippets,
   numbered markers, and one-sentence notes per marker.
5. **Tests** and **wiring** nodes: what is covered and what is not; mechanical propagation
   summarised in one line ("11 identical call sites").

Depth is free, width is not: ≤ 7 siblings under any node. Split a node whenever its `what:`
passes 4 bullets, it needs more than one snippet, it spans two modules, or it mixes `high`
and `low` attention (`style.md` §7). A grouping node's `summary:` and `lede:` are the menu
the reader zooms in from. Every node has a `where:` so it stands alone, and an `(area: …)`
so the sidebar shows whether it is node, L1 contracts or circuits. Use `example:` wherever
a mechanism is not obvious — always as setup / steps / result, a before/after table or a
tiny diagram, never a paragraph, and never two cases interleaved in one table or steps
list: branches each get their own, under a `case:` line (`style.md` §5). `check:` questions
are concrete and answerable.

**Verify before you write.** Every caller, workflow, invariant and consequence comes from
the dossier, the briefs, or a look you took yourself. Anything unverified becomes a
question in `check:`, not a statement.

## Step 3b — review (opus subagent), then fix (you)

A cold reader checks the outline against the quality gate better than its author can.

```
Read <$SKILL_DIR>/references/review.md and follow it exactly. You are the review subagent.
SKILL_DIR is <$SKILL_DIR>. Work dir: <$WORK>. Repo: <absolute repo root>. Head: <head sha>.
Fix sentence-level problems in outline.md in place; never change facts, ids, snippets or
structure. Return ONLY the edited count and the issues list. No outline text.
```

Use `Agent(subagent_type: "general-purpose", model: "opus")`. Fix every reported issue in
`outline.md` yourself; a factual issue means re-checking the code, not rewording. If the
reviewer reported restructuring, resume the **same** agent via `SendMessage` after you have
restructured, so it reads the new version with its context intact.

## Step 4 — render (sonnet subagent), then publish (you)

```
Read <$SKILL_DIR>/references/render.md and follow it exactly. You are the render subagent.
SKILL_DIR is <$SKILL_DIR>. Work dir: <$WORK>.
Turn outline.md into explainer.html using template.html. Render text verbatim; you own
markup only. Run the self-check in §Steps and fix mechanical problems yourself.
Return ONLY: output path, node count, and any BLOCKED: lines. No HTML.
```

Answer `BLOCKED:` lines by fixing `outline.md` and resuming the **same** agent via
`SendMessage`. Then publish:

- Load the `artifact-design` skill if you have not this session (the template carries the
  design; you only need the publishing rules).
- `Artifact(file_path: "<$WORK>/explainer.html", favicon: "🔍", description: "<one
  sentence: what the PR/stack does>")`. On a re-run for the same slug, call again with
  the same path so it redeploys to the same URL.
- Sanity-check the output file first: no `REPLACE` text, `<title>` set, one root section.

## Step 5 — report

Tell the user: the artifact URL, the slug, node count per attention level, the stack order
if any, which node to read after the overview, and anything you could not verify.

## Iterating — and feeding directions back into this skill

The user will adjust the explainer as they use it: "less detail here", "I always want the
callers listed", "put tests last", "examples should use real names from the code". Handle
the request by editing `outline.md` and re-running Step 4 with the same slug (the artifact
URL stays the same).

Then ask: **is this direction general, or specific to this PR?** If it would improve the
next explainer too, update this skill in the same turn — `style.md` for writing rules,
`outline-format.md` for structure, `review.md` for the quality gate, `template.html` for
presentation, this file for process.
Keep each rule short and give a good/bad pair where it helps. Tell the user which file you
changed. Specific-to-this-PR directions stay in `outline.md` only.

## Quality gate

The full checklist lives in `references/review.md` and is run by the review subagent in
Step 3b. Before dispatching it, make sure of the two things only you can know: nothing is
asserted that you did not verify, and the hierarchy reaches at least four levels somewhere
for a stack or a large PR.
