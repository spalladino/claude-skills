#!/usr/bin/env python3
"""Write threads.md for a PR: every review thread with its resolution state, the hunk it
was made on, and — for unresolved threads — what changed in that file since the comment.

Usage: pr_threads.py <repo_root> <owner/repo> <pr> <head_sha> --me <login> \
           --resolved-out threads-resolved.md > threads.md

The main agent decides whether a comment was addressed by reading this file only, so this
script fetches everything with pagination: threads and their replies, top-level reviews,
conversation comments, force-push events. Per unresolved thread it runs
`git diff <originalCommit> <head> -- <path> [<renamed path>]` (fetching the original
commit from origin if it is not local) and lists the commits in head that the commented
commit did not have. That diff is *starting* evidence: an ask may be satisfied elsewhere,
and after a rebase the commit list includes rewritten commits.
"""
import argparse
import json
import subprocess
import sys


def sh(*args, cwd=None):
    """Run a command; return (returncode, stdout)."""
    r = subprocess.run(args, capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout


def gql(query, **vars):
    cmd = ['gh', 'api', 'graphql', '-f', f'query={query}']
    for k, v in vars.items():
        if v is None:
            continue
        cmd += ['-F' if isinstance(v, int) else '-f', f'{k}={v}']
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'gh api graphql failed: {r.stderr.strip()}')
    return json.loads(r.stdout)['data']['repository']['pullRequest']


PR_ARGS = 'query($owner:String!,$name:String!,$pr:Int!,$after:String){ repository(owner:$owner,name:$name){ pullRequest(number:$pr){ %s } } }'
HEAD_Q = 'query($owner:String!,$name:String!,$pr:Int!){ repository(owner:$owner,name:$name){ pullRequest(number:$pr){ headRefOid } } }'
PAGE = 'pageInfo{hasNextPage endCursor}'
COMMENT_FIELDS = 'author{login} body createdAt url diffHunk originalCommit{oid} commit{oid} path'

THREADS_Q = PR_ARGS % f'''
  reviewThreads(first:50,after:$after){{ {PAGE} nodes{{ id isResolved isOutdated path line originalLine
    startLine originalStartLine diffSide resolvedBy{{login}}
    comments(first:50){{ {PAGE} nodes{{ {COMMENT_FIELDS} }} }} }} }}'''
THREAD_COMMENTS_Q = '''query($id:ID!,$after:String){ node(id:$id){ ... on PullRequestReviewThread{
  comments(first:50,after:$after){ pageInfo{hasNextPage endCursor} nodes{ %s } } } } }''' % COMMENT_FIELDS
REVIEWS_Q = PR_ARGS % f'reviews(first:100,after:$after){{ {PAGE} nodes{{ author{{login}} state body submittedAt url commit{{oid}} }} }}'
COMMENTS_Q = PR_ARGS % f'comments(first:100,after:$after){{ {PAGE} nodes{{ author{{login}} body createdAt url }} }}'
FORCE_Q = PR_ARGS % f'''timelineItems(first:100,after:$after,itemTypes:[HEAD_REF_FORCE_PUSHED_EVENT]){{ {PAGE} nodes{{
  ... on HeadRefForcePushedEvent{{ createdAt actor{{login}} beforeCommit{{oid}} afterCommit{{oid}} }} }} }}'''


def paginate(query, field, **vars):
    nodes, after = [], None
    while True:
        d = gql(query, after=after, **vars)[field]
        nodes += d['nodes']
        if not d['pageInfo']['hasNextPage']:
            return nodes
        after = d['pageInfo']['endCursor']


def thread_comments(t):
    cs = t['comments']['nodes']
    after = t['comments']['pageInfo']['endCursor'] if t['comments']['pageInfo']['hasNextPage'] else None
    while after:
        cmd = ['gh', 'api', 'graphql', '-f', f'query={THREAD_COMMENTS_Q}', '-f', f"id={t['id']}", '-f', f'after={after}']
        d = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)['data']['node']['comments']
        cs += d['nodes']
        after = d['pageInfo']['endCursor'] if d['pageInfo']['hasNextPage'] else None
    return cs


def have_commit(repo, sha):
    return sh('git', '-C', repo, 'cat-file', '-e', f'{sha}^{{commit}}')[0] == 0


def ensure_commit(repo, sha):
    if have_commit(repo, sha):
        return True
    sh('git', '-C', repo, 'fetch', '-q', 'origin', sha)  # best effort; servers may refuse unreachable shas
    return have_commit(repo, sha)


_rename_cache = {}


def renamed_to(repo, orig, head, path):
    """Head path of `path` if the range orig..head renamed it, else None."""
    if orig not in _rename_cache:
        code, out = sh('git', '-C', repo, 'diff', '--name-status', '-z', '-M', f'{orig}..{head}')
        m, fields, i = {}, out.split('\0'), 0
        while i < len(fields) and fields[i]:
            if fields[i][0] in 'RC':
                m[fields[i + 1]] = fields[i + 2]
                i += 3
            else:
                i += 2
        _rename_cache[orig] = m if code == 0 else {}
    return _rename_cache[orig].get(path)


def short(s, n=7):
    return (s or '')[:n]


def login(node):
    return (node or {}).get('author', {}).get('login') or '?' if node and node.get('author') else '?'


def one_line(body, n=120):
    b = ' '.join((body or '').split())
    return b if len(b) <= n else b[:n - 1] + '…'


def fence(text, lang=''):
    text = text.rstrip('\n')
    return f'```{lang}\n{text}\n```\n' if text else '_(empty)_\n'


def quote(body):
    return '\n'.join('  > ' + l for l in (body or '').splitlines()) or '  > _(empty)_'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repo')
    ap.add_argument('owner_repo')
    ap.add_argument('pr', type=int)
    ap.add_argument('head')
    ap.add_argument('--me', default='', help='reviewer of interest; threads they took part in are starred')
    ap.add_argument('--context', type=int, default=12, help='lines of head code around the thread line')
    ap.add_argument('--resolved-out', default='', help='file to receive resolved threads in full')
    a = ap.parse_args()
    owner, name = a.owner_repo.split('/')
    v = dict(owner=owner, name=name, pr=a.pr)
    permalink = lambda path, line: f'https://github.com/{a.owner_repo}/blob/{a.head}/{path}' + (f'#L{line}' if line else '')

    live_head = gql(HEAD_Q, **v)['headRefOid']
    threads = paginate(THREADS_Q, 'reviewThreads', **v)
    reviews = paginate(REVIEWS_Q, 'reviews', **v)
    comments = paginate(COMMENTS_Q, 'comments', **v)
    force = paginate(FORCE_Q, 'timelineItems', **v)
    for t in threads:
        t['all_comments'] = thread_comments(t)

    out = sys.stdout
    star = lambda logins: '★ ' if a.me and a.me in logins else ''

    out.write(f'# Threads: {a.owner_repo}#{a.pr}\n\nhead: `{a.head}`   reviewer of interest: `{a.me or "-"}`'
              f' — ★ marks anything they wrote or took part in\n\n')
    if live_head != a.head:
        out.write(f'> **WARNING:** the PR head on GitHub is now `{short(live_head)}`, not the pinned `{short(a.head)}`. '
                  f'Thread line numbers below are GitHub\'s, relative to the live head; the head excerpts and diffs use the '
                  f'pinned sha. Re-run gather to realign.\n\n')
    live_head_ok = live_head == a.head

    out.write('## Force pushes\n\n')
    out.write('none\n' if not force else '')
    for e in force:
        out.write(f"- {e['createdAt']} by {(e.get('actor') or {}).get('login', '?')}: "
                  f"`{short((e.get('beforeCommit') or {}).get('oid'))}` → `{short((e.get('afterCommit') or {}).get('oid'))}`\n")
    out.write('\nA force push is not evidence that a comment was addressed; only the code is.\n\n')

    out.write('## Top-level reviews (may contain asks not tied to a line)\n\n')
    revs = [r for r in reviews if (r.get('body') or '').strip() or r['state'] != 'COMMENTED']
    out.write('none\n\n' if not revs else '')
    for r in revs:
        lg = login(r)
        out.write(f"- {r['submittedAt']} {star([lg])}{lg} **{r['state']}** @ `{short((r.get('commit') or {}).get('oid'))}` — {r['url']}\n")
        if (r.get('body') or '').strip():
            out.write('\n' + quote(r['body']) + '\n\n')
    out.write('\n')

    out.write('## Conversation comments (may contain asks not tied to a line)\n\n')
    out.write('none\n\n' if not comments else '')
    for c in comments:
        lg = login(c)
        out.write(f"- {c['createdAt']} {star([lg])}{lg} — {c['url']}\n\n{quote(c['body'])}\n\n")

    unresolved = [t for t in threads if not t['isResolved']]
    resolved = [t for t in threads if t['isResolved']]

    out.write(f'## Unresolved threads ({len(unresolved)})\n\n')
    out.write('none\n\n' if not unresolved else '')
    for i, t in enumerate(unresolved, 1):
        cs = t['all_comments']
        first = cs[0] if cs else {}
        participants = [login(c) for c in cs]
        line, side = t.get('line'), t.get('diffSide')
        new_path = None
        orig = (first.get('originalCommit') or {}).get('oid')
        have_orig = bool(orig) and ensure_commit(a.repo, orig)
        if have_orig:
            new_path = renamed_to(a.repo, orig, a.head, t['path'])
        head_path = new_path or t['path']

        out.write(f"### T{i} — {star(participants)}{login(first)} on `{t['path']}`"
                  f"{f' line {line}' if line else ' (no current line)'}{' (outdated)' if t['isOutdated'] else ''}\n\n")
        out.write(f"thread url: {first.get('url', '')}\nthread id: `{t['id']}` (use this to reply within a review)\n")
        out.write(f"position: original line {t.get('originalLine')} ({side} side of the diff at the time)"
                  f" · current line at head: {line if line else 'none — line removed, moved, or a file-level comment'}\n")
        if new_path:
            out.write(f"renamed since the comment: `{t['path']}` → `{new_path}`\n")
        if line and side == 'RIGHT':
            out.write(f'head permalink: {permalink(head_path, line)}\n')
        out.write(f"commented at commit: `{short(orig)}`\n\n")
        out.write('commented hunk:\n\n' + fence(first.get('diffHunk', ''), 'diff') + '\n')
        out.write(f'comments ({len(cs)}):\n\n')
        for c in cs:
            lg = login(c)
            out.write(f"- {c['createdAt']} {star([lg])}{lg}:\n\n{quote(c['body'])}\n\n")

        if have_orig:
            paths = [t['path']] + ([new_path] if new_path else [])
            code, diff = sh('git', '-C', a.repo, 'diff', '-M', f'{orig}..{a.head}', '--', *paths)
            out.write(f"file changes since the comment (`git diff {short(orig)}..{short(a.head)} -- {' '.join(paths)}`):\n\n")
            if code != 0:
                out.write('_(git diff failed; evidence unavailable)_\n')
            elif diff.strip():
                out.write(fence(diff, 'diff'))
            else:
                out.write('_(file unchanged since the comment — the ask may still be met elsewhere; check at head)_\n')
            code, log = sh('git', '-C', a.repo, 'log', '--format=- `%h` %ad %s', '--date=short',
                           f'{orig}..{a.head}', '--', *paths)
            out.write('\ncommits touching the file that the commented commit did not have'
                      ' (after a rebase this includes rewritten commits):\n\n'
                      + ('_(git log failed; unavailable)_\n' if code != 0 else (log or '_(none)_\n')) + '\n')
        else:
            out.write(f'_(original commit `{short(orig)}` not available locally or from origin; compare the hunk above'
                      f' with the head code below yourself)_\n\n')

        if line and side == 'RIGHT':
            lo, hi = max(1, line - a.context), line + a.context
            code, src = sh('git', '-C', a.repo, 'show', f'{a.head}:{head_path}')
            if code != 0:
                out.write(f'_(`{head_path}` does not exist at the pinned head, or git show failed)_\n\n')
            elif not src.strip():
                out.write(f'_(`{head_path}` is empty at head)_\n\n')
            else:
                lines = src.splitlines()[lo - 1:hi]
                numbered = '\n'.join(f'{lo + k:>5}  {l}' for k, l in enumerate(lines))
                note = '' if live_head_ok else ' (line numbers may be off: head moved, see warning)'
                out.write(f"head code `{head_path}` lines {lo}–{min(hi, lo + len(lines) - 1)}{note}:\n\n" + fence(numbered) + '\n')
        elif line:
            out.write(f'_(GitHub reports line {line} on the {side} side, i.e. base-side coordinates; no head excerpt)_\n\n')

    out.write(f'## Resolved threads ({len(resolved)}) — one line each; flag one in the review only if it looks wrongly resolved'
              + (f'; full text in `{a.resolved_out}`' if a.resolved_out else '') + '\n\n')
    out.write('none\n' if not resolved else '')
    for t in resolved:
        cs = t['all_comments']
        first, last = (cs[0], cs[-1]) if cs else ({}, {})
        participants = [login(c) for c in cs]
        out.write(f"- {star(participants)}{login(first)} on `{t['path']}`:{t.get('line') or t.get('originalLine')}"
                  f" — resolved by {(t.get('resolvedBy') or {}).get('login', '?')}"
                  f" — first: “{one_line(first.get('body'))}” — last ({login(last)}): “{one_line(last.get('body'))}”"
                  f" — {first.get('url', '')}\n")

    if a.resolved_out:
        with open(a.resolved_out, 'w') as f:
            f.write(f'# Resolved threads in full: {a.owner_repo}#{a.pr}\n\n')
            for i, t in enumerate(resolved, 1):
                cs = t['all_comments']
                first = cs[0] if cs else {}
                f.write(f"## RT{i} — {login(first)} on `{t['path']}`:{t.get('line') or t.get('originalLine')}"
                        f" — resolved by {(t.get('resolvedBy') or {}).get('login', '?')} — {first.get('url', '')}\n\n")
                f.write('commented hunk:\n\n' + fence(first.get('diffHunk', ''), 'diff') + '\n')
                for c in cs:
                    f.write(f"- {c['createdAt']} {login(c)}:\n\n{quote(c['body'])}\n\n")


if __name__ == '__main__':
    main()
