---
name: update-node-threat-model
description: Update the Aztec node threat model (security/aztec-node-threat-model.md in AztecProtocol/claudebox) to record a scope or trust decision — typically after a reported finding turns out not to be an issue — and open a PR against labs-main. Use when the user invokes /update-node-threat-model with what to change.
argument-hint: "<what to update, and why the report is not an issue>"
disable-model-invocation: true
---

# update-node-threat-model

The user describes a change to the node threat model in `$ARGUMENTS` (often: "this report is
not an issue because X"). You set up a branch, hand the editing to the `threat-model-editor`
subagent (Opus, high effort), check its diff, push, open the PR and return the link. Keep the
threat model's contents out of your own context: the subagent reads the file, you read the diff.

- Repo: `~/Projects/claudebox` (`AztecProtocol/claudebox`)
- File: `security/aztec-node-threat-model.md`
- Base branch: `labs-main`

If `$ARGUMENTS` is empty or does not say what to change, ask before doing anything.

## 1. Branch and worktree

Never touch the main checkout at `~/Projects/claudebox`; it may be on another branch with local
changes. Pick a short kebab slug for the change and create a worktree in the scratchpad:

```bash
git -C ~/Projects/claudebox fetch origin labs-main
git -C ~/Projects/claudebox worktree add -b spl/threat-model-<slug> <scratchpad>/wt-threat-<slug> origin/labs-main
```

## 2. Delegate the edit

Spawn one `Agent` with `subagent_type: "threat-model-editor"` (its definition pins Opus at high
effort and carries the editing rules). Pass:

- the worktree path and branch name;
- the user's request, verbatim;
- any context the user gave or the conversation holds: the finding text, a report or issue link,
  the reasoning for why it is not a bug;
- the path for the PR body: `<scratchpad>/threat-model-<slug>-pr.md`.

Do not read the threat model yourself or restate its rules in the prompt; the agent does both.

If the agent stops without committing (the request was ambiguous, or the code contradicts it),
relay its question to the user, then continue the same agent with `SendMessage`.

## 3. Check the diff

```bash
git -C <worktree> diff --stat origin/labs-main
git -C <worktree> diff origin/labs-main
```

Confirm that only `security/aztec-node-threat-model.md` changed, that no existing ID was
renumbered or removed, and that the edit says what the user asked — no broader, no narrower.
If something is off, send it back to the same agent with `SendMessage` and re-check.

## 4. Push and open the PR

Read the PR body file the agent wrote. Take the title from the commit subject.

```bash
git -C <worktree> push -u origin spl/threat-model-<slug>
gh pr create --repo AztecProtocol/claudebox --base labs-main --head spl/threat-model-<slug> \
  --title "<commit subject>" --body-file <scratchpad>/threat-model-<slug>-pr.md
```

Then remove the worktree (`git -C ~/Projects/claudebox worktree remove <worktree>`); the branch
lives on the remote.

## 5. Report

Reply with the PR link, then one or two sentences on what the threat model now says, plus any
claim the agent could not verify against the code and any follow-up it suggested.
