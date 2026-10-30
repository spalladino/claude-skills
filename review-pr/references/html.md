# html — render review.md as an artifact (sonnet subagent recipe)

Only with `--html`. The main agent owns the content; the subagent owns the markup and renders
`review.md` verbatim.

## Main agent

1. Load the `artifact-design` skill if not loaded this session.
2. Dispatch one `Agent(subagent_type: "general-purpose", model: "sonnet")` with the prompt
   below.
3. Check `$WORK/review.html`: `<title>` set, every `##` and `###` heading of `review.md`
   present, table row counts match, no external scripts.
4. `Artifact(file_path: "<$WORK>/review.html", icon: "review", description: "<one sentence:
   what the PR does>")`. Save the URL to `$WORK/artifact.url`; on a re-run pass the saved URL
   as `url` so the review keeps its link. Tell the user the URL.

## Subagent prompt

```
You are the render subagent for the review-pr skill. Turn <$WORK>/review.md into one
self-contained HTML file at <$WORK>/review.html. Every sentence, table cell, code line and
id (B1, D2, T3) appears exactly once, unchanged. You own markup and layout only. Read-only
otherwise: do not touch the worktree, install anything, or run tests.

Conversion, mechanical, never by retyping:
- Convert the markdown with a real converter: `pandoc -f gfm -t html5` if installed, else
  `python3 -c 'import markdown'` (extensions: tables, fenced_code), else a small Python
  script you write that handles headings, paragraphs, lists, tables, fenced blocks, inline
  code, bold and links, HTML-escaping all text.
- Wrap the converted body in your own page shell (below). Derive the sidebar from the
  headings present in the output (h2 for sections, h3 for finding and thread ids).

Page contract:
- <title> of two to four words, e.g. "Review #25254".
- Sticky left sidebar from the headings; main column max width 76ch; 16px side gutters and
  no horizontal page scroll at phone width (sidebar collapses to a top list under 900px).
  Tables scroll inside their own container.
- Colors as tokens on :root; redefine them under @media (prefers-color-scheme: dark)
  guarded by :root:not([data-theme="light"]), and again under :root[data-theme="dark"].
  Explicit body background. A small light/dark toggle that sets data-theme.
- Post-process with exact string rules: `blocker`, `major`, `minor` and `confidence
  high|medium|low` inside a finding heading become pills (blocker red, major amber, minor
  grey; confidence an outline pill); the status words in the discussion table
  (`addressed`, `partially addressed`, `acknowledged, pending`, `answered, no change`,
  `not addressed`, `unclear`) become pills (green, amber, blue, blue, red, grey); a table
  row containing ★ gets a left accent bar; a heading containing `TRADEOFF:` gets a
  labelled callout box around its section.
- Code blocks keep monospace and wrap off; inline code uses a tinted background.
- No external scripts or stylesheets except Google Fonts.

Self-check: every `## ` and `### ` line of review.md appears in review.html; table row
counts match. Return ONLY the output path, the converter used, the heading count, and any
BLOCKED: line for content you could not place. No HTML in your reply.
```
