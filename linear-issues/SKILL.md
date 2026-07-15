---
name: linear-issues
description: Capture the full history of how a Linear issue was tackled — link the PR with a "Fixes A-NNN" line, attach intermediate artifacts (failed-run logs, plans, traces) to the issue, and record investigation findings (root cause, fix, ruled-out approaches) as comments. Use whenever working on a Linear issue: implementing it, debugging it, or investigating a bug.
---

# Working with Linear issues

The goal: **use the Linear issue as the durable record of how we tackled it.** Chat logs and local scratch files disappear; the issue persists. Anyone who opens it later — including future us — should be able to reconstruct what the problem was, what we tried, what we ruled out, which artifacts mattered, and how it was resolved.

This runs *alongside* the actual work, not instead of it. Whenever you're working on a Linear issue (identifier looks like `A-NNN`, `NET-42`, etc.), do the four things below.

## Linear MCP toolbox — call these directly, don't search for how

- **Find the identifier first** (`A-NNN`) if you don't already have it — derive it from the branch name (Linear embeds it, e.g. `spl/a-690-fix-x`), the user's message, or the PR description; if still unknown, search with `mcp__linear-server__list_issues` or ask. Don't guess.
- **Read the issue** — `mcp__linear-server__get_issue` `{ id: "A-NNN" }`. Returns description, state, existing attachments, and the suggested git branch name. Do this first.
- **Read existing discussion** — `mcp__linear-server__list_comments` `{ issueId: "A-NNN" }`. Check before posting so you don't duplicate a comment.
- **Post / update a comment** — `mcp__linear-server__save_comment` `{ issueId: "A-NNN", body }`. Reply in a thread: `{ parentId, body }`. Edit an existing comment: `{ id, body }`.
- **Attach a written doc** — `mcp__linear-server__save_document` `{ issue: "A-NNN", title, content }`. Capture the returned doc id; update later with `{ id, content }`.
- **Attach a raw file** — see [Attaching a file](#attaching-a-raw-file) below.
- **Link a URL on the issue** (PR, CI run, dashboard) — `mcp__linear-server__save_issue` `{ id: "A-NNN", links: [{ url, title }] }`. Append-only; existing links are never removed.

> `body`/`content` is **Markdown** — pass literal newlines, not `\n` escape sequences. (When to use a doc vs. a file attachment is covered in §2.)

---

## 1. Link the PR back to the issue

Always make the PR link to the Linear issue. Add a line to the **PR description**:

```
Fixes A-NNN
```

Linear's GitHub integration recognizes `Fixes` / `Closes` / `Resolves <identifier>` in the PR title, description, or branch name, auto-links the PR to the issue, and (workflow-dependent) typically moves it to Done on merge. Use the **issue identifier** (`A-690`), never the UUID. One `Fixes` line per issue if several apply.

- The `create-pr` skill already adds this when an issue is in the conversation context — so if you used it, this is done. Just confirm the right identifier is present.
- Fallback if the PR didn't auto-link (no integration, or the magic word was missing): attach the PR URL explicitly with `mcp__linear-server__save_issue` `{ id: "A-NNN", links: [{ url: "<pr-url>", title: "PR: <title>" }] }`.

---

## 2. Attach intermediate artifacts to the issue

Any artifact that was *central* to the work — and that you'd want to look at again — goes onto the issue so it survives the loss of the local workspace. Examples: the log of a failed run we're debugging, a stack trace, profiler output, a JSON dump of bad state, a screenshot, or the written plan we worked from.

Pick the right mechanism:

| Artifact | How |
|---|---|
| Something **you authored in markdown** (the plan, an investigation writeup, a design note) | Linear **document** parented to the issue — `save_document { issue: "A-NNN", title, content }` |
| A **raw file** produced by a tool or run (failed-test log, trace, screenshot, JSON, large diff) | **File attachment** via the upload flow below — keeps it verbatim |

Don't attach noise — only artifacts that are genuinely relevant to understanding or reproducing the issue. Title each one so it's obvious what it is and why it's there (e.g. "Failed run log — flaky e2e_block_building, run 4821").

### Attaching a raw file

Four steps, **one file at a time** — the signed URL from step 2 expires in **60s**, so don't prepare a file until you're ready to PUT it immediately, and never batch the prepare calls. The file isn't on the issue until step 4 succeeds.

```bash
# 1. Get the EXACT byte size and choose a contentType. The `size` you pass in
#    step 2 must equal the bytes you PUT, so don't edit the file in between.
#    text/plain (.log/.txt) · text/markdown (.md) · application/json (.json)
#    image/png (.png) · application/octet-stream (unknown/binary)
stat -c %s /path/to/run.log        # -> <SIZE> in bytes
```

```
# 2. Prepare the upload — returns { assetUrl, uploadRequest: { url, headers } }
mcp__linear-server__prepare_attachment_upload
  { issue: "A-NNN", filename: "run.log", contentType: "text/plain", size: <SIZE> }
```

```bash
# 3. PUT the raw bytes to uploadRequest.url. Emit one -H per entry in
#    uploadRequest.headers, verbatim (exact casing). Don't base64-encode or
#    transform the file.
curl -X PUT --data-binary @/path/to/run.log \
  -H "<header-1-from-uploadRequest.headers>: <value-1>" \
  -H "<header-2-from-uploadRequest.headers>: <value-2>" \
  "<uploadRequest.url>"
```

```
# 4. REQUIRED — link the uploaded asset to the issue (until this runs, nothing
#    is attached, even though the PUT succeeded).
mcp__linear-server__create_attachment_from_upload
  { issue: "A-NNN", assetUrl: "<assetUrl>", title: "Failed run log", subtitle: "flaky e2e, run 4821" }
```

A **403 on the PUT** means either a header was dropped/altered *or* the 60s window lapsed (a permission prompt on the `curl` can eat it). Don't retry the dead URL — re-run step 2 for a fresh `assetUrl` + headers, discard the old ones, and PUT again right away.

Ignore the deprecated `create_attachment` (base64) tool — it eats context; use the flow above.

---

## 3. Record investigation findings as comments

For any issue that's about *figuring something out* (a bug, a regression, "why is X slow", "investigate Y"), narrate the investigation on the issue so it reads like a timeline. Post a short comment **once you've validated an insight** — confirmed it, not merely suspect it — rather than only at the end. Don't post hunches; wait until it's verified, then record it:

- When you've **confirmed the root cause** (reproduced it, traced it, or otherwise verified — not just a guess) → post it.
- When the **fix is in place and works** → post what changed and why it resolves the issue.
- Note the **approaches you ruled out** and why — this is often the most valuable part later, because it stops the next person from re-walking dead ends.

Use `mcp__linear-server__save_comment` `{ issueId: "A-NNN", body }`. Keep comments tight; **link to the attached log/doc** rather than pasting large output inline. Template:

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

State changes (To Do → In Progress → Done) are usually handled by the PR integration on merge; only set state manually with `save_issue { id, state }` if the user asks or the integration isn't wired up.
