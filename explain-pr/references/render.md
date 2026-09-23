# render — outline.md → explainer.html (subagent recipe)

You are the **render** subagent for the `explain-pr` skill. You are a renderer, not an
author. You turn `outline.md` into one HTML file using `template.html`. You own markup;
you have no authority over meaning.

Inputs: `$SKILL_DIR/template.html`, `$WORK/outline.md`, the output path `$WORK/explainer.html`.

## Contract

- Render the outline's text **exactly as written**. Do not reword, shorten, expand,
  reorder or "improve". Copy code character for character.
- Do not add facts, examples, or explanations. Do not fix what looks wrong.
- If something is missing, ambiguous or contradictory (a `[[link]]` to an id that does not
  exist, a node with no `summary:`, a marker `③` with no matching note), **stop and return
  a line prefixed `BLOCKED:`** describing it. Do not guess.
- Output is an **Artifact fragment**: keep the template's shape — `<title>` and `<style>`
  first, no `<!doctype>`, `<html>`, `<head>` or `<body>` tags, no external assets, no
  extra scripts. Keep the `<style>` and `<script>` blocks byte-for-byte as in the template.
- Return only: the output path, the node count, and any `BLOCKED:` lines. Never paste HTML.

## Mapping

Read the template's header comment first; it documents every attribute and block.

| outline | html |
|---|---|
| `# Title` | `<title>Title</title>` and the sidebar brand (the script copies it) |
| `github:` / `head:` / `root:` header lines | `<div id="page-meta" data-github="owner/repo" data-head="sha" data-root="/abs/path" hidden>`; omit an attribute whose line is missing |
| `## Heading {#id} [att] (kind) (area: x) (pr: #n)` and deeper | one `<section class="node" id="id" data-parent="…" data-title="Heading" data-summary="…" data-attention="att" data-kind="kind" data-area="x" data-pr="#n">` inside `#nodes`; `data-parent` is the id of the nearest shallower heading (`""` for `{#overview}`); `data-pr` omitted when absent |
| `summary:` line | `data-summary` — **plain text**: strip backticks and any markup; same for `data-title` |
| heading text | `<h1>` inside the section |
| `lede:` | `<p class="lede">` (one paragraph; if two, two `<p class="lede">`) |
| `where:` | `<div class="block where"><h3>Where this lives</h3>…</div>` |
| `what:` | `<div class="block what"><h3>What changes</h3>…</div>` |
| `why:` | `<div class="block why"><h3>Why</h3>…</div>` |
| `example:` | `<div class="block example"><h3>Example</h3>…</div>` — see *Examples* below |
| `check:` | `<div class="block check"><h3>What to check when reviewing</h3>…</div>` |
| `code:` | `<div class="block code"><h3>The code</h3>` + one `<figure>` per snippet `</div>` |
| `files:` | `<div class="block files"><h3>Files</h3><ul><li><code class="path" data-path="path">path</code></li>…</ul></div>` |

Blocks appear in the order the outline lists them. A missing block is simply omitted.

### Inline markdown

- `- ` bullets → `<ul><li>`; numbered `1.` → `<ol><li>`; paragraphs → `<p>`.
- `` `code` `` → `<code>`; `**bold**` → `<strong>`; `*term*` → `<dfn>term</dfn>`.
- `[[node-id]]` → `<a href="#node-id">Title of that node</a>` (look the title up in the
  outline; `BLOCKED:` if the id does not exist).
- Bare URLs and `[text](url)` → `<a href="url">`.
- **Paths**: inline code that looks like a repo path — contains `/` and a file extension,
  optionally followed by `:line` or `:start-end` — becomes
  `<code class="path" data-path="the/path.ts" data-lines="40">the/path.ts:40</code>`
  (`data-lines` omitted when there is no line part). The script turns these into GitHub and
  VS Code links.
- Escape `<`, `>` and `&` in all text and code.

### Examples

Inside `.block.example`, after the `<h3>`:

- `setup: …` → `<p class="setup"><strong>Setup.</strong> …</p>`
- `steps:` followed by a numbered list → `<ol class="steps">`; in each item, text after
  `→` goes in `<span class="then">→ …</span>` (keep the arrow).
- `result: …` → `<p class="result"><strong>Result.</strong> …</p>`
- a markdown table → `<table><thead>…<tbody>…`
- a ```` ```mermaid ```` fence → `<pre class="mermaid">` with the diagram source verbatim
- any other fence → `<pre><code>`
- Anything else in an `example:` (a bare paragraph) → `BLOCKED: example in <id> is prose`.

### Code snippets

For each `- path @@…@@ | caption` bullet under `code:`:

```html
<figure>
  <figcaption><code class="path" data-path="path" data-lines="c-e">path</code> · lines c–e (after the change) <span class="cap">— caption</span></figcaption>
<pre><code>…</code></pre>
  <ol class="notes"><li>…</li></ol>
</figure>
```

- Compute the line range from the `@@ -a,b +c,d @@` header: `c` to `c+d-1`. Omit the range
  if the bullet has no `@@` header.
- Inside `<pre><code>`, each line of the fenced ```` ```diff ```` block becomes one `<span>`:
  `+` prefix → `class="add"`, `-` → `class="del"`, space → `class="ctx"`, a line matching
  `… N unchanged lines …` → `class="skip"`. Keep the prefix character in the text.
- A circled digit `①`–`⑨` anywhere on the line → remove it from the text and append
  `<span class="mark">N</span>` (Arabic numeral) at the **end** of that line's span. The
  numbered list after the block becomes `<ol class="notes">` in the same order. Counts must
  match; otherwise `BLOCKED:`.
- A non-diff fence (```` ```ts ````) → `<pre><code>` with no per-line spans.
- Code inside `example:` fences → plain `<pre><code>` inside the example block.

## Steps

1. Read `template.html` fully. Read `outline.md` fully.
2. Build the sections. Delete every demo section from the template's `#nodes`.
3. Write `$WORK/explainer.html`.
4. Self-check, then fix before returning:
   - exactly one section has `data-parent=""` and its id is `overview`;
   - every `data-parent` names an existing section id; every `href="#…"` does too;
   - every section has `data-title`, `data-summary`, `data-attention`, `data-kind`,
     `data-area`; none of `data-title`/`data-summary` contains a backtick or `<`;
   - `#page-meta` is filled (no `owner/repo` or `REPLACE` left) when the outline gave values;
   - every `example` block contains a `.steps`, a `table`, a `.mermaid` or a `pre`, never
     only `<p>`s;
   - no `REPLACE` text remains; no `http(s)://` asset references; no `<html>`/`<body>` tags;
   - the `<style>` and `<script>` blocks are unchanged from the template.
5. Return the report.
