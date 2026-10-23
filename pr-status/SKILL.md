---
name: pr-status
description: >-
  Report the state of the user's open PRs — draft, awaiting review, reviewed and waiting on the author, conflicts needing a rebase, CI green/red/running, stacked on another PR — grouped into which ones the user must act on and which ones need a reviewer nudged. Defaults to AztecProtocol/aztec-packages and aztec-labs-eng/aztec-node. Use when the user asks about the status of their PRs, what PRs need attention, or whom to nudge for reviews.
argument-hint: "[owner/repo ...]"
---

# PR status

Run the read-only status script. Pass repos in `$ARGUMENTS` to override the default `AztecProtocol/aztec-packages aztec-labs-eng/aztec-node`:

```bash
~/.claude/skills/pr-status/scripts/pr-status.py $ARGUMENTS
```

It makes one GraphQL query for every open PR the viewer authored in those repos, plus one per stacked PR whose parent is not one of the viewer's open PRs. Add `--json` for raw per-PR fields.

## Verdicts

| Verdict | Meaning |
|---|---|
| `ACT` | On the user: red or cancelled CI, CI not run, changes requested, unresolved threads where a reviewer spoke last, no reviewer requested, a reviewer to re-request after new pushes, approved and green (merge), conflicts on a PR with no pending review, or the parent of a stack merged or closed (retarget) |
| `NUDGE` | Waiting on requested reviewers. The age is time since the request. Ping the reviewers. Conflicts here show as a `later` line: rebasing before the review is wasted work, since review changes may need another rebase |
| `WAIT` | Nothing to do: CI running, auto-merge or merge queue pending, or approved but stacked on an open PR |
| `DRAFT` | Draft PRs. Only conflicts, red CI and unanswered threads are flagged; "no reviewer" and "CI not run" are expected for drafts |

A PR can carry `act`, `wait` and `later` lines at once; any `act` line makes the verdict `ACT`. Stacked means the base is neither the default branch nor a `merge-train/*` or `backport-to-*` branch. The parent PR is found by matching its head branch.

## Report

The output groups PRs by verdict (ACT, NUDGE, WAIT, DRAFT), then by repo, then by stack. A stack of two or more of the user's open PRs shows as `Stack #a → #b → …` with its members in that verdict nested below, bottom of the stack first. Members of one stack can land in different verdicts. Relay the output as is. Do not re-derive the state with extra `gh` calls unless something looks wrong. After it, add one short line naming the PRs to act on first and the reviewers to nudge (grouped by reviewer, with the oldest request first). Do not message reviewers, rebase or rerun CI unless the user asks. For a PR the user wants driven to green, suggest `/monitor-pr <number>`.

## Caveats

- GitHub computes mergeability lazily. The script retries once after 5s when any PR reports `UNKNOWN`; PRs that are still unknown show `conflicts unknown`.
- CI dedupes checks by name and keeps the latest run, so a cancelled run superseded by a green one counts as green. A `ci` check that was skipped (aztec CI skips drafts) reads as `not-run`.
- Bot reviews (claude, github-actions) are ignored for review state. Bot comments still count as unresolved threads awaiting a reply.
