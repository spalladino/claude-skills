---
name: html-explainer
description: Produce a polished, self-contained HTML explainer page for a topic, concept, system, document, or piece of code. Use whenever the user asks for an "HTML explainer", an HTML page that explains or visualizes something, or wants something explained as a standalone HTML file. The HTML/CSS authoring is delegated to a Sonnet subagent to preserve the main agent's context window; the subagent renders the prepared content verbatim and never reinterprets it.
---

# HTML Explainer

Turn a topic into a clean, standalone HTML explainer — **without** burning the main
agent's context window on hundreds of lines of markup.

The work splits into two roles that must not blur:

- **You (the main agent)** own the *content*. You have the full context of what's
  being explained, so you produce the complete, final, unambiguous text and an
  explicit spec for any diagram. This is the authoritative source of truth.
- **A Sonnet subagent** owns the *rendering*. It takes your content as immutable
  input and turns it into HTML using the pre-built template. It worries only about
  markup, layout, visual formatting, and drawing diagrams from your spec. It does
  **not** interpret, reword, summarize, add, omit, correct, or assume anything about
  the content.

Delegating the markup is the whole point: HTML/CSS is verbose and token-heavy, and
you already hold the expensive context. Hand off the mechanical part.

## Step 1 — Settle the basics

Confirm (from the request, or ask if genuinely unknown — don't over-ask):

- **What** is being explained, and the **audience/depth** if it matters.
- **Output path.** Default to `<topic-slug>.html` in the current working directory
  unless the user names a location.
- **Title.**

If the source material lives in files, read what you need now — *you*, not the
subagent, are responsible for understanding the subject matter.

## Step 2 — Write the content brief

This is the most important step. Produce a **complete, final content brief** and save
it to the scratchpad (e.g. `<scratchpad>/explainer-brief.md`). The subagent will
render exactly what's in this brief and nothing else, so it must be:

- **Complete** — every word that should appear on the page is present, in final form.
  No "expand on this", no "[add example here]", no placeholders.
- **Unambiguous** — section order is fixed; component intent is explicit; diagrams are
  fully specified down to node and edge labels.
- **Verbatim-ready** — write the actual prose, code, and table values you want shown.

Recommended brief structure:

```
# <Title>
Subtitle: <one line, or omit>

## Section: <heading>
<the exact body text, paragraph by paragraph>
[component hints in brackets, e.g. "render as a Tip callout", "numbered steps",
 "code block (language: ts)", "table with columns X/Y"]

## Diagram: <name>
Form: <flow / boxes-and-arrows / hierarchy / sequence / …>
Nodes: <exact labels>
Edges: <from → to, with exact edge labels>
Layout: <left-to-right / top-down / …>
Caption: <exact caption text>
```

Component hints map onto pre-styled pieces in the template (callouts, numbered steps,
code blocks, tables, key-value lists, figures/diagrams). Use them so the subagent
doesn't have to guess structure — but the subagent still owns final markup choices.

## Step 3 — Delegate rendering to a Sonnet subagent

Spawn **one** `Agent` with `subagent_type: "general-purpose"` and **`model: "sonnet"`**.
The prompt must contain:

1. The **absolute path to the template**: `~/.claude/skills/html-explainer/template.html`
   (instruct it to read the template first and reuse the `<style>` block unchanged).
2. The **absolute path to the content brief** from Step 2.
3. The **absolute output path** for the finished HTML file.
4. The **rendering contract**, quoted below, verbatim.

> **Rendering contract — you are a renderer, not an author.**
> - Render the brief's text **exactly as written**. Do not reword, rephrase,
>   shorten, expand, translate, reorder, or "improve" any wording. Copy code and
>   table values character-for-character.
> - Do **not** interpret the content, add facts, add examples, infer missing
>   pieces, or fix what looks like an error. You have no authority over meaning.
> - You **do** own presentation: choosing heading levels, applying the template's
>   pre-styled components, spacing, table layout, and rendering diagrams from their
>   specs. Pick the visual form for a diagram freely, but include **exactly** the
>   nodes, edges, and labels specified — no more, no fewer.
> - Keep the output a **single self-contained file**: no external fonts, scripts,
>   stylesheets, or network requests. Keep the template's `<style>` block; extend it
>   only if a component genuinely needs it.
> - If anything in the brief is missing, ambiguous, contradictory, or looks wrong,
>   **stop and return a question** prefixed `BLOCKED:` — do not guess or paper over it.
> - Return only: the output path written, and any `BLOCKED:` questions. Do not paste
>   the HTML back.

If the subagent returns `BLOCKED:`, answer from the brief/context or ask the user,
then resume the **same** agent via `SendMessage` (don't spawn a new one — that throws
away its context).

## Step 4 — Verify and deliver

- Confirm the output file exists and is non-trivial in size.
- Sanity-check it's well-formed: single `<html>` root, the `<style>` block is intact,
  no leftover template demo sections, no external `http(s)://` asset references.
- Spot-check that the rendered text matches the brief — the subagent must not have
  drifted from the wording.
- Report the path to the user and offer to open it (e.g. `open <file>` /
  `xdg-open <file>`).

## Notes

- **The brief is the contract.** If the page comes out wrong, the fix is almost always
  a sharper brief, not a chattier subagent. Keep meaning on your side of the line and
  markup on the subagent's.
- **Styling is centralized** in the template's `<style>` block — tweak it there to
  restyle every explainer. It ships with light/dark theming and print styles.
- **One subagent, one file.** For very large explainers, still prefer a single
  subagent; split into multiple pages only if the user asks.
- Use Sonnet specifically — capable enough for clean markup, and it keeps the main
  agent's context free for the reasoning that actually needs it.
