---
name: self-review
description: >-
  Review your own change before posting it: bugs and design findings from reviewers that never saw how it was built, settled by a cold verifier that debates them with the reviewers, then the user decides what to fix and won't-fix decisions are made public. Reviews the current working copy (commits not yet in the base plus uncommitted and untracked files) against its base branch. Use when the user invokes /self-review or asks to review their own work, branch or uncommitted changes before opening or updating a PR. Flags: --base <branch>, --no-codex, --fresh.
argument-hint: "[--base <branch>] [--no-codex] [--fresh] [focus...]"
---

# self-review

**You built this change, so you are the worst judge of it.** One fresh orchestrator gathers
the change, runs reviewers that never saw your reasoning, and has a cold verifier debate their
findings with them. You show the report unchanged and help the user decide what to fix.

```
you ─ orchestrator (opus) ─┬─ gather (sonnet)
                           ├─ BUGS (opus)            ┐
                           ├─ DESIGN (opus)          ├─ reviewers, in parallel
                           ├─ codex (CLI, astra)     ┘
                           └─ verifier (opus) ── challenges each reviewer, once:
                                SendMessage (interactive), or a stand-in it spawns (claude -p);
                                codex by session id
```

The orchestrator's recipe and every prompt below it live in `references/orchestrator.md`. It
reuses review-pr's checklist, finding formats and dossier script; review-pr itself is not run.

## Ground rules

- **Your bias stays out.** Never tell any subagent what the change is for, why you built it
  this way, or what you worry about. The Step 2 prompt is verbatim: fill only the bracketed
  slots, with facts. The reviewers learn the change from the code, the commits and the
  Linear issue.
- **Hands off the working copy while the review runs.** Do not edit, commit, stash or check
  out anything until the orchestrator returns.
- **The report is not yours to edit.** Show it verbatim (Step 3); your own view goes in
  labelled notes beside it.
- **Nothing outward-facing without asking.** PR body edits, issues and comments wait for the
  user's go.

## Paths

`$SKILL_DIR` = this file's directory, symlink resolved (`readlink -f`). `$REVIEW_PR_DIR` =
`$SKILL_DIR/../review-pr`. `$WORK` = `${XDG_CACHE_HOME:-~/.cache}/self-review/<owner>-<repo>/<key>/`,
lower case; `<key>` is the branch with `/` turned into `--` (`spl/foo` → `spl--foo`), or
`detached-<first 8 hex of sha1 of the repo root path>-<merge-base7>`. Gather computes it; the
layout is in `references/gather.md`. You touch only `$WORK/report.md` (the deliverable) and
`$WORK/decisions.md` (Step 4).

## Step 1 — scope (you)

Facts only, from a few git commands:

1. Repo root, branch, `owner/repo` from the origin remote.
2. **Base.** `--base` wins if given (strip a leading `origin/`). Else the base of this
   branch's open PR (`gh pr view --json baseRefName,number`). Else list the candidates that
   exist on the remote (`git ls-remote --heads origin next main master 'v[0-9]*' 'release/*'`)
   and pick the one whose merge-base with HEAD leaves the fewest commits (`git rev-list --count
   <mb>..HEAD`); same merge-base → first in that order. Ask only when different merge-bases
   come within two commits of each other, or no candidate exists. Fetch the chosen base (and,
   when comparing, each candidate) by name before computing merge-bases, one `git fetch -q
   origin <name>` each: a single fetch of several names aborts on the first missing one.
3. **Scope**: `git diff --stat <mb>` (commits plus staged and unstaged edits) and
   `git ls-files --others --exclude-standard` (untracked). Nothing at all → say so and stop.
   Ask when it looks wrong: hundreds of files, or base-branch merge commits in the range.
4. The Linear issue key, if the branch name or a commit subject carries one
   (`[A-Z][A-Z0-9]+-\d+`).

Tell the user in one line and go on unless you asked something: "Reviewing `<branch>` against
`<base>` (merge-base `<mb7>`): N commits, uncommitted edits in M files, U untracked."

## Step 2 — run the orchestrator

`Agent(subagent_type: "general-purpose", model: "opus")`, with this prompt verbatim:

```
You are the orchestrator of the self-review skill. Read <$SKILL_DIR>/references/orchestrator.md
and follow it exactly.
Repo: <absolute repo root> (<owner/repo>). Branch: <branch, or "detached">.
Base: origin/<base_ref>, merge-base <sha>. PR: <number, or none>.
Skill dir: <$SKILL_DIR>. review-pr dir: <$REVIEW_PR_DIR>.
Linear issue: <KEY, or none>. Codex: <yes, or no with --no-codex>. Fresh: <yes with --fresh, else no>.
User's focus: <the user's own words after the flags, verbatim, or none>.
Return the report as orchestrator.md §8 says, and nothing else.
```

Wait for it with the working copy untouched. `BLOCKED: …` means it could not run (nesting
unavailable, git failure): relay it and stop.

## Step 3 — present

Reply with the path to `report.md`, then the report verbatim: not reworded, reordered, merged
or trimmed. Where you have something to add about a finding, put it right after that
finding's text, as its own quote block:

> **Implementer's note** — <at most two lines>

Only a constraint or intent the reviewers could not see, or which fix option you would pick
and why. If you think a finding is wrong, say so with `path:line`, but leave it in the report.
No note on a finding you have nothing to add to, and no notes grouped at the end.

Then ask for a decision per finding: **fix** (which option), **won't fix** (with the reason),
or **follow-up** (a Linear issue). Accept shorthand ("fix B1 B2 option 1, wontfix D2 too
costly, rest follow-up").

## Step 4 — act on the decisions

Append to `$WORK/decisions.md`, one line per finding, readable on its own:
`<date> <id> [path:line] <one-line claim> — fix (option N) | won't fix: <reason> | follow-up <KEY>`.
The file is cumulative; later runs' reviewers read it.

- **Fix**: implement what the user picked. Commit only if the user asks.
- **Won't fix**: make it public, so the next agent does not redo the work or fall into the
  same hole.
  - In the code, when the decision is tied to a line a future reader will question: a short
    comment saying what is deliberately not done and why. Not for style preferences.
  - In the PR body, always: a `## Deliberately not changed` section, one bullet per decision
    with its reason. If the PR exists, show the new body and run `gh pr edit` only on the
    user's go. If not, the `create-pr` skill adds the section from `decisions.md`.
  - In a module's README, only for a decision about the whole module, and only if the user
    agrees.
- **Follow-up**: list the issues you would file (title, one line each); after the user
  confirms, file them through the `linear` agent with the defaults from the user's CLAUDE.md
  and write the keys into `decisions.md`.

## Step 5 — re-run after fixing

Run the skill again. Gather compares the working copy with the last reviewed snapshot:
`unchanged` → the orchestrator returns the last report; small interdiff → `incremental` (each
prior finding marked fixed, still present, moot or decided; new findings only from the
interdiff); else `full`. Decisions in `decisions.md` reach the reviewers as settled.

## Feeding directions back into this skill

When the user adjusts the output or the process and the change would help every future run,
edit this skill in the same turn: `orchestrator.md` for prompts and the report shape,
`gather.md` for what is collected, this file for your own steps. Shared review rules
(`checklist.md`, the finding formats) live in review-pr; change them there only when they
should apply to both skills. Say which file changed.
