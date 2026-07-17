---
name: stacked-prs
description: Manage a stack of dependent pull requests with plain git — no Graphite/gt/ghstack. Use when you have a chain of PRs that build on each other and need to carry a change through the whole stack after editing a PR near the base, or when setting up, restacking, or pushing a stack. Covers `git history` (`reword`/`split` in Git 2.54+, `fixup` in 2.55+) and `git rebase --update-refs` (Git 2.38+), force-with-lease pushing, and the config to make it the default.
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

Native git gives you two purpose-built tools for this — no Graphite, `gt`, `ghstack`, or `spr`
needed:

- **`git history`** (experimental; `reword`/`split` in Git 2.54+, `fixup` in 2.55+) — rewrites an
  *existing* commit in an early PR (`fixup` a fix into it, `reword` its message, `split` it) and
  automatically updates every descendant branch. The cleanest answer to "I need to change a PR near
  the base"; see the next section.
- **`git rebase --update-refs`** (Git 2.38+) — the portable workhorse. Rebase the tip branch once
  and git moves every intermediate branch pointer. Use it to restack onto a moved base, to push a
  change through conflicts, or on any git older than 2.54.

Rule of thumb: **editing a commit already in the stack → `git history`; restacking onto a new
base, or anything that will conflict → `git rebase --update-refs`.**

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

## Editing a commit in an early PR — `git history` (Git 2.54+)

This is the direct answer to "I need to fix a PR near the base and carry the change up the whole
stack." `git history` rewrites an *existing* commit and, by default, **rewrites every local branch
descended from it** — the entire stack follows in one command, with no interactive todo, no
`--onto`, and no manual force-moving of the intermediate branches.

Three subcommands, all defaulting to `--update-refs=branches` (pass `--update-refs=head` to move
only the current branch):

```bash
# Fix a bug in an earlier commit (e.g. the base commit of part-1), staged from anywhere in the stack:
git add <fixed-files>
git history fixup <commit>         # fold the staged fix into <commit>; part-1/2/3 all follow

# Reword an earlier commit's message (does not touch your working tree):
git history reword <commit>

# Split an earlier commit into two, choosing hunks interactively:
git history split <commit>
```

`fixup` folds your staged changes into `<commit>` via a three-way merge, preserving its message
and author. It is like `git commit --fixup` + an autosquash rebase, except `git history` rewrites
*every* local descendant branch by default, not just the refs inside a rebase range — precisely
the stacked-PR case. Add `--dry-run` to print the ref updates (in `git update-ref` format) without
applying them.

**Before you reach for it:**

- **Requires Git 2.54+** (`reword`, `split`) / **2.55+** (`fixup`). Older git — including 2.48 —
  does not have it; use `rebase --update-refs` below. Check with `git version`.
- **It refuses any operation that would conflict**, and is atomic — it never leaves a half-broken
  tree, but it also cannot push a fix through a conflict. For a conflicting change, use rebase.
- **Does not work with histories that contain merge commits** (yet), and **runs no githooks**
  (as of 2.55).
- Its reach is *broader* than `rebase --update-refs`: it rewrites every descendant branch, not
  just refs inside a rebase range — so a stray local branch on that commit moves too (see Gotchas).

## Restacking with `git rebase --update-refs` (Git 2.38+)

The portable path: works on any git ≥ 2.38, restacks onto a moved base, and pushes changes through
conflicts. Rebase the tip branch and git moves the intermediate branch pointers for you.

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
a plain commit on top. If instead you **rewrite** an existing commit in `part-1` (changing its
SHA), this command breaks: git replays the stale pre-rewrite commits and hands you bogus `add/add`
conflicts on code that is already correct. For a content fix, message change, or split of that
commit, `git history` (see above) is the clean path — `fixup` (Git 2.55+), or `reword`/`split`
(Git 2.54+). To **drop or reorder** commits (which `git history` does not do), or on git older
than 2.54, use Case C (interactive `edit`), or the explicit `--onto` form — replay everything
above the *old* `part-1` tip onto the *new* one:

```bash
git checkout spl/part-3
git rebase --update-refs --onto spl/part-1 <old-part-1-tip> spl/part-3
```

### Case C — edit, reorder, or insert a commit in the middle interactively

Interactive rebase is the general tool — it can amend, reword, split, drop, reorder, or insert any
commit partway down the stack. (For a plain amend/reword/split, `git history` above is quicker;
reach here for **drop, reorder, and insert**, or on git older than 2.54.) Rebase with the tip
checked out, targeting the base. Git inserts `update-ref` lines into the todo marking each branch
boundary:

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
  global config on, where even `git pull --rebase` restacks. `git history` is broader still — it
  rewrites *every descendant* branch, not just refs in a range — so the same stray-branch caveat
  applies; use `--update-refs=head` to limit it to the current branch, or `--dry-run` to preview.
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

Rebase commands run with the **tip branch checked out**; `git history` can run from anywhere in
the stack.

| You did | Run |
|---|---|
| Fix an existing commit in an early PR (Git 2.55+) | `git add <files> && git history fixup <commit>` |
| Reword / split an existing commit (Git 2.54+) | `git history reword <commit>` / `git history split <commit>` |
| Base branch moved | `git fetch && git rebase --update-refs origin/<base>` |
| Added a *new* commit on an early branch | `git rebase --update-refs <that-branch>` |
| Drop / reorder / insert a commit, or amend on git < 2.55 | `git rebase -i --update-refs origin/<base>` (do it in the todo) |
| Merged the bottom PR (squash) | `git rebase --update-refs --onto origin/<base> <merged-branch> <tip>` then `git branch -D <merged-branch>` |
| Ready to publish | `git push --atomic --force-with-lease --force-if-includes origin <b1> <b2> <b3>` |
