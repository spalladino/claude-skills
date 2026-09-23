# post — turn chosen findings into PR comments (sonnet drafter recipe + posting rules)

Runs only when the user names what to post. Posting is the one write this skill does, and
it is always one GitHub review, never loose comments.

## Main agent

1. **Take the order literally.** The user names findings (`B2`, `D1`), thread rows (`T3`) or
   free-form points, and the review action: `comment`, `approve`, `request changes`, or
   `pending` (left open for them to submit from the web). If the action is missing, ask;
   do not guess. Nothing else from the review gets posted.
2. **Write `$WORK/post-plan.md`**, one block per item:
   ```
   ## <id or short name>
   target: thread `<thread id from threads.md>`   |   new: `<path>` line <n> [start <m>] side RIGHT
   point: <two to five bullets in your words: the claim, the evidence (path:line), the ask>
   tone: <answer to a question | pushback on a reply | new finding | nit>
   ```
   For a thread reply, quote the last comment in the thread so the drafter answers it.
   Review body: one or two sentences if the user wants one, else `none`.
3. **Dispatch the drafter** (below), `Agent(subagent_type: "general-purpose", model: "sonnet")`.
4. **Read `$WORK/post.json` yourself.** You are accountable for every sentence: fix anything
   that overstates the evidence, softens the ask, or drifts from the plan.
5. **Dry-run, then confirm:**
   ```bash
   python3 "$SKILL_DIR/scripts/post_review.py" <owner/repo> <n> <head> "$WORK/post.json" \
     --model "<your model's display name>" --me <me> --event <EVENT> --dry-run
   ```
   Show the user the dry-run output verbatim and wait for a go, unless they already said to
   post without showing. Then run it without `--dry-run`. The script pins the head sha and
   refuses to post if the PR moved.
6. **Report** the review URL, the event, and, for `pending`, that they submit or discard it
   from the Files tab.

The signature `_Written by Claude <model> at <me>'s request._` is appended by the script
to every comment and to the review body. Never add it yourself and never remove it.

## Drafter prompt

```
You are the drafter for review-pr. Read <$WORK>/post-plan.md; for each block also read the
finding it refers to in <$WORK>/review.md and, for thread replies, the thread in
<$WORK>/threads.md. Write <$WORK>/post.json in the shape post_review.py documents:
{"body": "<review body or empty>", "comments": [{"thread_id": …, "body": …} |
{"path": …, "line": …, "start_line"?: …, "side": "RIGHT", "body": …}]}. Copy targets from the
plan exactly.

How to write each body:
- Address the author directly, as a colleague. One point per comment, in the order: what you
  see, why it matters, what you suggest. Two to six sentences.
- Plain words, active verbs, no hedging ("I think maybe"), no praise padding, no "great PR".
- Evidence inline: quote the one or two lines that matter in a fenced block with the
  language tag, or cite `path:line`. No permalinks; GitHub anchors the comment already.
- A thread reply answers the last message in the thread; do not restate the original ask.
- For a nit say "nit:" first. For a TRADEOFF proposal state the loss in one sentence.
- Do not mention the review process, the ids (B2, T3), other findings, or that a model wrote
  this; the signature is added for you.
Read-only apart from writing post.json: do not post anything, touch the worktree, or run
commands other than reading files. Return ONLY the number of comments written.
```
