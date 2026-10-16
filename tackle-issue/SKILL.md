---
name: tackle-issue
description: >-
  Tackle a reported Linear issue end to end. Sonnet agents gather the issue, its comments and linked docs, Linear duplicates and related GitHub PRs; you study the code and explain the problem with before/after scenarios, weigh the suggested fix against alternatives, and challenge the reported severity. After the user approves a fix, an Opus agent implements it in a worktree, codex reviews it, and a draft PR goes up. Use when the user invokes /tackle-issue A-NNN or asks to look into, triage or fix a reported issue.
argument-hint: "<Linear identifier, e.g. A-2400>"
disable-model-invocation: true
---

# tackle-issue

**You are the analyst.** Sonnet agents do the clerical fetching. You spend your context on
the code, so that you can explain the issue to someone who has never opened the module,
judge whether the report is right, and brief the implementer. Nothing is written to GitHub
or Linear until the user approves a fix.

## Ground rules

- **Read-only until the go-ahead.** Steps 1–3 never comment, label, assign, set state,
  push or edit files in the repo. Every gather prompt carries this line:
  > Read-only: do not comment, react, label, assign, change state or edit anything on
  > Linear, GitHub, Notion or Slack. Your only output is the files named in this prompt and
  > your summary.
- **Cite the code.** Every claim about behavior names `path:line` at the commit you read
  (`origin/main` unless the issue says otherwise). A claim you could not check goes under
  "Not verified" as a question, never into the explanation as fact.
- **Do not trust the report.** The reporter may have misread the code, hit it on an old
  version, or proposed a fix that moves the bug elsewhere. Check each claim against the code.

## Paths

`$SKILL_DIR` is the directory holding this file (resolve the symlink once; subagents cannot
guess it). `$WORK` = `${XDG_CACHE_HOME:-~/.cache}/tackle-issue/<id>/`, with `<id>` the
lower-case identifier (e.g. `a-2400`). Create it before Step 1.

```
$WORK/issue.md      # issue body, every comment, attachments, relations, linked docs in full
$WORK/linear.md     # Linear duplicates and related issues
$WORK/prs.md        # related, duplicate or conflicting GitHub PRs
$WORK/explain.md    # your explanation (Step 3), the source for the implementer brief
$WORK/decision.md   # the fix the user approved, plus every decision from the Q&A
```

## Step 1 — gather (two Sonnet agents, in parallel)

Read `my-context` first for the user's GitHub handle, repos and Linear team. Send both Agent
calls in **one message**. Both are `subagent_type: "general-purpose"`, `model: "sonnet"`.
Sonnet agents may call the Linear MCP tools directly (the gate exempts cheap models), and
unlike the `linear` agent they also have `gh`, Notion, Slack and WebFetch.

### Issue agent

```
You are the issue-gather agent for tackle-issue. Issue: <A-NNN>. <read-only line>

1. Fetch the issue (get_issue): title, team, state, priority, labels, assignee, reporter,
   created date, project, cycle, relations (blocks, blocked by, related, duplicate), parent
   and sub-issues, attachments. Fetch every comment (list_comments), threads included.
2. Follow every link in the body and comments, one hop deep:
   - Linear issues and documents: fetch them (title, state, the part that matters).
   - GitHub issues, PRs and code links, in any repo: `gh issue view` / `gh pr view
     --comments` / `gh api` for permalinks. Note the repo and the commit a code link pins.
   - Notion pages: the notion fetch tool. Slack threads: slack_read_thread.
   - Anything else: WebFetch. Note each link you could not open, and why.
   Pull out the version, network, commit or release the reporter was running, and any
   logs, stack traces or reproduction steps.
3. Write <$WORK>/issue.md: a header with the metadata, the description verbatim, every
   comment verbatim with author and date, then one section per linked item with its source
   URL and the content that bears on the issue (verbatim for code, logs and repro steps).
4. Search Linear for duplicates and related issues across ALL teams: open issues plus those
   completed or canceled in the last 90 days, with 4–8 search terms drawn from the issue
   (identifiers, error messages, metric and config names, synonyms). Leave out the issue
   itself and the relations from step 1 (they are already in issue.md). Write
   <$WORK>/linear.md, at most 8 matches, strongest first, one line each:
   `A-NNN · title · state · assignee · DUPLICATE | RELATED | FIXED-BY · why it matches`.
   FIXED-BY means an issue that was closed with a change which may already fix this one.
   Write `none` if nothing qualifies.

Return ONLY: one line per file written, the search terms you used (for the PR agent), the
version or commit the reporter ran, the links you could not open, and the code paths the
issue names.
```

### PR agent

```
You are the PR-scan agent for tackle-issue. Issue: <A-NNN>. Repos: <current repo from
`gh repo view --json nameWithOwner -q .nameWithOwner`, plus any my-context repo where the
fix could land>. <read-only line>

1. Fetch the issue title and description (get_issue) and pick 4–8 search terms:
   identifiers, error messages, metric or config names, synonyms.
2. `gh pr list --repo <r> --state all --search "<terms> updated:>=<60 days ago>" --json
   number,title,author,state,url,updatedAt,mergedAt`, several searches. Also search for
   the identifier itself (`<A-NNN>` in titles, bodies and branch names).
3. Name the code areas the issue points at (Grep the repo for the identifiers it names).
   List open PRs that touch them: `gh pr list --repo <r> --state open --limit 200 --json
   number,title,author,url,files`, filtered to those paths.
4. For each candidate, read the body and the diff of the overlapping files (`gh pr diff`)
   before classifying.

Write <$WORK>/prs.md, at most 8 matches, strongest first, one line each:
`#N · title · author · state · DUPLICATE | FIXES | RELATED | CONFLICT · why`, with the
overlapping files for CONFLICT. DUPLICATE: an open PR making the same fix. FIXES: a merged
PR that already fixes the issue (say whether it is on main only or also on a release
branch). RELATED: same feature or bug, different change. CONFLICT: an open PR editing the
same code in a way that will clash. Write `none` if nothing qualifies.

Return ONLY the lines of prs.md.
```

**Stop early** if either agent finds a DUPLICATE, FIXES or FIXED-BY match: report it, check
the claim against the code yourself, and ask the user whether to go on.

## Step 2 — understand (you)

Read `$WORK/issue.md`, `linear.md`, `prs.md`, and `$SKILL_DIR/references/explain-format.md`.
Then read the code at `origin/main` (`git fetch origin main` first; read with
`git show origin/main:<path>` or open files when the checkout is on main). Read whole
functions around the reported spot, their callers, and the code the suggested fix would
touch. Answer, for yourself:

- **Does the bug exist on main?** Trace the reported input to the wrong output. If the
  reporter ran an older version, also check that version (`git show <tag>:<path>`); a bug
  fixed on main but live on a release still matters, and needs a port.
- **What is the root cause**, as opposed to the symptom the reporter saw?
- **Who can trigger it**, under what preconditions, and what breaks when they do?
- **Does the suggested fix address the root cause?** What else does it change? Does it
  break an invariant, a caller or a test?
- **What fixes did the reporter not consider?** Fixing it at a different layer, removing
  the condition that makes it possible, a smaller change, or a larger one that removes a
  class of bugs. Aim for two or three real alternatives; do not invent weak ones to fill
  the list.

When a question can be settled by running something cheap (a unit test, a script, a
`cast call`), run it. If a claim needs a build or a live network to check, list it under
"Not verified" rather than guessing.

Load `writing-well` (`Skill(skill: "writing-well")`) now; it governs every sentence from
here on.

## Step 3 — explain (you)

Write `$WORK/explain.md` following `references/explain-format.md`, then reply with its full
content. It covers: a verdict up front, the problem with before/after scenarios, the root
cause, the severity check, the suggested fix, the alternatives with your recommendation,
and what you could not verify.

Then wait. The user will ask questions, push back, or pick a fix. Answer from the code and
cite it. Update `explain.md` when an answer changes the analysis, so it stays the record.

**Skipping the wait.** When the invocation already asks for the fix ("/tackle-issue A-NNN
and fix it", "go straight to implementing"), that is the go-ahead: post the explanation and
continue to Step 4 with your recommended fix. Stop and wait anyway when the verdict is not
**confirmed**, when Step 1 found an overlap, or when the choice between fixes needs a
decision only the user can make (a breaking change, a tradeoff with no clear winner).

If the verdict is **not a bug** or **working as intended**, do not offer to implement. Offer
instead: a draft reply to the reporter (the user posts it, or approves you posting it), and,
for a security report on the node, the `update-node-threat-model` skill to record why it is
out of scope.

## Step 4 — the go-ahead

The user approves a fix in their own words ("go", "do option B", "ship it"), or approved it
up front (see Skipping the wait). Before dispatching, settle these, asking with one
`AskUserQuestion` only for what the conversation has not answered and cannot be inferred:

- **Fix**: which option, with any changes from the Q&A.
- **Base branch**: `main` unless the issue was hit on a release that needs it sooner. A
  release fix usually lands on main first and is ported after with `port-to-branch`; say so.
- **Disclosure**: if the issue is an undisclosed security problem, the repo is public; the
  PR title, body, commit messages, code comments and test names must describe the change
  without spelling out the exploit. Ask the user when in doubt.

Write `$WORK/decision.md`: the chosen fix, the scope (what is in, what is explicitly out),
the base branch, the disclosure constraint, the test that should go red then green, and
every decision the user made during the Q&A, in their words where it matters.

**Claim the issue.** Spawn the `linear` agent (`model: "sonnet"`) to re-read the issue's
assignee and state now, since `issue.md` may be stale, and then:

- **Assigned to someone else**: change nothing on the issue, and tell the user who has it.
- **Unassigned**: assign it to the user (Linear user from `my-context`).
- **State is Backlog or Todo** (state type `backlog` or `unstarted`): move it to the team's
  In Progress state. Leave any other state as it is.

Have it return one line: the assignee and state before and after.

## Step 5 — implement (Opus, high effort, in a worktree)

Create the worktree yourself so it starts from a fresh base, using Linear's suggested
branch name when it follows the `spl/` prefix, else `spl/<id>-<slug>`:

```bash
git fetch origin <base>
git worktree add -b <branch> <repo>/.claude/worktrees/<id> origin/<base>
```

`cleanup-worktrees` knows to look in `.claude/worktrees`. Then dispatch:

`Agent(subagent_type: "general-purpose", model: "opus", effort: "high")`

```
You are the implementer for tackle-issue, fixing <A-NNN>. Work only in the worktree
<abs path>, on branch <branch>; never touch the main checkout at <repo>.

Read first: <$WORK>/decision.md (what to do; it wins over anything else), <$WORK>/explain.md
(the analysis), <$WORK>/issue.md (the report), and the CLAUDE.md files of the repo and of
each component you touch. Follow them, including red/green: write or run a test that fails
for the reported reason before you fix, show it failing, then show it passing.

Bootstrap only what the components you touch need, as the component CLAUDE.md says. Keep
to the scope in decision.md: if you find a second bug or the fix needs to grow, stop and
report it rather than widening the change. Commit with Conventional Commits, naming
specific files in `git add`. Do not push and do not open a PR.

If you are stuck, or the code contradicts the analysis, return a message starting with
BLOCKED: and your specific questions, and stop. You will be resumed with answers.

Report back: files changed, the red and green test runs (command and result), the build
and lint results, any deviation from decision.md and why, and follow-ups you noticed.
```

Handle `BLOCKED:` the way `implement-plan` does: answer from the analysis, or ask the user,
then resume the **same** agent with `SendMessage`.

When it reports done, read the diff yourself (`git -C <wt> diff origin/<base>...HEAD`).
Check it against `decision.md` and against the root cause in `explain.md`. Do not take the
agent's word for the test results; check that the red/green runs it quotes test the
reported behavior.

## Step 6 — codex review (Astra, medium)

Load the `codex` skill and follow it, with `-m gpt-6-astra -c model_reasoning_effort=medium`
and `-C <worktree>`. The prompt gives codex the paths of `issue.md`, `explain.md` and
`decision.md`, the diff range `origin/<base>...HEAD`, and asks it to find whether the change
fixes the root cause, what it breaks, missing tests, and scope creep, critically. Do not
show it your own opinion of the diff.

Triage per the codex skill: verify each claim against the code, drop low-priority nits and
list them. Send the fixes you accept to the **same** implementer via `SendMessage` as one
batch, as new commits. Re-read the diff after. One codex round is the default; resume the
codex session for a second only if the fixes were substantial.

## Step 7 — draft PR

Follow the `create-pr` skill from inside the worktree (run `git` and `gh` with the worktree
as the working directory): draft, `ci-draft` label when the repo has it, base from
`decision.md`, `Fixes <A-NNN>` at the end of the body, and the disclosure constraint.

Then, per `linear-issues`, spawn the `linear` agent (`model: "sonnet"`) to post one comment
on the issue: root cause, the fix and the PR URL, the alternatives ruled out and why. Do
not change the issue's assignee, state or priority beyond the claim in Step 4 unless the
user asked.

Report: the PR URL, the worktree path, the codex findings you dropped, the follow-ups the
implementer noted, and whether a port to a release branch is still needed.

## Feeding directions back into this skill

When the user adjusts the output in a way that would improve the next run ("always show
the call chain", "shorter severity section", "skip codex for one-liners"), edit this skill
in its own repo in the same turn — `references/explain-format.md` for the explanation's
shape, this file for the process — and say which file changed. Requests about one issue
stay in that issue's `explain.md`.
