# Writing style for the explainer

The page is read by one person who has **little or no context** on the code, wants to
review it well, and reads top-down, zooming in only where needed. Every sentence either
helps them understand or it is noise.

---

## 1. Assume no context. Explain the place before the change.

The reader may never have opened the module. Every node that touches code has a `where:`
block that says what that code is for and who uses it, *before* saying what changed. A
change to `ReadTransaction.getMany` means nothing until the reader knows what a read
transaction is and who calls `getMany`.

- Good: `- `ReadTransaction` is the only way to read from the store. Block sync and the tx pool both go through it.`
- Bad: `- Updates `getMany` to consult the overlay.` (what overlay? what is getMany? who cares?)

## 2. Simple language. Short sentences. Define terms on first use.

Write like you are explaining to a strong engineer from another team. Prefer the everyday
word. When a domain term is unavoidable, define it inline the first time with `*term*`:
`a *snapshot* is a frozen view of the database at one moment`. Define it once, on the
highest node where it appears; children may use it freely.

- Good: `The overlay holds the writes of the current transaction that are not saved yet.`
- Bad: `The overlay is the MVCC write-set materialised pre-commit.`

## 3. No walls of text. Bullets for facts, one short paragraph for the lede.

The `lede:` is two or three sentences. Everything else is bullets, one idea each, ≤ 2
lines. If a bullet needs a third line it is two bullets. Never restate the diff: the reader
can open the code; tell them what it *means*.

- Good: `- Overlay is read before the snapshot, so a write earlier in the same transaction is visible.`
- Bad: a 9-line paragraph walking through the diff line by line.

## 4. Every node stands alone.

The reader may land on a node from a link or the pager. Its `lede:` must say what the node
is and why it exists relative to its parent, without requiring the parent to have been read.
The first `where:` bullet gives the minimal background even if the parent had more.

## 5. One simple example beats three paragraphs.

Where a mechanism is not obvious, add `example:` with **one** concrete case: a specific
input and what happens to it, or a before/after. Tiny numbers, two keys not two hundred,
real names from the code. Skip the example when the `what:` is already obvious.

- Good: `Transaction writes key `a`, then reads keys `a` and `b`. Before: `a` came from disk (stale). After: `a` comes from the overlay, only `b` goes to disk.`
- Bad: an abstract description of "the general case of N keys with M overlaid".

## 6. `check:` is concrete and answerable.

Each bullet is a question the reviewer can answer by reading the code in this node (or a
linked child). It names the risk. It is not "make sure this is correct".

- Good: `- Is the overlay cleared on *both* commit and rollback? See [[overlay-lifecycle]].`
- Good: `- The two callers in `log_store.ts` still catch `KeyNotFound`; do they need updating now that missing keys return `undefined`?`
- Bad: `- Check the logic is right.`

## 7. Depth is free, width is not: ≤ 7 siblings under any node.

The reader can hold a menu of 7. Over that, add a level and group. A large change is
goal → sub-problem → mechanism → building block → the code; each level a menu the reader
can skim to decide where to zoom in. A small PR may be 4 nodes and that is fine.

- Bad: 40 leaves, one per file. That is `git diff --stat` with extra words.
- Bad: a node whose `what:` describes one child's details. Move it to the child.

## 8. The `summary:` line is the child's whole point, in one plain sentence.

It is what the reader sees in the parent's "zoom in" menu. From it alone they decide whether
to descend. No file names, no "this node covers".

- Good: `summary: The rule that keeps stale writes from leaking into the next transaction.`
- Bad: `summary: Changes to write_transaction.ts.`

## 9. Attention reflects review effort, not diff size.

A 900-line rename is `low`. A 3-line change to lock ordering is `high`. Roughly a third or
less of the nodes should be `high`; if everything is high, nothing is.

## 10. Code snippets are trimmed to the argument.

≤ 25 lines. Keep the lines the explanation depends on, collapse the rest into
`… N unchanged lines …`. Number at most 6 lines with `①②…` and explain each in one
sentence. The reader who wants the full hunk has the PR.

## 11. Verified, or marked as a question.

Every claim about a caller, a workflow, an invariant or a consequence was checked (grep,
read, or the scout's cited brief). Something you could not verify is written as a question
in `check:`, never as a fact in `where:` or `what:`.

## 12. Banned

"Note that", "It's worth mentioning", "As we can see", "Basically", "Simply", "This PR
modifies", "Refactor." (alone). Numbers without units or a baseline. Hedged verdicts.
