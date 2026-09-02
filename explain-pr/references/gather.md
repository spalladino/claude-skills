# gather — build the dossier (subagent recipe)

You are the **gather** subagent for the `explain-pr` skill. You do the clerical half:
resolve the PR or PR stack, pin shas, and write a `dossier.md` that the (expensive) main
agent reads *instead of* the raw diff.

Rules:

- Never explain, judge, or summarise the change. Never guess a line number.
- Return a **short summary only** — no diff, no dossier content, no file dumps.
- `$REPO` = `git rev-parse --show-toplevel`. All paths are repo-root-relative POSIX paths,
  exactly as `git diff --name-only` prints them.
- Work dir `$WORK` is given to you. Create it with `mkdir -p`.

---

## 1. Resolve the target

### A single PR

```bash
gh pr view <n> --json number,title,body,url,baseRefName,headRefName,commits,files > $WORK/pr-<n>.json
git fetch origin "$(jq -r .baseRefName $WORK/pr-<n>.json)" "$(jq -r .headRefName $WORK/pr-<n>.json)"
BASE=$(git merge-base origin/<baseRefName> origin/<headRefName>)
HEAD=$(git rev-parse origin/<headRefName>)
```

Use the **merge base**, not the tip of the base branch, so changes that landed on the base
after the PR forked are excluded.

### A PR stack

The user may give several numbers, or one number and the word "stack". Detect the stack
yourself: PR *n* is stacked on PR *m* when `n.baseRefName == m.headRefName`. Starting from
the given PR(s), follow `baseRefName` downwards until you reach a branch that is not the
head of an open PR (`gh pr list --head <branch> --state open --json number`), and follow
upwards with `gh pr list --base <headRefName> --state open --json number,title`. Order the
stack bottom (closest to main) to top.

For each PR in the stack record its own `base → head`: the base of PR *k* is the head sha
of PR *k-1* (so each PR's dossier section shows only its own diff), and the bottom PR's base
is its merge base with its target branch. Whole-stack `BASE`/`HEAD` = bottom base, top head.

### A commit range

`<a>..<b>`: `BASE=$(git merge-base <a> <b>); HEAD=$(git rev-parse <b>)`. Treat it as a
single "PR" with no title or body.

## 2. Pick the slug

Given `--slug`, use it. Otherwise: single PR → `pr-<n>`; stack → `pr-<bottom>-<top>`;
range → `<shortbase>-<shorthead>`. Kebab-case only.

## 3. Hunk arithmetic — the one thing that must be exact

`@@ -a,b +c,d @@` touches head lines `c .. c+d-1`. A missing count means 1. `d == 0` is a
pure deletion: record `head <c> (deletion)`.

```bash
git diff -U0 $BASE..$HEAD -- <path> | grep -E '^@@' | \
  sed -E 's/^@@ -[0-9,]+ \+([0-9]+)(,([0-9]+))? @@.*/\1 \3/' | \
  awk '{n=($2==""?1:$2); if(n==0) print $1" DELETION"; else print $1"-"($1+n-1)}'
```

## 4. Write `$WORK/dossier.md`

One file, this shape. For a stack, repeat the `## PR` block per PR in stack order, and
put each PR's files under its own `### Files (#n)` heading using that PR's own base/head.

````markdown
# Dossier: <slug>

repo: <owner/repo>   base `<BASE>` → head `<HEAD>`
stack: #25254 (cee7f40→9b21c05) → #25282 (9b21c05→38e30f9)     # omit for a single PR

## PR #25254 "<title>" — <url>
branch: <headRefName> → <baseRefName>
body:
<the PR body, trimmed to what states intent: drop CI checklists, screenshots, templates,
"how to test" boilerplate. Keep under ~30 lines. If it links an issue, include the issue
title and 2–4 lines of its body via `gh issue view`.>
commits:
- `abc1234` <subject>
stat:
```
<git diff --stat <base>..<head>>
```
skipped (not diffed below):
- `yarn.lock` (+1204 −31) — lockfile

### Files (#25254)

#### `yarn-project/kv-store/src/lmdb-v2/store.ts` — M, +15 −9

imported by: `yarn-project/archiver/src/log_store.ts`, `yarn-project/p2p/src/tx_pool.ts` (+3 more) · 2 test files

##### `@@ -108,9 +112,15 @@ export class Store` → head **112–126**

```diff
<the -U3 hunk body, verbatim>
```
````

Rules for the dossier:

- Every file from `git diff --name-status`, in `--stat` order, except skipped ones. Skip
  lockfiles, vendored trees, snapshots, and files marked generated (`@generated` in the
  first 5 lines or `linguist-generated`). List each skipped file with its `+/−` counts.
- Hunk bodies come from `git diff -U3 <base>..<head> -- <path>` **verbatim** — three lines
  of context so the reader can follow the code. Head line ranges come from the `-U0`
  arithmetic above, not from the `-U3` header. Do not summarise, reflow or truncate.
- Renames: `R old.ts → new.ts` in the file heading; path = the head path.
- **`imported by:`** — for each non-test source file, a cheap grep at head for the file's
  stem in import forms (`git grep -l -E "['/]<stem>(\.[a-z]+)?['\"]" $HEAD -- ':!<path>'`,
  or the language's equivalent). Up to 4 non-test importers, then `(+N more)`, then the
  count of test files. `imported by: none found` when empty. A heuristic, not a promise.
- If the whole dossier would exceed ~5000 lines, still include every hunk, but say so in
  the summary so the main agent can narrow scope.

## 5. Return

Report **only** this, as plain lines:

```
slug: pr-25254-25282
repo: aztecprotocol/aztec-packages
base: cee7f40   head: 38e30f9
stack: #25254 cee7f40→9b21c05 "title" · #25282 9b21c05→38e30f9 "title"
files: 14 changed (+412 −96), 2 skipped (yarn.lock, src/generated/api.ts)
dossier: <$WORK>/dossier.md (612 lines, 38 hunks)
notes: <anything odd — missing branch, dirty worktree, huge diff, a PR in the stack already merged>
```
