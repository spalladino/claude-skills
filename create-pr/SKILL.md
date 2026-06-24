---
name: create-pr
description: Create a GitHub pull request for the current branch. Use when the user asks to create, open, or submit a PR.
argument-hint: [title]
---

# Create Pull Request

Create a PR for the current branch following this workflow.

## Step 1: Gather context

Skip this step if you already have the context of what was done in this changeset from the conversation or a plan. Otherwise, gather the following information, by running these in parallel:

- `git status` (never use `-uall`)
- `git diff` to see unstaged changes
- `git diff --cached` to see staged changes
- `git log origin/<base>..HEAD` and `git diff origin/<base>...HEAD` to understand all commits in this branch (ask the user for base branch if unsure) (analyze ALL commits on the branch and not just the latest)

## Step 2: Draft the PR description

Use the conversation context, or a plan if there is any, to understand the motivation.

### Title

- Short, under 70 characters
- Use conventional commit style: `fix(scope):`, `feat(scope):`, `chore(scope):`, etc.
- If `$ARGUMENTS` is provided, use it as the title

### Body — scale it to the size of the change

Match the description to how much the reviewer actually needs. Do not pad a small change into the full template.

**Trivial change** (typo, one-liner, config bump, comment, dependency bump): a single sentence. No headers.

```
Bump `viem` to 2.21.0 to pick up the EIP-7702 fix.
```

**Small, focused change** (one concern, one subsystem): one or two sentences of context, then what you did. Headers optional — a short paragraph is fine.

```
Session tokens never expired, so revoked sessions stayed valid. Add a TTL check in the session middleware.
```

**Substantial change** (new feature, refactor, multiple subsystems): use the sections below. Open with a one-sentence summary, then:

```
## Context

Explain *why* this change exists — the problem it solves, or the bug it fixes. Look at the first messages of the conversation or the start of the plan for clues. 1-3 sentences.

## Approach

Explain *how* it was done at a high level — concepts and subsystems, not individual files. A few sentences, or up to ~5 bullets if there are distinct aspects.

## API changes

Only if there are **public** API changes. Describe what changed for callers. Omit this section entirely otherwise.
```

Do not add a "Changes" / per-package breakdown — the diff already lists the files. Only call out specific packages inside Approach when the *where* is itself non-obvious or important.

### Issue linking

If there is a Linear or GitHub issue in the conversation context (mentioned by the user, referenced in a plan, or fetched via tools), add a `Fixes <identifier>` line at the end of the body:

- **Linear**: `Fixes LIN-123` (use the issue identifier, e.g. `A-690`, `NET-42`)
- **GitHub**: `Fixes #123` (use the issue number)

If multiple issues are relevant, add one `Fixes` line per issue.

### Style rules

- Default to fewer words. When in doubt, cut a sentence rather than add one.
- Do NOT use checklists (`- [ ]`) unless explicitly requested
- Do NOT add a "Test plan" or "Changes" section
- Do NOT add a "Generated with Claude Code" footer
- Write in plain, direct language. No filler, no restating the title.
- Focus on _why_ over _what_ in the context. Focus on concepts over files in the approach.

## Step 3: Create the PR

Run in parallel as needed:

- Push to remote with `-u` if needed
- Create PR with `gh pr create`

Use a HEREDOC for the body:

```bash
gh pr create --title "the pr title" --body "$(cat <<'EOF'
## Context
...

## Approach
...
EOF
)"
```

## Step 4: Return the PR URL
