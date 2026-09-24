---
name: linear-issues
description: Capture the full history of how a Linear issue was tackled — link the PR with a "Fixes A-NNN" line, attach intermediate artifacts (failed-run logs, plans, traces) to the issue, and record investigation findings (root cause, fix, ruled-out approaches) as comments. Use whenever working on a Linear issue: implementing it, debugging it, or investigating a bug.
---

# Working with Linear issues

The goal: **use the Linear issue as the durable record of how we tackled it.** Chat logs and local scratch files disappear; the issue persists. Anyone who opens it later — including future us — should be able to reconstruct what the problem was, what we tried, what we ruled out, which artifacts mattered, and how it was resolved.

This runs *alongside* the actual work, not instead of it. Whenever you're working on a Linear issue (identifier looks like `A-NNN`, `NET-42`, etc.), do the four things below.

## All Linear access goes through the `linear` agent

Linear's MCP responses are token-heavy, so the main session never calls them directly — a `PreToolUse` hook denies it. Spawn the **`linear`** agent (Agent tool, `subagent_type: "linear"`), tell it what you need, and it returns a compact summary while the raw payloads stay in its context.

- **Batch.** Give it every Linear step of the current milestone in one prompt — read the issue *and* its comments, or post the comment *and* attach the log *and* link the PR. One agent, one round trip.
- **Ask narrowly.** "State, assignee and description of A-690" beats "tell me about A-690". Say what you want back.
- **Find the identifier first** (`A-NNN`) — derive it from the branch name (Linear embeds it, e.g. `spl/a-690-fix-x`), the user's message, or the PR description. Only ask the agent to search when it's genuinely unknown, and don't guess.
- **What it can do:** read an issue, read/post/edit comments, attach a markdown document, attach a raw file (hand it absolute paths plus a title and subtitle for each), append a link to the issue, set state.
- `body`/`content` is **Markdown** — pass literal newlines, not `\n` escape sequences.

The Linear-side mechanics (tool names, the attachment upload dance) live in the agent definition at `~/.claude/agents/linear.md`; you don't need them here.

---

## 1. Link the PR back to the issue

Always make the PR link to the Linear issue. Add a line to the **PR description**:

```
Fixes A-NNN
```

Linear's GitHub integration recognizes `Fixes` / `Closes` / `Resolves <identifier>` in the PR title, description, or branch name, auto-links the PR to the issue, and (workflow-dependent) typically moves it to Done on merge. Use the **issue identifier** (`A-690`), never the UUID. One `Fixes` line per issue if several apply.

- The `create-pr` skill already adds this when an issue is in the conversation context — so if you used it, this is done. Just confirm the right identifier is present.
- Fallback if the PR didn't auto-link (no integration, or the magic word was missing): ask the `linear` agent to attach the PR URL to the issue as a link, titled `PR: <title>`.

---

## 2. Attach intermediate artifacts to the issue

Any artifact that was *central* to the work — and that you'd want to look at again — goes onto the issue so it survives the loss of the local workspace. Examples: the log of a failed run we're debugging, a stack trace, profiler output, a JSON dump of bad state, a screenshot, or the written plan we worked from.

Pick the right mechanism:

| Artifact | How |
|---|---|
| Something **you authored in markdown** (the plan, an investigation writeup, a design note) | Linear **document** parented to the issue — give the `linear` agent the title and the markdown |
| A **raw file** produced by a tool or run (failed-test log, trace, screenshot, JSON, large diff) | **File attachment** — give the `linear` agent the absolute path; it keeps the file verbatim |

Don't attach noise — only artifacts that are genuinely relevant to understanding or reproducing the issue. Title each one so it's obvious what it is and why it's there (e.g. "Failed run log — flaky e2e_block_building, run 4821").

### Attaching a raw file

Hand the `linear` agent the issue identifier, the **absolute path** of each file, and a title and subtitle for each — it knows the upload flow. Ask it back for one line per file (`<filename> · attached | FAILED <error>`) and nothing else. Never read a big log into your own context just to attach it.

If the same agent is also linking a URL (§1 fallback) or setting state, hand it those in the same prompt.

---

## 3. Record investigation findings as comments

For any issue that's about *figuring something out* (a bug, a regression, "why is X slow", "investigate Y"), narrate the investigation on the issue so it reads like a timeline. Post a short comment **once you've validated an insight** — confirmed it, not merely suspect it — rather than only at the end. Don't post hunches; wait until it's verified, then record it:

- When you've **confirmed the root cause** (reproduced it, traced it, or otherwise verified — not just a guess) → post it.
- When the **fix is in place and works** → post what changed and why it resolves the issue.
- Note the **approaches you ruled out** and why — this is often the most valuable part later, because it stops the next person from re-walking dead ends.

Ask the `linear` agent to post the comment on `A-NNN` (pass the body verbatim). Keep comments tight; **link to the attached log/doc** rather than pasting large output inline. Template:

```markdown
**Root cause** — <one or two sentences on the actual cause>.

**Fix** — <what changed and why it resolves it>. (PR: <url>)

**Ruled out** — <approaches tried or considered, and why each didn't pan out>.
```

A fast investigation can collapse into a single comment. A long one should be several comments over time so the chronology is visible — use a fresh top-level comment for each distinct milestone, and `parentId` replies only when amending or continuing a specific earlier comment.

---

## 4. Close the loop

Before you consider the work done on the issue, verify:

- [ ] If the work produced a PR, it links back (`Fixes A-NNN`).
- [ ] Central artifacts are attached (plan as a doc, failed-run logs/traces as files).
- [ ] For investigations, a comment captures **cause / fix / ruled-out**.

State changes (To Do → In Progress → Done) are usually handled by the PR integration on merge; only ask the `linear` agent to set state if the user asks or the integration isn't wired up.
