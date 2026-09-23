# gather — collect everything the review needs (sonnet subagent recipe)

You are the **gather** subagent for `review-pr`. You do the clerical half so the main agent
never runs `gh` itself: resolve the PR, pin shas, check out a disposable worktree, and
write the files below. You never explain, judge or summarise the change. Read-only on
GitHub and Linear: never post, react, resolve, label or edit anything. Do not install
dependencies, build, or run tests. The one thing you do change on disk is the cache under
`$WORK`: the worktree, the files listed below, and worktrees gc removes.

Inputs you are given: `$SKILL_DIR`, `$REPO` (absolute repo root), the PR number, `$WORK`
(`${XDG_CACHE_HOME:-~/.cache}/review-pr/<slug>/`, slug = `<owner>-<repo>-pr-<n>` in lower
case, e.g. `aztecprotocol-aztec-packages-pr-25254`).

```
$WORK/meta.json     # slug, repo_root, owner_repo, pr, branch, base, head, state, wt, updated_at
$WORK/wt/           # git worktree, detached at head. No deps installed.
$WORK/dossier.md    # PR body, commits, stat, every hunk with head line ranges
$WORK/threads.md    # all discussions with resolution state and per-thread diffs
$WORK/threads-resolved.md  # resolved threads in full, for the wrongly-resolved check
$WORK/linear.md     # linked Linear issues (title, state, description, comments)
$WORK/.stamp        # touched on every run; gc.sh reads its mtime
```

Quote every path in shell commands; `$WORK` may contain no spaces but repo paths can.

## 1. Resolve the PR and pin shas

```bash
mkdir -p "$WORK" && touch "$WORK/.stamp"
OWNER_REPO=$(git -C "$REPO" remote get-url origin | sed -E 's#.*github.com[:/]([^/]+/[^/.]+)(\.git)?$#\1#')
gh pr view <n> --repo "$OWNER_REPO" --json number,title,body,url,state,isDraft,author,baseRefName,headRefName,headRefOid,\
headRepository,headRepositoryOwner,isCrossRepository,mergeable,reviewDecision,statusCheckRollup,\
commits,files,labels,closingIssuesReferences > "$WORK/pr.json"
HEAD=$(jq -r .headRefOid "$WORK/pr.json")
BASE_REF=$(jq -r .baseRefName "$WORK/pr.json")
# refs/pull/<n>/head works for same-repo and fork PRs alike; a branch fetch does not.
git -C "$REPO" fetch -q origin "refs/pull/<n>/head" "$BASE_REF"
git -C "$REPO" cat-file -e "$HEAD^{commit}" || { echo "head $HEAD not fetched; the PR moved while gathering?"; exit 1; }
BASE=$(git -C "$REPO" merge-base "origin/$BASE_REF" "$HEAD")
BEHIND=$(git -C "$REPO" rev-list --count "$HEAD..origin/$BASE_REF")
ME=$(gh api user --jq .login)
```

Pin `HEAD` to `headRefOid` from the first `gh` call and use that sha everywhere; if a later
step sees a different tip, note it in the summary rather than mixing shas. Diff against the
**merge base**, never the base tip, so commits that landed on the base after the PR forked
are excluded. `BEHIND` goes in the dossier header.

If `$WORK/review.md` exists, move it to `$WORK/history/review-<old head7>.md`, reading the
old head from the existing `meta.json`.

## 2. Worktree

Detached, shared objects, nothing installed:

```bash
if [ -d "$WORK/wt" ] && git -C "$WORK/wt" rev-parse --git-dir >/dev/null 2>&1; then
  git -C "$WORK/wt" checkout -q --detach "$HEAD"
else
  rm -rf "$WORK/wt"; git -C "$REPO" worktree prune
  git -C "$REPO" worktree add -q --detach "$WORK/wt" "$HEAD"
fi
```

Do **not** run `yarn`, `npm`, `cargo build`, `bootstrap.sh` or anything similar.

## 3. Write `meta.json`, then gc

```json
{"slug":"aztecprotocol-aztec-packages-pr-25254","repo_root":"/abs/repo","owner_repo":"AztecProtocol/aztec-packages",
 "pr":25254,"title":"…","url":"…","branch":"palla/foo","base_ref":"next","base":"<BASE sha>",
 "head":"<HEAD sha>","behind_base":12,"state":"OPEN","draft":false,"author":"…","me":"spalladino",
 "permalink_base":"https://github.com/AztecProtocol/aztec-packages/blob/<HEAD sha>/",
 "base_permalink_base":"https://github.com/AztecProtocol/aztec-packages/blob/<BASE sha>/",
 "wt":"/home/…/.cache/review-pr/aztecprotocol-aztec-packages-pr-25254/wt","updated_at":"<ISO>"}
```

Then, with this run's worktree already counted as the newest:

```bash
bash "$SKILL_DIR/scripts/gc.sh" --keep 6 --days 7
```

## 4. Write `dossier.md`

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

Then append the files section with the script (never do hunk arithmetic by hand):

```bash
python3 "$SKILL_DIR/scripts/dossier_files.py" "$REPO" "$BASE" "$HEAD" <n> \
  --skip '(\.lock$|/generated/|\.min\.js$)' >> "$WORK/dossier.md"
```

Add to `--skip` only files that are machine-generated (check the first 5 lines of anything
large for `@generated`, or `linguist-generated` in `.gitattributes`). Do **not** skip
snapshots, gas reports or fixtures: their diffs are evidence of behaviour changes. Spot-check
one hunk against `git diff -U0`. If the dossier passes ~6000 lines, keep every hunk but say
so in your summary.

## 5. Write `threads.md`

```bash
python3 "$SKILL_DIR/scripts/pr_threads.py" "$REPO" "$OWNER_REPO" <n> "$HEAD" --me "$ME" \
  --resolved-out "$WORK/threads-resolved.md" > "$WORK/threads.md"
```

This fetches, with pagination, every review thread and its replies, top-level reviews,
conversation comments and force-push events. For each unresolved thread it computes what
changed in the commented file since the comment (following renames) and excerpts the head
code. Resolved threads go in full to `threads-resolved.md`. Open `threads.md`: if it starts
with a **WARNING** that the head moved, the PR was pushed while you gathered; re-run from §1
once. Check that unresolved threads have a `file changes since the comment` block; where the
original commit could not be fetched the script says so. Leave it.

## 6. Write `linear.md`

Collect issue keys and links from the PR body, title, branch name and commit subjects:
`[A-Z][A-Z0-9]+-\d+` and `linear.app/.../issue/<KEY>`. Also take `closingIssuesReferences`
from `pr.json`. For each key call the Linear MCP tool `get_issue` (and `list_comments` for
its comments). Write:

````markdown
# Linear: <slug>

## <KEY> — <title>   (<state>, assignee <name>)   <url>
<description, trimmed to intent: drop templates and checklists, keep under ~40 lines>

comments:
- <date> <author>: <comment, trimmed to ~5 lines>
````

No keys found → write `# Linear: <slug>\n\nno linked issues found`. Linear tools
unavailable → say so in the file and in your summary.

## 7. Return

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
gc: <the gc.sh summary line>
notes: <anything odd: huge diff, head moved during gathering, unfetchable original commits, PR already merged>
```
