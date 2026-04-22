---
name: create-pr
description: Create a GitHub pull request for the current branch. Use when the user asks to create, open, or submit a PR.
argument-hint: [title]
---

# Create Pull Request

Create a PR for the current branch following this workflow.

## Step 1: Gather context

Run these in parallel:

- `git status` (never use `-uall`)
- `git diff` to see unstaged changes
- `git diff --cached` to see staged changes
- `git log origin/<base>..HEAD` and `git diff origin/<base>...HEAD` to understand all commits in this branch (ask the user for base branch if unsure)

## Step 2: Draft the PR description

Use the conversation context, or a plan if there is any, to understand the motivation.

Analyze ALL commits on the branch (not just the latest) and write the description using this structure:

### Title

- Short, under 70 characters
- Use conventional commit style: `fix(scope):`, `feat(scope):`, `chore(scope):`, etc.
- If `$ARGUMENTS` is provided, use it as the title

### Body

```
## Motivation

Explain *why* this change exists. What problem does it solve? If it fixes a bug, describe the bug.
Keep it succinct: 2-4 sentences.

## Approach

Explain *how* it was done at a high level. Focus on concepts and subsystems, not individual files.
Keep it succinct: 2-4 sentences.

## Changes

Outline the main packages or areas changed as a bulleted list:
- **package-name**: Brief description of what changed and why
- **package-name (tests)**: Brief description of test changes
```

### Issue linking

If there is a Linear or GitHub issue in the conversation context (mentioned by the user, referenced in a plan, or fetched via tools), add a `Fixes <identifier>` line at the end of the body:

- **Linear**: `Fixes LIN-123` (use the issue identifier, e.g. `A-690`, `NET-42`)
- **GitHub**: `Fixes #123` (use the issue number)

If multiple issues are relevant, add one `Fixes` line per issue.

### Style rules

- Do NOT use checklists (`- [ ]`) unless explicitly requested
- Do NOT add a "Test plan" section
- Do NOT add a "Generated with Claude Code" footer
- Write in plain, direct language. No filler.
- Focus on _why_ over _what_ in the motivation. Focus on concepts over files in the approach.

## Step 3: Create the PR

Run in parallel as needed:

- Push to remote with `-u` if needed
- Create PR with `gh pr create`

Use a HEREDOC for the body:

```bash
gh pr create --title "the pr title" --body "$(cat <<'EOF'
## Motivation
...

## Approach
...

## Changes
...
EOF
)"
```

## Step 4: Return the PR URL
