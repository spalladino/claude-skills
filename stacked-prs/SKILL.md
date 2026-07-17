---
name: stacked-prs
description: Manage a stack of dependent pull requests with plain git — no Graphite/gt/ghstack. Use when you have a chain of PRs that build on each other and need to rebase the whole stack after changing a PR near the base, or when setting up, reordering, or pushing a stack. Covers `git rebase --update-refs`, force-with-lease pushing, and the config to make it the default.
argument-hint: [what you changed, e.g. "added a commit to the base PR, restack everything"]
---

# Managing stacked PRs with git history

A **stack** is a chain of branches where each builds on the previous one, and each has its own
PR. You split a large change into reviewable pieces, or keep working past a PR that is still in
review:

```
next  <-  part-1  <-  part-2  <-  part-3
          (PR #1)     (PR #2)     (PR #3, base: part-2)
```

The hard part is not creating the stack — it is keeping it in sync. Any time you change a PR
**near the base** (rebase onto a moved base branch, or amend/insert a commit in an early branch),
every branch above it still points at the *old* commits and must be replayed. Doing that branch
by branch with `git rebase --onto` is tedious and error-prone.

Native git solves this with **`git rebase --update-refs`** (Git 2.38+, October 2022). You rebase
the tip branch once, and git moves every intermediate branch pointer for you. This is the whole
skill. You do **not** need Graphite, `gt`, `ghstack`, or `spr` for this.

## Enable it by default

Do this once so every rebase keeps your stack intact:

```bash
git config --global rebase.updateRefs true
```

With this on, plain `git rebase <base>` behaves like `--update-refs`. The rest of this doc shows
the flag explicitly so the commands work regardless of config; drop `--update-refs` if you have
set the config. Turn it off for a single rebase with `--no-update-refs`.

## Setting up a stack

Branch each piece off the previous one:

```bash
git checkout -b spl/part-1 next
# ...commits for part 1...
git checkout -b spl/part-2 spl/part-1
# ...commits for part 2...
git checkout -b spl/part-3 spl/part-2
# ...commits for part 3...
```

Then open each PR against the branch below it: `part-1 -> next`, `part-2 -> part-1`,
`part-3 -> part-2`. Reviewers see only each PR's own diff.

## The core scenario: you changed a PR near the base

### Case A — the base branch moved

`next` (or the merge-train base) got new commits and you want the whole stack on top:

```bash
git fetch origin
git checkout spl/part-3          # the TIP of the stack
git rebase --update-refs origin/next
```

Git replays `part-1`, `part-2`, and `part-3` onto the new `next` and moves all three branch
pointers. One command, whole stack restacked.

### Case B — you added a *new* commit on top of an early branch

Say review feedback lands on `part-1`. Add the fix as a **new commit** on `part-1`, then replay
everything above it — again from the tip:

```bash
git checkout spl/part-1
# ...make the fix...
git commit -am "fix: address review feedback"

git checkout spl/part-3          # tip again
git rebase --update-refs spl/part-1
```

`part-2` and `part-3` are replayed onto the new `part-1`, and `part-2`'s pointer is moved on the
way. (`part-1` is already where you want it, so it is the rebase target, not something being
replayed.)

This works **only** because the old `part-1` tip is still an ancestor of the new one — the fix is
a plain commit on top. If instead you **amend, reword, drop, or reorder** an existing commit in
`part-1` (rewriting its SHA), this command breaks: git tries to replay the stale pre-rewrite
commits and hands you bogus `add/add` conflicts on code that is already correct. For a rewrite,
use Case C (interactive `edit` handles it cleanly), or the explicit `--onto` form — replay
everything above the *old* `part-1` tip onto the *new* one:

```bash
git checkout spl/part-3
git rebase --update-refs --onto spl/part-1 <old-part-1-tip> spl/part-3
```

### Case C — edit, reorder, or insert a commit in the middle interactively

To amend, reword, split, drop, or reorder a commit that lives partway down the stack, rebase
interactively with the tip checked out, targeting the base. Git inserts `update-ref` lines into
the todo marking each branch boundary:

```bash
git checkout spl/part-3
git rebase -i --update-refs origin/next
```

```
pick d323fff part 1 commit A
pick 45768bc part 1 commit B
update-ref refs/heads/spl/part-1

pick 9b97cc6 part 2 commit C
update-ref refs/heads/spl/part-2

pick 31ab2ab part 3 commit D
```

Each `update-ref refs/heads/<branch>` line means "after replaying the commit above me, set this
branch here." Mark a commit `edit` (or `reword`/`squash`), do the work, `git rebase --continue`,
and every downstream branch follows automatically. You can also move a `pick` across an
`update-ref` line to relocate a commit from one PR to another.

## Push the whole stack

Rebasing rewrites SHAs, so every branch needs a force-push. Push them in one command:

```bash
git push --force-with-lease origin spl/part-1 spl/part-2 spl/part-3
```

Use **`--force-with-lease`**, never bare `--force`. It refuses the push if the remote branch
moved since your last fetch — the guard that stops you clobbering a teammate's (or a bot's) commit
on your branch. Two hardening flags:

- `--force-if-includes` (Git 2.30+) — guarantees your push includes everything you have actually
  seen, closing the background-fetch gap described in Gotchas.
- `--atomic` — makes the multi-branch push all-or-nothing. Without it, refs update independently,
  so a single failed lease leaves the remote stack half-updated and PR diffs briefly wrong.

```bash
git push --atomic --force-with-lease --force-if-includes origin spl/part-1 spl/part-2 spl/part-3
```

## Merging the stack, bottom-up

Merge from the base of the stack upward: land `part-1`'s PR into `next` first. Most repos
**squash-merge**, which collapses `part-1`'s commits into one new commit on `next` with a fresh
SHA — so the rest of the stack is now sitting on the old, orphaned `part-1` commits.

When `part-1`'s PR merges and its head branch is auto-deleted, GitHub automatically retargets
`part-2`'s PR onto `next`. **Verify** that retarget landed (it only fires on branch deletion),
then restack the remainder onto the updated base with an explicit `--onto`, and drop the merged
local branch:

```bash
git fetch origin
git checkout spl/part-3
git rebase --update-refs --onto origin/next spl/part-1 spl/part-3
git branch -D spl/part-1          # merged; its local ref is now stale
```

Do **not** reach for a plain `rebase --update-refs origin/next` here: that replays `part-1`'s
stale commits, and the moment `next` has any other change touching the same files you get
conflicts on code that is already merged. The `--onto ... spl/part-1` form excludes everything up
to the old `part-1` tip, so only `part-2` and `part-3` replay.

## Gotchas

- **Rebase from the tip.** `--update-refs` only moves branches that point at commits *inside the
  rebase you are running*. Rebase the top branch so every intermediate branch is in range;
  rebasing a middle branch leaves the ones above it stranded.
- **It moves *every* local branch in range, not just your stack.** Any local branch pointing at a
  rebased commit is force-moved — including a `backup-of-part-2` you made "just in case", or a
  colleague's branch you happened to check out. A non-interactive rebase does this with no prompt;
  in interactive mode you can delete the stray `update-ref` line. This bites hardest with the
  global config on, where even `git pull --rebase` restacks.
- **Branches checked out in another worktree are skipped silently.** Such a branch is left
  pointing at the old commits with no warning. After every restack, read the "Updated the
  following refs" list git prints — it is the only confirmation of what actually moved.
- **Only branches that exist when the rebase starts are tracked.** The `update-ref` lines are
  generated up front, so a branch you create mid-rebase is not moved (you can hand-add a line with
  `git rebase --edit-todo`).
- **Force-with-lease can be defeated by background fetches.** If something auto-fetches (some IDEs
  do), the lease compares against the freshly-fetched ref and may pass when you did not intend it
  to. `--force-if-includes` closes that gap.
- **Requires Git 2.38+** for `--update-refs`. Check with `git version`.

## Quick reference

All commands run with the **tip branch checked out**.

| You did | Run |
|---|---|
| Base branch moved | `git fetch && git rebase --update-refs origin/<base>` |
| Added a *new* commit on an early branch | `git rebase --update-refs <that-branch>` |
| Amended / reworded / reordered / dropped a mid-stack commit | `git rebase -i --update-refs origin/<base>` (do it in the todo) |
| Merged the bottom PR (squash) | `git rebase --update-refs --onto origin/<base> <merged-branch> <tip>` then `git branch -D <merged-branch>` |
| Ready to publish | `git push --atomic --force-with-lease --force-if-includes origin <b1> <b2> <b3>` |
