# gather — snapshot the working copy and collect what the reviewers read (sonnet subagent recipe)

You are the **gather** subagent of `self-review`: freeze the working copy into a snapshot
commit, decide the mode, write the files below. Never explain, judge or summarise the change.
Never modify the working copy, the index, refs or the stash; read-only on GitHub and Linear;
no installs, builds or tests.

Inputs: `$REPO` (absolute repo root), `$OWNER_REPO`, the branch, `$BASE_REF`, `$BASE` (the
merge-base sha), the PR number or none, `$REVIEW_PR_DIR`, the Linear key or none, `fresh`.

```
$WORK/meta.json        # repo_root, owner_repo, branch, base_ref, base, head, snap, prev_snap, mode, issue, pr, updated_at
$WORK/dossier.md       # commits, untracked files, stat, every hunk with line ranges at the snapshot
$WORK/linear.md        # the linked issue
$WORK/decoherence.md, decoherence.json   # flow signals and area fix history
$WORK/fix-history.md   # older fixes and checks around the touched functions
$WORK/interdiff.md     # incremental mode only
$WORK/history/<snap7>/ # an earlier run's report.md, findings-*.md, verify.md, fix-history.md, prompt-*.md
```

Written by others, read by you: `report.md`, `report.done` (the snapshot of the last finished
review), `decisions.md` (never move or edit it). Quote every path in shell commands.

## 1. Work dir

```bash
SLUG=$(echo "$OWNER_REPO" | tr '/' '-' | tr '[:upper:]' '[:lower:]')
KEY=<branch, lower case, every "/" replaced by "--">
# detached HEAD: KEY=detached-$(printf '%s' "$REPO" | sha1sum | cut -c1-8)-<BASE7>
WORK="${XDG_CACHE_HOME:-$HOME/.cache}/self-review/$SLUG/$KEY"
mkdir -p "$WORK"
```

## 2. Snapshot

One commit object holding the whole working copy (commits, staged and unstaged edits,
untracked files that are not ignored), built through a throwaway index so the real index,
working tree and refs stay untouched:

```bash
TMP_INDEX=$(mktemp)
cp "$(git -C "$REPO" rev-parse --path-format=absolute --git-path index)" "$TMP_INDEX"
GIT_INDEX_FILE="$TMP_INDEX" git -C "$REPO" add -A
TREE=$(GIT_INDEX_FILE="$TMP_INDEX" git -C "$REPO" write-tree)
rm -f "$TMP_INDEX"
HEAD=$(git -C "$REPO" rev-parse HEAD)
if [ "$TREE" = "$(git -C "$REPO" rev-parse 'HEAD^{tree}')" ]; then SNAP=$HEAD
else SNAP=$(git -C "$REPO" commit-tree "$TREE" -p "$HEAD" -m "self-review snapshot"); fi
COMMITS=$(git -C "$REPO" rev-list --count "$BASE..$HEAD")
```

`$SNAP` is the head everywhere below. Untracked files adding more than ~2000 lines, or any
single file over 1 MB, are probably forgotten build output: list them under `notes:` and keep
going.

## 3. Mode

Decide it once. Read the old `meta.json` (if any) for `base` (`OLD_BASE`), and `report.done`
for the snapshot of the last finished review (`PREV`).

- `full`: `fresh` is yes; or `report.done` or `report.md` is missing; or `PREV` is gone
  (`git cat-file -e`), reason `old snapshot gone`.
- `unchanged`: `PREV`'s tree equals `$TREE` (compare trees, never commit shas: every snapshot
  is a new commit) and `OLD_BASE` equals `$BASE`.
- `incremental`: the interdiff is small. Otherwise `full (interdiff too big)`.

Interdiff, written to `$WORK/interdiff.md` under a header naming both snapshots and the method:

1. `OLD_BASE` = `$BASE`: method `direct`, `git -C "$REPO" diff "$PREV" "$SNAP"` with its `--stat`.
2. Otherwise (rebased): method `range-diff`,
   `git -C "$REPO" range-diff "$OLD_BASE..$PREV" "$BASE..$SNAP"`; a plain diff would drag in
   the base's own changes.
3. Too big: more than half as many lines as the whole change
   (`git diff --shortstat "$BASE" "$SNAP"`), or over ~1500 lines.

Archive: `unchanged` moves nothing; skip to §9. `incremental`, or `full` after a finished run,
moves `report.md`, `findings-*.md`, `verify.md`, `fix-history.md` and `prompt-*.md` into
`$WORK/history/<PREV7>/` and deletes `report.done`. Any mode but `incremental` deletes a stale
`interdiff.md`.

## 4. meta.json

```json
{"repo_root":"/abs/repo","owner_repo":"aztec-labs-eng/aztec-node","branch":"spl/foo","base_ref":"next",
 "base":"<BASE>","head":"<HEAD>","snap":"<SNAP>","prev_snap":"<PREV or null>","mode":"full",
 "issue":"A-123","pr":null,"updated_at":"<ISO>"}
```

## 5. dossier.md

````markdown
# Dossier: <owner/repo> <branch>

repo: <owner/repo>   root: <abs repo root>
branch: <branch> → <base_ref>   merge-base `<BASE7>`   HEAD `<HEAD7>`   snapshot `<SNAP7>`
uncommitted edits: <yes|no>   untracked files: <count>   PR: <#n or none>

## Commits (<COMMITS>)
- `abc1234` <date> <subject>
…
<"plus uncommitted edits" when SNAP ≠ HEAD>

## Untracked files
<one per line, or "none">

## Stat
```
<git diff --stat BASE SNAP>
```
````

Then append the files section with review-pr's script, never by hand (the fourth argument
only labels the heading):

```bash
python3 "$REVIEW_PR_DIR/scripts/dossier_files.py" "$REPO" "$BASE" "$SNAP" "<SNAP7>" \
  --skip '(\.lock$|/generated/|\.min\.js$)' >> "$WORK/dossier.md"
```

Add to `--skip` only machine-generated files (`@generated` in the first lines, or
`linguist-generated` in `.gitattributes`). Never skip snapshots, gas reports or fixtures.

## 6. linear.md

Collect issue keys from the given key, the branch name and the commit subjects
(`[A-Z][A-Z0-9]+-\d+`). For each, call the Linear MCP tool `get_issue` (and `list_comments`),
or delegate to the `linear` agent type if available. Write:

````markdown
# Linear: <owner/repo> <branch>

## <KEY> — <title>   (<state>, assignee <name>)   <url>
<description, trimmed to intent: drop templates and checklists, keep under ~40 lines>

comments:
- <date> <author>: <comment, trimmed to ~5 lines>
````

No keys → `no linked issues found`. Linear tools unavailable → say so in the file and the
summary.

## 7. decoherence.md

```bash
node ~/.claude/skills/decoherence/scripts/decoherence.cjs --repo "$REPO" --base "origin/$BASE_REF" \
  --range "$BASE..$SNAP" --title "<oldest commit subject, or the branch name>" \
  --out "$WORK" --name decoherence --quiet
```

If it fails, write `# Decoherence\n\nunavailable: <one-line reason>` and go on; never retry or
install anything.

## 8. fix-history.md

Older changesets for the DESIGN reviewer. Always write the file. Write
`# Fix history\n\nskipped: <reason>` when the change is not a fix (neither the branch name nor
any commit subject contains `fix`) and `decoherence.md` shows no touched function with earlier
fixes and no second way, or in `incremental` mode when the interdiff touches no function.

Otherwise, for the functions the change modifies (in `incremental` mode, those the interdiff
touches) and the conditions or branches it adds, search the base branch's history up to 12
weeks back (`git -C "$REPO" log --first-parent "origin/$BASE_REF" -L :<fn>:<file>`,
`git log --first-parent -S'<predicate>'`, `git show`) and write:

1. Earlier fixes to the same functions: PR, date, one line on what each changed, and whether
   it was the same kind of special case as this change (a guard, exception, reason, fallback).
2. The same predicate or check added before elsewhere: where it lives at the snapshot, which
   PR added it.
3. For each second way `decoherence.md` lists, and each new helper, type or branch next to an
   existing one: the existing path it parallels, and whether it is still live (its callers).

Facts only, no recommendations. Cite sha7, PR numbers and `path:line` at the snapshot. At
most 40 lines under `# Fix history`.

## 9. Return

Only this, as plain lines. No diff, no file contents.

```
work: <$WORK>
snap: <SNAP sha>   head: <HEAD7>   base: <BASE sha>   commits: <COMMITS>
mode: full | full (<reason>) | incremental from <PREV7>, <direct|range-diff>, <files> files +A −D | unchanged
prev: <PREV sha or none>
files: <N> changed (+A −D), <S> skipped; uncommitted edits <yes|no>; untracked <U>
dossier: <lines> lines, <hunks> hunks
linear: <KEY list or none>
decoherence: <N> touched functions with earlier fixes, <S> second ways | unavailable: <reason>
fix history: <F> earlier fixes, <C> repeated checks, <P> parallel paths | skipped: <reason>
decisions: <count of lines in decisions.md, or none>
notes: <anything odd: suspicious untracked files, huge diff, base far behind>
```
