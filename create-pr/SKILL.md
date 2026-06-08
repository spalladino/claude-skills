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

Write the description using this structure:

### Title

- Short, under 70 characters
- Use conventional commit style: `fix(scope):`, `feat(scope):`, `chore(scope):`, etc.
- If `$ARGUMENTS` is provided, use it as the title

### Body

```
## Motivation

Explain *why* this change exists. What problem does it solve? If it fixes a bug, describe the bug. Pay special attention at the first messages of the conversation or the beginning of the plan (if any) for motivation clues.

Keep it succinct. No need to expand longer than needed.

## Approach

Explain *how* it was done at a high level. Focus on concepts and subsystems, not individual files.

Keep it succinct. No need to expand longer than needed.

Consider using bullet points or subsections if there are multiple key aspects to the approach.

## API changes

If there are any **public** API changes, describe them here. If not, omit this section.

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
