---
name: codex
description: Invoke the Codex CLI to get a second opinion on a plan, design, analysis, or piece of code. Use ONLY when the user explicitly asks to involve codex (e.g. "ask codex", "have codex review", "get codex's take", "check with codex"). Do not invoke proactively.
allowed-tools:
  - "Bash(codex exec -m gpt-5.6-terra -c model_reasoning_effort=medium --sandbox read-only --skip-git-repo-check -C *)"
  - "Bash(codex exec -m gpt-5.6-sol -c model_reasoning_effort=high --sandbox read-only --skip-git-repo-check -C *)"
  - "Bash(codex exec -m gpt-5.6-sol -c model_reasoning_effort=xhigh --sandbox read-only --skip-git-repo-check -C *)"
  - "Bash(codex exec resume *)"
  - "Bash(grep -m 1 -oE 'session id: [0-9a-f-]{36}' *)"
  - "Bash(mktemp -d -t codex-*)"
---

# Ask Codex for Review

Use the `codex` CLI to get a second opinion from a different model family. Codex runs as a separate agent and can read files in the current repo, so it's useful for sanity-checking plans, designs, risky code changes, or observations that you want challenged by a fresh perspective.

**Only invoke this skill when the user explicitly asks for codex.** Do not reach for it on your own initiative.

**Codex is not an oracle.** It can be confidently wrong, miss context, hallucinate APIs, or misread the code. Treat its response as input to your own reasoning, not a verdict. Be critical: if codex disagrees with you, weigh the argument on its merits; if codex agrees, don't assume that confirms your position.

## Unique temp paths per invocation

Multiple Claude instances may run codex concurrently, and you may call codex more than once in a single session. Always allocate a fresh directory at the start of each invocation — never hardcode paths like `/tmp/codex-prompt.md`:

```bash
mktemp -d -t codex-XXXXXXXX
```

Remember the returned path and use it literally in later tool calls for `prompt.md`, `response.md`, and `log.txt`. Separate Bash tool calls do not share shell variables, so do not rely on exporting `CODEX_DIR` in one call and using it in another. Reuse the same directory for follow-ups to that Codex session.

## Choose the model and reasoning effort

Scale both the model and reasoning effort to the review's difficulty:

| Review | Model | Reasoning effort | Use when |
| --- | --- | --- | --- |
| Routine | `gpt-5.6-terra` | `medium` | The scope and success criteria are clear, the relevant code is localized, and the review mainly needs a solid independent pass. |
| Substantive (default) | `gpt-5.6-sol` | `high` | The review involves ambiguity, cross-cutting behavior, architecture, non-obvious failure modes, or meaningful risk. Use this when unsure. |
| Exceptional | `gpt-5.6-sol` | `xhigh` | The question is unusually difficult, contentious, high-stakes, or has already survived serious pushback and needs the deepest single-agent analysis. |

Do not use `gpt-5.6-luna` for this skill. Luna is optimized for clear, repeatable, high-volume work; a critical second opinion needs more judgment. Likewise, do not use `none`, `minimal`, or `low` reasoning effort. Do not reach for `xhigh` by default: it costs more time and usage, and `high` is the normal baseline for a substantive review.

## How to invoke codex (first turn)

Use the non-interactive `codex exec` subcommand. Write the prompt to a file with the Write tool (cleaner than heredocs) and pipe it in — CLI argument quoting is brittle for multi-paragraph prompts.

```bash
codex exec \
  -m gpt-5.6-sol \
  -c model_reasoning_effort=high \
  --sandbox read-only \
  --skip-git-repo-check \
  -C "$(pwd)" \
  -o "<codex-dir>/response.md" \
  - < "<codex-dir>/prompt.md" \
  > "<codex-dir>/log.txt" 2>&1
```

Replace `<codex-dir>` with the literal path returned by `mktemp`.

Flags:

- `-m` and `model_reasoning_effort` — choose them from the table above; do not rely on the caller's configured defaults.
- `--sandbox read-only` — governs *shell commands codex may execute*, not file reads; codex can still read files under `-C`. Keep this review skill read-only.
- `--skip-git-repo-check` — avoids failures when cwd isn't a git root.
- `-C <dir>` — working directory codex sees. Point it at the narrowest repo or package that contains all files relevant to the question.
- `-o <file>` — write codex's final message to a file. Read from here cleanly rather than parsing the noisy event log.
- `-` — read the prompt from stdin (the piped prompt file).
- Redirect all stdout+stderr to `log.txt` so you can extract the session id.

Codex calls can take several minutes. Run in the background (`run_in_background: true`) if you have other work to do; otherwise accept a long foreground wait.

## Capturing the session id

After the call finishes, extract the session id from the log so follow-ups can resume the same conversation. `codex exec` prints a `session id: <uuid>` line in its human-readable log; anchor on that prefix so an unrelated UUID in the echoed prompt can't be matched by accident:

```bash
grep -m 1 -oE 'session id: [0-9a-f-]{36}' "<codex-dir>/log.txt"
```

Copy the UUID after `session id:` from the output. This depends on the human-readable log format. If it ever breaks, switch to `--json` and inspect one session-start event before choosing a field to parse — do not guess the field name.

If the grep comes up empty, fall back to `--last` when resuming — it picks the most recent session globally, so only safe if no other codex session has started since. Save the session id alongside the response path for the rest of the conversation:

> "Codex session: `<uuid>` (files in `<codex-dir>`)"

## Following up / resuming

If codex's response is unclear, seems wrong, or you want to push back, **resume the same session** rather than starting fresh — codex will have the full context of its own prior reasoning:

```bash
# Write the follow-up prompt
# (use the Write tool to create <codex-dir>/followup-N.md)

codex exec resume "<session-uuid>" \
  -m gpt-5.6-sol \
  -c model_reasoning_effort=high \
  -o "<codex-dir>/response-N.md" \
  - < "<codex-dir>/followup-N.md" \
  >> "<codex-dir>/log.txt" 2>&1
```

`codex exec resume` does not accept `--sandbox` or `-C`. Run it from the relevant working directory. Keep the original model and reasoning effort unless the follow-up has materially increased the difficulty; for example, escalate a routine Terra/medium review to Sol/high when the first response exposes deeper ambiguity. Reserve Sol/xhigh for the exceptional cases in the table above.

Use numbered filenames (`response-2.md`, `followup-2.md`, …) so earlier turns aren't overwritten. Resume whenever you disagree with codex, need clarification, want to point out an error in its response, or want to test whether it holds its position under pushback. Starting a new session throws away its context and often wastes a round-trip re-establishing the setup.

If no UUID was extracted, use `codex exec resume --last ...` instead — but only if you're confident no other codex session has run in the meantime, since `--last` is global.

## Writing the prompt

Codex starts with zero context from this conversation. Brief it like a colleague who just walked in. The prompt should include:

1. **The question** — what specifically do you want feedback on? "Review my plan" is too vague. "Is my plan for X sound? Specifically, is the assumption about Y correct, and will the approach in Z handle edge case W?" is better.

2. **Facts vs. inferences vs. asks** — be explicit about which is which. Codex can't tell them apart from prose alone.
   - **Facts**: things you verified from the code, docs, or user — give file paths and line numbers.
   - **Inferences**: things you deduced but didn't verify — label them clearly ("I inferred that...", "I'm assuming...").
   - **Plans/observations under review**: the thing you actually want critiqued — set it off in its own section.

3. **Relevant context** — paste or reference the specific code, file paths, constraints, and prior decisions codex needs. Prefer pointing codex at files (it can read them via `-C`) over pasting large blobs, but paste short snippets inline so codex can't miss them.

4. **Explicit instruction to be critical** — ask codex to look for flaws, wrong assumptions, missed edge cases, and better alternatives. Otherwise it tends to be agreeable. Sample phrasing:

   > Be critical. I want you to find problems with this plan, not validate it. Point out wrong assumptions, missed edge cases, and anything that looks like it won't work. If you think the approach is fundamentally wrong, say so. If the plan looks correct, say that too — but only after genuinely trying to break it.

5. **Response shape** — tell codex what you want back. A short verdict + bulleted concerns is usually more useful than a long essay. E.g. "Respond in under 500 words: a one-line verdict, then bullets for each concern, then a brief 'things that look fine' list."

## Prompt template

```
I'm working on <short context — what project/feature/bug>. I want a critical second opinion on <what exactly>.

## Facts (verified)
- <fact>: <file:line or source>
- ...

## Inferences (unverified — please challenge)
- I'm assuming <X>. I haven't confirmed this.
- ...

## What I'm asking you to review
<The plan / observation / code under review. Be specific. Include code or file paths.>

## What I want from you
Be critical. Try to find problems with this before you validate it. Specifically:
- Are my facts actually correct? (Check the files if you need to.)
- Are my inferences safe?
- Does the plan handle <specific edge cases>?
- Is there a simpler/better approach I'm missing?

Respond in under <N> words: one-line verdict, then bulleted concerns, then what looks fine.
```

## After codex responds

Don't just relay codex's response to the user. Do your own pass:

- **Verify claims**: if codex says "function X does Y", "file Z doesn't exist", or "flag W isn't supported", check it. Codex can hallucinate file paths, symbols, or API details — and can also misread its own environment state (e.g. claiming a call failed when it succeeded). Verify concrete factual claims against the repo, docs, or `--help` before acting on them.
- **Weigh concerns by strength**: distinguish real objections from surface-level nitpicks.
- **Flag disagreements explicitly**: if codex contradicts something you believe, tell the user both views and your current take — don't silently flip.
- **Resume rather than start over**: if you have a specific pushback or clarifying question, resume the session (see above) instead of opening a new one.
- **Summarize for the user**: a short digest ("codex flagged X and Y, I think X is valid and Y is a misread because...") is more useful than pasting the raw response. Offer the full response file path (`<codex-dir>/response.md`) in case they want to read it directly.
