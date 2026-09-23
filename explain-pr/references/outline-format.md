# `outline.md` — the format the main agent writes

`outline.md` is the main agent's only output. The **render** subagent turns it into the
HTML page mechanically and adds no meaning, so anything left out is lost. Write final
prose here; there is no later editing pass.

Read `style.md` before writing a single bullet.

---

## Header

```markdown
# Make getLogsByTags fast and correct under concurrent callers
slug: pr-25254-25282
github: aztecprotocol/aztec-packages
head: 38e30f9c1d2e
root: /home/santiago/Projects/aztec-packages
```

`#` = the page title, a short noun phrase (also the artifact title). `slug:` = the work dir
name. `github:`, `head:` and `root:` come from the gather summary and let the page turn
every file path into a GitHub link (at the head sha) and a VS Code link (absolute path).

## Nodes

One markdown heading per node. Heading depth is the hierarchy: `##` is a child of the
overview, `###` a grandchild, and so on down to `######`. Depth is free; width is not
(≤ 7 siblings, see style.md).

```markdown
## Overlay reads {#overlay-reads} [high] (design) (area: node) (pr: #25282)
summary: A read inside a write transaction must now see that transaction's own writes.
```

- `{#id}` — required, kebab-case, unique. The overview node is always `{#overview}` and
  is the single `##` at the top; everything else nests under it.
- `[attention]` — `high` (review carefully: a correctness or design argument lives here),
  `medium` (behaviour change, worth a look), `low` (mechanical, skim). Judged by review
  attention needed, never by diff size.
- `(kind)` — `overview`, `design` (a sub-problem or the modularisation), `module` (one
  module and what happens to it), `code` (a concrete piece of implementation), `tests`,
  `wiring` (mechanical propagation).
- `(area: x)` — required. Which part of the system the node touches, shown as a chip in the
  sidebar so the reader sees at a glance where each node lives. Values: `node` (TypeScript
  node, `yarn-project/`), `l1` (Solidity, `l1-contracts/`), `circuits` (Noir,
  `noir-projects/`), `bb` (`barretenberg/`), `docs`, `infra`, `mixed` (overview or a node
  spanning several). Combine with `+` when a node genuinely spans two: `node+l1`.
- `(pr: #n)` — optional, for stacks: which PR this node belongs to.
- `summary:` — required. **One** plain sentence, **plain text** (no backticks, no
  markup). Shown in the parent's "zoom in" menu, so the reader decides from it whether to
  descend.
- Heading text is also plain text: no backticks. Write `getMany reads the overlay first`,
  not `` `getMany` reads… `` — the sidebar cannot render markup.

## Blocks

Under the heading, in this order, each introduced by a label line. Use the ones that apply.
Content is markdown: paragraphs, `- ` bullets, `` `code` ``, `[[node-id]]` links (rendered as
links to that node), `*term*` for a term you are defining on first use.

```markdown
lede:
Two or three plain sentences. What this node is about and why it exists relative to its
parent.

where:
- What the touched module does, who calls it, which workflows go through it — BEFORE the
  change. Background, verified, cited (`path:line`).
- Define words the reader will meet.

what:
- The change, in bullets. One idea per bullet.

why:
- The problem it solves, or the reason for this design over the obvious alternative.

example:
setup: Cap is 1024. Four buckets of 256 arrive, then single messages.
steps:
1. Bucket 4 arrives, total becomes 1024. → fits, it is kept.
2. Bucket 5 arrives, total would be 1025. → rejected, over the cap.
3. Bucket 4 is evicted later. → every kept bucket still has total ≥ 1025.
result: The chain can never consume again; the cap must be checked against the *parent*
total, not the running one.

check:
- Concrete questions the reviewer should answer while reading this node's code.
- Link to the node where the code is, if that is a child: see [[getmany-txid]].

code:
- yarn-project/kv-store/src/lmdb-v2/read_transaction.ts @@ -20,6 +24,15 @@ | getMany with overlay
  ```diff
    async getMany(keys) {
  +   const fromOverlay = this.overlay.getMany(keys); ①
  +   const missing = keys.filter((k, i) => fromOverlay[i] === undefined); ②
      … 6 unchanged lines …
  -   return this.snapshot.getMany(keys);
  +   return merge(fromOverlay, await this.snapshot.getMany(missing));
    }
  ```
  1. Ask the overlay first, so a write earlier in this transaction is visible.
  2. Only the keys the overlay did not have go to the disk snapshot.

files:
- yarn-project/kv-store/src/lmdb-v2/read_transaction.ts
- yarn-project/kv-store/src/lmdb-v2/write_transaction.ts
```

### `example:` details

An example is **never a paragraph**. Pick one of these shapes:

- **Setup / steps / result** (default): `setup:` one line of starting state with tiny
  numbers; `steps:` a numbered list, each step `what happens. → what the system does`;
  `result:` one line saying what is different from before.
- **Before / after table**: a markdown table with columns `| case | before | after |`.
- **Diagram**: a ```` ```mermaid ```` fence (sequence or flow), ≤ 8 nodes, when the point is
  an ordering or a data flow. Always pair it with a one-line `result:`.
- **Code**: a ```` ```ts ```` (or other language) fence of ≤ 6 lines with a comment per line,
  when the example *is* a call.

Names come from the code (`bucket 4`, `slot S+1`, `block 41`), numbers stay tiny, and
each step is one short sentence.

### `code:` details

- One `- path @@hunk@@ | caption` bullet per snippet. Copy the `@@` header from the dossier
  so the head line range is known; the caption becomes the figure title.
- The fenced ```` ```diff ```` block is the **trimmed** hunk: keep the lines the argument
  depends on, replace runs of unchanged lines with `… N unchanged lines …`. Aim for ≤ 25
  lines. Prefixes `+`, `-`, space (context) are kept.
- Circled digits `①②③…` placed at the **end** of a line become numbered markers (rendered at
  the line's right edge, with the note shown on hover); the numbered list after the block
  explains each one. ≤ 6 markers per snippet.
- A snippet with no diff prefixes (plain code at head) is also fine: use ```` ```ts ````
  or the right language, and the caption says `(after the change)`.

### Paths

Any file path in prose — in `where:` citations like `` `archiver/src/log_store.ts:40` ``, in
`files:`, in captions — is rendered as a link to GitHub at the head sha and to VS Code.
Write them as inline code, repo-root-relative, with an optional `:line` or `:start-end`.

### Which blocks where

| node kind | usually has |
|---|---|
| overview | lede, where (the area of the system + glossary), what (one bullet per child, linked), why, example, check (the 2–3 things that matter most, linked) |
| design | lede, where, what, why, example, check |
| module | lede, where, what, check, files |
| code | lede, code (1–3 snippets), check, files |
| tests | lede, what (what is covered, what is not), files |
| wiring | lede, what ("the 11 call sites are identical except…"), files |

A node with children does not need `code:`; its job is to be a menu. A leaf usually does.

## Stacks

For a PR stack, the overview's `what:` lists the PRs in order with one line each. Below it,
organise by **sub-problem**, not by PR — a PR may span several and several PRs may attack
one — and mark each node with `(pr: #n)`. Where the stack order matters ("#2 only makes
sense after #1 added X"), say so in the overview's `why:`.
