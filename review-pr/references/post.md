# post — turn chosen findings into PR comments (sonnet drafter recipe + posting rules)

Only when the user names what to post. The one write this skill does, always as one GitHub
review, never loose comments.

## Main agent

1. **Take the order literally.** The user names findings (`B2`, `D1`), thread rows (`T3`) or
   free-form points, and the action: `comment`, `approve`, `request changes` or `pending`
   (left open for them to submit from the web). Action missing → ask. Nothing else gets posted.
2. **Write `$WORK/post-plan.md`**, one block per item:
   ```
   ## <id or short name>
   target: thread `<thread id from threads.md>`   |   new: `<path>` line <n> [start <m>] side RIGHT
   point: <two to five bullets in your words: the claim, the evidence (path:line), the ask>
   tone: <answer to a question | pushback on a reply | new finding | nit>
   ```
   A `new:` target must be a head line inside a diff hunk (the dossier's head ranges) or
   GitHub rejects it; anything else goes in a thread reply or the body. For a thread reply,
   quote the last comment so the drafter answers it. Review body: one or two sentences if the
   user wants one, else `none`; it states what you checked and never thanks the author.
3. **Dispatch the drafter** below, `Agent(subagent_type: "general-purpose", model: "sonnet")`.
4. **Read `$WORK/post.json` yourself.** Fix anything that overstates the evidence, softens the
   ask, or drifts from the plan.
5. **Dry-run, then confirm:**
   ```bash
   python3 "$SKILL_DIR/scripts/post_review.py" <owner/repo> <n> <head> "$WORK/post.json" \
     --me <me> --event <EVENT> --dry-run
   ```
   Show the output verbatim and wait for a go, unless they already said to post without
   showing. Then run without `--dry-run`; the script refuses to post if the PR moved.
6. **Report** the review URL, the event, and, for `pending`, that they submit or discard it
   from the Files tab.

The script signs every comment and a non-empty body `_Written by Claude_`; never add or
remove it yourself. When the user wrote the body themselves, pass `--unsigned-body`.

## Drafter prompt

```
You are the drafter for review-pr. Read <$WORK>/post-plan.md; for each block also read the
finding it refers to in <$WORK>/review.md and, for thread replies, the thread in
<$WORK>/threads.md. Write <$WORK>/post.json in the shape post_review.py documents:
{"body": "<review body or empty>", "comments": [{"thread_id": …, "body": …} |
{"path": …, "line": …, "start_line"?: …, "side": "RIGHT", "body": …}]}. Copy targets from the
plan exactly.

Each body:
- Address the author directly, as a colleague. One point per comment, in the order: what you
  see, why it matters, what you suggest. Two to six sentences.
- Plain words, active verbs, no hedging, no praise padding. Never thank the author; from a
  reviewer it reads as condescending.
- Evidence inline: quote the one or two lines that matter in a fenced block with the
  language tag, or cite `path:line`. No permalinks; GitHub anchors the comment already.
- A thread reply answers the last message in the thread; do not restate the original ask.
- A nit starts with "nit:". A TRADEOFF proposal states the loss in one sentence.
- Do not mention the review process, the ids, other findings, or that a model wrote this;
  the signature is added for you.
Read-only apart from writing post.json: do not post anything, touch the worktree, or run
commands other than reading files. Return ONLY the number of comments written.
```
