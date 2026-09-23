#!/usr/bin/env python3
"""Emit the `### Files (#n)` section of an explain-pr dossier for one base..head range.

Usage: dossier_files.py <repo> <base> <head> <prnum> [--skip <regex>] >> dossier.md

For every file in `git diff --name-status base..head` (in that order) it prints the file
heading with +/- counts, an `imported by:` heuristic for non-test source files, and every
-U3 hunk verbatim under a heading that carries the head line range computed from the -U0
diff (see gather.md §3). Files matching --skip are listed at the end under `skipped:` with
their counts so the caller can paste them into the PR block.
"""
import argparse
import re
import subprocess
import sys

HUNK_RE = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')


def git(repo, *args):
    return subprocess.run(['git', '-C', repo, *args], capture_output=True, text=True, check=True).stdout


def parse_u0(text):
    """-U0 hunks -> [(old_start, head_start, head_end | None)]. head_end None means pure deletion."""
    out = []
    for line in text.splitlines():
        m = HUNK_RE.match(line)
        if not m:
            continue
        old_start, new_start = int(m.group(1)), int(m.group(3))
        new_count = int(m.group(4)) if m.group(4) is not None else 1
        out.append((old_start, new_start, None if new_count == 0 else new_start + new_count - 1))
    return out


def parse_u3(text):
    """-U3 diff -> [(old_start, old_count, header_line, body_lines)]."""
    lines = text.splitlines()
    starts = [i for i, l in enumerate(lines) if l.startswith('@@')] + [len(lines)]
    out = []
    for s, e in zip(starts, starts[1:]):
        m = HUNK_RE.match(lines[s])
        old_count = int(m.group(2)) if m.group(2) is not None else 1
        body = lines[s + 1:e]
        while body and body[-1] == '':
            body.pop()
        out.append((int(m.group(1)), old_count, lines[s], body))
    return out


def head_range(u0, old_start, old_count):
    """Head line range covered by the -U0 hunks that fall inside a -U3 hunk's old-side span."""
    lo, hi = old_start, old_start + max(old_count, 1) - 1
    matched = [h for h in u0 if lo <= h[0] <= hi]
    if not matched:
        return '?'
    if len(matched) == 1 and matched[0][2] is None:
        return f'{matched[0][1]} (deletion)'
    lo_h = min(h[1] for h in matched)
    hi_h = max(h[2] if h[2] is not None else h[1] for h in matched)
    return str(lo_h) if lo_h == hi_h else f'{lo_h}-{hi_h}'


def importers(repo, head, path):
    """Cheap grep for files at head that import `path` by stem. A heuristic, not a promise."""
    stem = re.sub(r'\.[^.]+$', '', path.rsplit('/', 1)[-1])
    pattern = rf"['\"/]{re.escape(stem)}(\.[a-z]+)?['\"]"
    res = subprocess.run(['git', '-C', repo, 'grep', '-l', '-E', pattern, head, '--', f':!{path}'],
                         capture_output=True, text=True)
    files = sorted({l.split(':', 1)[1] for l in res.stdout.splitlines() if ':' in l})
    if not files:
        return 'imported by: none found'
    if len(files) > 200:
        return f'imported by: too generic a filename to grep meaningfully (matched {len(files)} files)'
    is_test = lambda f: re.search(r'(test|spec)', f, re.I) is not None
    non_test = [f for f in files if not is_test(f)]
    tests = len(files) - len(non_test)
    line = 'imported by: ' + (', '.join(f'`{f}`' for f in non_test[:4]) or 'none')
    if len(non_test) > 4:
        line += f' (+{len(non_test) - 4} more)'
    if tests:
        line += f' · {tests} test files'
    return line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repo')
    ap.add_argument('base')
    ap.add_argument('head')
    ap.add_argument('prnum')
    ap.add_argument('--skip', default='', help='regex of paths to list under skipped: instead of diffing')
    a = ap.parse_args()
    rng = f'{a.base}..{a.head}'
    skip_re = re.compile(a.skip) if a.skip else None

    skipped = []
    out = sys.stdout
    out.write(f'### Files (#{a.prnum})\n\n')
    for line in git(a.repo, 'diff', '--name-status', rng).splitlines():
        parts = line.split('\t')
        status = parts[0]
        if status.startswith('R'):
            old, path = parts[1], parts[2]
            rename = f' (R `{old}` → `{path}`)'
        else:
            old, path, rename = None, parts[1], ''
        add, dele = git(a.repo, 'diff', '--numstat', rng, '--', path).split('\t')[:2]
        if skip_re and skip_re.search(path):
            skipped.append(f'- `{path}` (+{add} −{dele})')
            continue
        out.write(f'#### `{path}` — {status[0]}, +{add} −{dele}{rename}\n\n')
        if 'test' not in path and not path.endswith('.md'):
            out.write(importers(a.repo, a.head, path) + '\n\n')
        u0 = parse_u0(git(a.repo, 'diff', '-U0', rng, '--', path))
        for old_start, old_count, header, body in parse_u3(git(a.repo, 'diff', '-U3', rng, '--', path)):
            out.write(f'##### `{header}` → head **{head_range(u0, old_start, old_count)}**\n\n```diff\n{header}\n')
            out.write('\n'.join(body) + '\n```\n\n')
    if skipped:
        out.write('skipped (not diffed above):\n' + '\n'.join(skipped) + '\n\n')


if __name__ == '__main__':
    main()
