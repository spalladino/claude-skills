# gather — collect everything the review needs (sonnet subagent recipe)

You are the **gather** subagent for `review-pr`: resolve the PR, pin shas, check out a
disposable worktree, write the files below. Never explain, judge or summarise the change.
Read-only on GitHub and Linear; no installs, builds or tests. The one thing you change on
disk is the cache under `$WORK`: the worktree, the files below, and worktrees gc removes.

Inputs: `$SKILL_DIR`, `$REPO` (absolute repo root), the PR number, `fresh` (yes with
`--fresh`). You compute `$WORK` (§1) and return it in §10.

```
$WORK/meta.json     # slug, repo_root, owner_repo, pr, branch, base, head, state, mode, prev_head, wt, updated_at
$WORK/wt/           # git worktree, detached at head, no deps installed
$WORK/dossier.md    # PR body, commits, stat, every hunk with head line ranges
$WORK/threads.md    # all discussions with resolution state and per-thread diffs
$WORK/threads-resolved.md  # resolved threads in full
$WORK/linear.md     # linked Linear issues
$WORK/decoherence.md, decoherence.json  # flow signals and area fix history
$WORK/fix-history.md  # older fixes and checks around the touched functions
$WORK/interdiff.md  # incremental mode only
$WORK/threads.prev.md  # same-head mode only: threads.md as the last run left it
$WORK/.stamp        # touched on every run; gc.sh reads its mtime
```

Quote every path in shell commands.

## 1. Resolve the PR and pin shas

```bash
OWNER_REPO=$(git -C "$REPO" remote get-url origin | sed -E 's#.*github.com[:/]([^/]+/[^/.]+)(\.git)?$#\1#')
WORK="${XDG_CACHE_HOME:-$HOME/.cache}/review-pr/$(echo "$OWNER_REPO" | tr '/' '-' | tr '[:upper:]' '[:lower:]')-pr-<n>"
mkdir -p "$WORK" && touch "$WORK/.stamp"
gh pr view <n> --repo "$OWNER_REPO" --json number,title,body,url,state,isDraft,author,baseRefName,headRefName,headRefOid,\
headRepository,headRepositoryOwner,isCrossRepository,mergeable,reviewDecision,statusCheckRollup,\
commits,files,labels,closingIssuesReferences,reviews > "$WORK/pr.json"
HEAD=$(jq -r .headRefOid "$WORK/pr.json")
BASE_REF=$(jq -r .baseRefName "$WORK/pr.json")
# refs/pull/<n>/head works for same-repo and fork PRs alike; a branch fetch does not.
git -C "$REPO" fetch -q origin "refs/pull/<n>/head" "$BASE_REF"
git -C "$REPO" cat-file -e "$HEAD^{commit}" || { echo "head $HEAD not fetched; the PR moved while gathering?"; exit 1; }
BASE=$(git -C "$REPO" merge-base "origin/$BASE_REF" "$HEAD")
BEHIND=$(git -C "$REPO" rev-list --count "$HEAD..origin/$BASE_REF")
ME=$(gh api user --jq .login)
```

Use `$HEAD` everywhere; if a later step sees a different tip, note it in the summary rather
than mixing shas. Diff against the merge base, never the base tip.

## 2. Mode

Before §4 overwrites `meta.json`, read its old `head`, `base` and `updated_at`, and
`$WORK/review.done` (the head of the last finished review). `PREV_HEAD` = the sha in
`review.done`, `PREV_BASE` = the old `base`.

- `full`: `fresh` is yes; or `review.done` is missing or names a different head than the old
  `meta.json` (last run unfinished; this run overwrites its files); or `review.md` or
  `notes.md` is missing.
- `same-head`: `PREV_HEAD` = `$HEAD`.
- `incremental`: the head moved and the interdiff is small. Otherwise `full (<reason>)`.

Interdiff, written to `$WORK/interdiff.md`:

1. `PREV_HEAD` missing locally → `git -C "$REPO" fetch -q origin "$PREV_HEAD"`; still missing →
   `full (old head gone)`.
2. `PREV_HEAD` is an ancestor of `$HEAD` and `PREV_BASE` = `$BASE`: method `direct`,
   `git diff "$PREV_HEAD" "$HEAD"` plus `git log --oneline "$PREV_HEAD..$HEAD"`.
3. Otherwise (rebase, or base merged in): method `range-diff`,
   `git range-diff "$PREV_BASE..$PREV_HEAD" "$BASE..$HEAD"`; a plain diff would drag in the
   base's own changes.
4. Header: old head, new head, method, new commits, `git diff --stat` (direct) or the
   range-diff commit pairing.
5. Too big → `full (interdiff too big)`: more than half as many lines as the whole PR diff
   (`git diff --shortstat "$BASE" "$HEAD"`), or over ~1500 lines.

Archive by mode:

- `same-head`: move nothing. Copy `threads.md` to `threads.prev.md` before §6 rewrites it;
  after §6 report `threads changed: yes|no` from `diff -q`.
- `incremental`, or `full` after a finished run: move `review.md`, `notes.md`,
  `findings-*.md`, `fix-history.md` and `verify.md` into `$WORK/history/<PREV_HEAD7>/`, delete
  `review.done`.
- Any mode but `incremental`: delete a stale `interdiff.md`.

On the head-moved retry (§6) keep the mode, `PREV_HEAD` and `PREV_BASE` from the first pass
and do not archive again; only redo the interdiff (`incremental` may become `full (interdiff
too big)`). Exception: `same-head` archived nothing and is no longer the same head, so pick
the mode afresh.

**Prior reviews**, for the `prior:` line: GitHub reviews by `$ME`
(`jq --arg me "$ME" '[.reviews[] | select(.author.login == $me and .state != "PENDING")]' "$WORK/pr.json"`:
count, last `submittedAt`, `state`, `commit.oid`, commits since via `git rev-list --count
<oid>..$HEAD`, or `rebased since` when `<oid>` is not an ancestor), and this skill's last run
(`PREV_HEAD`, old `updated_at`, the `history/` folder or `review.md` in `same-head`). Neither →
`prior: none`.

## 3. Worktree

Detached, shared objects, nothing installed (no `yarn`, `npm`, `cargo build`, `bootstrap.sh`):

```bash
if [ -d "$WORK/wt" ] && git -C "$WORK/wt" rev-parse --git-dir >/dev/null 2>&1; then
  git -C "$WORK/wt" checkout -q --detach "$HEAD"
else
  rm -rf "$WORK/wt"; git -C "$REPO" worktree prune
  git -C "$REPO" worktree add -q --detach "$WORK/wt" "$HEAD"
fi
```

## 4. meta.json, then gc

```json
{"slug":"aztecprotocol-aztec-packages-pr-25254","repo_root":"/abs/repo","owner_repo":"AztecProtocol/aztec-packages",
 "pr":25254,"title":"…","url":"…","branch":"palla/foo","base_ref":"next","base":"<BASE sha>",
 "head":"<HEAD sha>","behind_base":12,"state":"OPEN","draft":false,"author":"…","me":"spalladino",
 "permalink_base":"https://github.com/AztecProtocol/aztec-packages/blob/<HEAD sha>/",
 "base_permalink_base":"https://github.com/AztecProtocol/aztec-packages/blob/<BASE sha>/",
 "mode":"incremental","prev_head":"<PREV_HEAD sha or null>",
 "wt":"/home/…/.cache/review-pr/aztecprotocol-aztec-packages-pr-25254/wt","updated_at":"<ISO>"}
```

Then `bash "$SKILL_DIR/scripts/gc.sh" --keep 6 --days 7`.

## 5. dossier.md

````markdown
# Dossier: <slug>

repo: <owner/repo>   root: <abs repo root>   worktree: <$WORK/wt>
PR #<n> "<title>" — <url>
author: <login>   from fork: <yes/no>   state: <OPEN|…> <draft?>   review decision: <…>   mergeable: <…>
branch: <headRefName> → <baseRefName>   base `<BASE7>` → head `<HEAD7>`   behind base: <BEHIND> commits
permalinks: head <permalink_base>   base <base_permalink_base>   (append `<path>#L<n>`)
CI: <one line from statusCheckRollup: N passing, M failing (names), K pending>
labels: …

## Body
<PR body verbatim, minus CI checklists, templates and screenshots. Keep links and issue keys.>

## Commits (<count>)
- `abc1234` <date> <subject>
…

## Stat
```
<git diff --stat BASE..HEAD>
```
````

Then append the files section with the script, never by hand:

```bash
python3 "$SKILL_DIR/scripts/dossier_files.py" "$REPO" "$BASE" "$HEAD" <n> \
  --skip '(\.lock$|/generated/|\.min\.js$)' >> "$WORK/dossier.md"
```

Add to `--skip` only machine-generated files (`@generated` in the first lines, or
`linguist-generated` in `.gitattributes`). Never skip snapshots, gas reports or fixtures.
Spot-check one hunk against `git diff -U0`. Past ~6000 lines, keep every hunk but say so in
the summary.

## 6. threads.md

```bash
python3 "$SKILL_DIR/scripts/pr_threads.py" "$REPO" "$OWNER_REPO" <n> "$HEAD" --me "$ME" \
  --resolved-out "$WORK/threads-resolved.md" > "$WORK/threads.md"
```

If `threads.md` starts with a **WARNING** that the head moved, re-run from §1 once, keeping
the mode per §2. Where the script says an original commit could not be fetched, leave it.

## 7. linear.md

Collect issue keys from the PR body, title, branch name and commit subjects
(`[A-Z][A-Z0-9]+-\d+`, `linear.app/.../issue/<KEY>`) and `closingIssuesReferences` in
`pr.json`. For each, call the Linear MCP tool `get_issue` (and `list_comments`), or delegate
to the `linear` agent type if available. Write:

````markdown
# Linear: <slug>

## <KEY> — <title>   (<state>, assignee <name>)   <url>
<description, trimmed to intent: drop templates and checklists, keep under ~40 lines>

comments:
- <date> <author>: <comment, trimmed to ~5 lines>
````

No keys → `no linked issues found`. Linear tools unavailable → say so in the file and the
summary.

## 8. decoherence.md

Skip in `same-head` mode (no DESIGN fork runs). The script reads git objects only and writes
only into `$WORK`:

```bash
node ~/.claude/skills/decoherence/scripts/decoherence.cjs --repo "$REPO" --base "origin/$BASE_REF" \
  --range "$BASE..$HEAD" --title "<PR title>" --out "$WORK" --name decoherence --quiet
```

If it fails, write `# Decoherence: <slug>\n\nunavailable: <one-line reason>` and go on; never
retry or install anything.

## 9. fix-history.md

Older changesets for the DESIGN fork: were these functions fixed before, was the same check
added elsewhere. In `same-head` mode leave the last run's file as it is. Otherwise always
write it. Write `# Fix history: <slug>\n\nskipped: <reason>` when the PR title is not a `fix`
and `decoherence.md` shows no touched function with earlier fixes and no second way (or is
unavailable).

Otherwise, for the functions the PR modifies (in `incremental` mode, those the interdiff
touches) and the conditions or branches it adds, search the base branch's history up to 12
weeks back (`git -C "$REPO" log --first-parent "origin/$BASE_REF" -L :<fn>:<file>`,
`git log --first-parent -S'<predicate>'`, `git show`) and write:

1. Earlier fixes to the same functions: PR, date, one line on what each changed, and whether
   it was the same kind of special case as this PR (a guard, exception, reason, fallback).
2. The same predicate or check added before elsewhere: where it lives at head, which PR.
3. For each second way `decoherence.md` lists, and each new helper, type or branch next to an
   existing one: the existing path it parallels, and whether it is still live (its callers).

Facts only, no recommendations. Cite sha7, PR numbers and `path:line` at head. At most 40
lines under `# Fix history: <slug>`.

## 10. Return

Only this, as plain lines. No diff, no file contents.

```
slug: aztecprotocol-aztec-packages-pr-25254
work: /home/…/.cache/review-pr/aztecprotocol-aztec-packages-pr-25254
repo: AztecProtocol/aztec-packages   root: /abs/repo   wt: <$WORK/wt>
pr: #25254 "<title>" by <author> — <state>, <draft?>, fork: <y/n>, review decision <…>, CI <one line>
base: <BASE7>  head: <HEAD sha>  behind base: <N>
files: 14 changed (+412 −96), 2 skipped
dossier: <lines> lines, <hunks> hunks
threads: <U> unresolved (<K> with <me> taking part), <R> resolved, <F> force pushes, <T> top-level reviews/comments by <me>
linear: <KEY list or none>
decoherence: <N> touched functions with earlier fixes, <S> second ways, adds without replacing in <areas or none> | skipped (same-head) | unavailable: <reason>
fix history: <F> earlier fixes, <C> repeated checks, <P> parallel paths | skipped: <reason>
prior: none | github: <N> review(s) by <me>, last <date> <STATE> at <sha7>, <K> commits since (or rebased since); review-pr: <date> at head <old7>, history/<old7>/review.md
mode: full | full (<fallback reason>) | same-head, threads changed: yes|no | incremental from <old7>, <direct|range-diff>, <N> new commits, <files> files +A −D
gc: <the gc.sh summary line>
notes: <anything odd: huge diff, head moved during gathering, unfetchable original commits, PR already merged>
```
