---
name: start-work
description: >-
  Before starting a piece of work, check Linear for duplicate or closely related issues and GitHub for duplicate, related, or conflicting PRs (open or recently closed), using two Sonnet agents in parallel. If nothing overlaps and no Linear issue tracks the work yet, file one. Use when the user invokes /start-work or asks to check for duplicates or overlapping work before starting a task.
argument-hint: "[description of the work, or a Linear identifier]"
---

# Start work

Make sure the work is not already done, in flight, or about to collide with someone else's change, and that a Linear issue tracks it. Two read-only scans run in parallel on Sonnet; an issue is filed only when both come back clean.

All Linear access goes through the `linear` agent (`subagent_type: "linear"`); a hook blocks direct Linear MCP calls from the main session. Read `my-context` for the user's GitHub handle, repos, Linear team and Linear user.

## Step 1: Write the brief

Build a short brief of the work from `$ARGUMENTS` and the conversation. If neither describes it well enough to search for, ask the user one question rather than guessing.

- **Goal**: one or two sentences on what changes and why.
- **Areas**: subsystems, packages, and the files or directories likely to change. Spend a few quick Grep/Glob calls to name real paths. Do not plan the implementation.
- **Search terms**: 4–8 keywords and phrases, including synonyms and the identifiers (function, metric, config, or test names) a related issue or PR would mention.
- **Existing issue**: a Linear identifier (`A-NNN`) if one already tracks the work. Look in the user's message and in the branch name (`git branch --show-current`, e.g. `spl/a-690-fix-x`). Do not search Linear for it here; the scan does that.

## Step 2: Run both scans in parallel

Send both Agent calls in **one message** so they run concurrently, then wait for both results. Paste the brief into each prompt; neither agent sees this conversation. Both are read-only: tell them not to comment, label, or change anything.

### Linear scan

`subagent_type: "linear"`, `model: "sonnet"`. Ask it to:

- If the brief names an existing issue, read it first (title, state, assignee, description summary) and use it to refine the search. Leave it out of the duplicate list.
- Search with several of the search terms, across **all teams**, covering open issues plus issues completed or canceled in the last 30 days.
- Return at most 8 matches, strongest first, one line each: `A-NNN · title · state · assignee · DUPLICATE | RELATED · why it matches`. **DUPLICATE** means it tracks the same change; **RELATED** means it touches the same behavior or code, or blocks or depends on this work. Drop anything weaker. Return `none` if nothing qualifies.

### PR scan

`subagent_type: "general-purpose"`, `model: "sonnet"`. Point it at the current repo (`gh repo view --json nameWithOwner -q .nameWithOwner`) and at any other repo in my-context's repo list where the same change could land. Ask it to:

- Search for open PRs, and for PRs merged or closed in the last 14 days, using the search terms: `gh pr list --repo <r> --state all --search "<terms> updated:>=<date>" --json number,title,author,state,url,updatedAt`.
- Find open PRs that touch the brief's areas, even if their titles look unrelated: `gh pr list --repo <r> --state open --limit 200 --json number,title,author,url,files`, filtered to paths under those areas. For candidates, read the PR body and the diff of the overlapping files (`gh pr diff`) before classifying.
- Return at most 8 matches, strongest first, one line each: `#N · title · author · state · DUPLICATE | RELATED | CONFLICT · why`, with the overlapping files for CONFLICT. **DUPLICATE**: makes the same change. **RELATED**: same feature or bug, but a different change. **CONFLICT**: an open PR that edits the same code in a way that will clash in merge or in behavior. Return `none` if nothing qualifies.

## Step 3: Decide

Report the matches in a short table (both scans together, strongest first), then:

- **Any DUPLICATE or CONFLICT**: stop. Do not file an issue. Explain the overlap and let the user decide: drop the work, coordinate with the author, build on the other PR, or go ahead anyway.
- **Only RELATED matches**: list them and ask with `AskUserQuestion` whether to go ahead. If the user says yes, continue to Step 4 and link the related issues.
- **Nothing found**: say so in one line and continue to Step 4.

## Step 4: Make sure an issue tracks the work

If the brief already names an issue, stop here: report it and the branch name to use.

Otherwise, draft the issue in the main session, since only it has the context. Follow the repo's `create-issue` skill (`.claude/skills/create-issue/SKILL.md`) for the body if the repo has one: summary, context, approach, acceptance criteria, and an estimate of 1, 2, 3, or 5. Keep it scaled to the work; a small fix gets a short issue.

Use these defaults unless the user said otherwise. They come from my-context:

- **Team**: the user's Linear team.
- **Assignee**: the user.
- **Cycle**: the team's current cycle.
- **State**: In Progress.
- **Related**: mark the RELATED Linear issues from Step 2 as related to the new one.
- Leave project, labels, and priority unset unless the conversation settles them.

Spawn the `linear` agent (`model: "sonnet"`) with the title, the Markdown body verbatim, and those fields. Have it create the issue with `save_issue` and return the identifier, URL, and Linear's suggested branch name. Report all three to the user, with the estimate and a one-line reason for it.

From here, the `linear-issues` skill applies: the PR carries `Fixes A-NNN`, and central artifacts and findings go on the issue.
