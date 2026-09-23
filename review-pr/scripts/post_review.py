#!/usr/bin/env python3
"""Post a set of comments to a PR as ONE review, each signed as agent-written.

Usage: post_review.py <owner/repo> <pr> <head_sha> <post.json> --me <login>
                      [--event COMMENT|APPROVE|REQUEST_CHANGES|PENDING] [--dry-run]

post.json:
{
  "body": "optional review summary (markdown)",
  "comments": [
    {"thread_id": "PRRT_…", "body": "reply inside an existing thread"},
    {"path": "yarn-project/x.ts", "line": 42, "side": "RIGHT", "body": "new comment on a head line"},
    {"path": "yarn-project/x.ts", "start_line": 40, "line": 42, "side": "RIGHT", "body": "multi-line"}
  ]
}

Behaviour:
- Reuses the caller's existing pending review on the PR if there is one, else creates one
  pinned to <head_sha>. Every comment lands inside that review, so the author gets one
  notification and the reviewer sees one bundle.
- Appends the signature "_written by claude_" to every comment and to the review body.
- --event PENDING (the default) leaves the review open for the human to submit from the web.
  Any other event submits it.
- --dry-run prints exactly what would be posted and touches nothing.
"""
import argparse
import json
import subprocess
import sys

SIG = '\n\n_written by claude_'


def gql(query, **vars):
    cmd = ['gh', 'api', 'graphql', '-f', f'query={query}']
    for k, v in vars.items():
        cmd += ['-F' if isinstance(v, int) else '-f', f'{k}={v}']
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'gh api graphql failed: {r.stderr.strip()}\n{r.stdout.strip()}')
    d = json.loads(r.stdout)
    if d.get('errors'):
        sys.exit('graphql errors: ' + json.dumps(d['errors'], indent=1))
    return d['data']


PR_Q = '''query($owner:String!,$name:String!,$pr:Int!){ repository(owner:$owner,name:$name){ pullRequest(number:$pr){
  id headRefOid reviews(first:20,states:[PENDING]){ nodes{ id author{login} } } } } }'''
CREATE_REVIEW = 'mutation($pr:ID!,$sha:GitObjectID!){ addPullRequestReview(input:{pullRequestId:$pr,commitOID:$sha}){ pullRequestReview{ id url } } }'
ADD_REPLY = 'mutation($rev:ID!,$thread:ID!,$body:String!){ addPullRequestReviewThreadReply(input:{pullRequestReviewId:$rev,pullRequestReviewThreadId:$thread,body:$body}){ comment{ url } } }'
ADD_THREAD = '''mutation($rev:ID!,$path:String!,$line:Int!,$side:DiffSide!,$body:String!){
  addPullRequestReviewThread(input:{pullRequestReviewId:$rev,path:$path,line:$line,side:$side,body:$body}){ thread{ id } } }'''
ADD_THREAD_RANGE = '''mutation($rev:ID!,$path:String!,$line:Int!,$start:Int!,$side:DiffSide!,$body:String!){
  addPullRequestReviewThread(input:{pullRequestReviewId:$rev,path:$path,line:$line,startLine:$start,side:$side,startSide:$side,body:$body}){ thread{ id } } }'''
SUBMIT = 'mutation($rev:ID!,$event:PullRequestReviewEvent!,$body:String!){ submitPullRequestReview(input:{pullRequestReviewId:$rev,event:$event,body:$body}){ pullRequestReview{ url state } } }'
UPDATE_BODY = 'mutation($rev:ID!,$body:String!){ updatePullRequestReview(input:{pullRequestReviewId:$rev,body:$body}){ pullRequestReview{ url } } }'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('owner_repo')
    ap.add_argument('pr', type=int)
    ap.add_argument('head')
    ap.add_argument('post_json')
    ap.add_argument('--me', required=True, help='GitHub login of the human who asked (to find their pending review)')
    ap.add_argument('--event', default='PENDING', choices=['PENDING', 'COMMENT', 'APPROVE', 'REQUEST_CHANGES'])
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    owner, name = a.owner_repo.split('/')
    plan = json.load(open(a.post_json))
    sig = SIG
    comments = plan.get('comments', [])
    body = (plan.get('body') or '').rstrip()
    if not comments and not body:
        sys.exit('nothing to post: no comments and no body')
    for c in comments:
        if not c.get('body', '').strip():
            sys.exit(f'empty body in comment: {c}')
        if 'thread_id' not in c and not (c.get('path') and c.get('line')):
            sys.exit(f'comment needs thread_id or path+line: {c}')
        c['body'] = c['body'].rstrip() + sig
    if body or a.event != 'PENDING':
        body = (body or '') + sig

    if a.dry_run:
        print(f'DRY RUN — would post to {a.owner_repo}#{a.pr} at {a.head[:7]} as ONE review, event={a.event}\n')
        if body:
            print('review body:\n' + body + '\n')
        for i, c in enumerate(comments, 1):
            where = f"reply in thread {c['thread_id']}" if 'thread_id' in c else \
                f"new comment on {c['path']}:{c.get('start_line', c['line'])}{'-' + str(c['line']) if c.get('start_line') else ''} ({c.get('side', 'RIGHT')})"
            print(f'--- comment {i}: {where}\n{c["body"]}\n')
        return

    pr = gql(PR_Q, owner=owner, name=name, pr=a.pr)['repository']['pullRequest']
    if pr['headRefOid'] != a.head:
        sys.exit(f"PR head is {pr['headRefOid'][:7]}, not the pinned {a.head[:7]}; re-run gather before posting")
    mine = [r for r in pr['reviews']['nodes'] if (r.get('author') or {}).get('login') == a.me]
    if mine:
        review_id = mine[0]['id']
        print(f'reusing existing pending review {review_id}')
    else:
        review_id = gql(CREATE_REVIEW, pr=pr['id'], sha=a.head)['addPullRequestReview']['pullRequestReview']['id']
        print(f'created pending review {review_id}')

    for c in comments:
        if 'thread_id' in c:
            gql(ADD_REPLY, rev=review_id, thread=c['thread_id'], body=c['body'])
        elif c.get('start_line'):
            gql(ADD_THREAD_RANGE, rev=review_id, path=c['path'], line=int(c['line']), start=int(c['start_line']),
                side=c.get('side', 'RIGHT'), body=c['body'])
        else:
            gql(ADD_THREAD, rev=review_id, path=c['path'], line=int(c['line']), side=c.get('side', 'RIGHT'), body=c['body'])
    print(f'added {len(comments)} comment(s)')

    if a.event == 'PENDING':
        if body:
            gql(UPDATE_BODY, rev=review_id, body=body)
        print(f'review left PENDING: submit or discard it from https://github.com/{a.owner_repo}/pull/{a.pr}/files')
    else:
        res = gql(SUBMIT, rev=review_id, event=a.event, body=body)['submitPullRequestReview']['pullRequestReview']
        print(f"submitted as {res['state']}: {res['url']}")


if __name__ == '__main__':
    main()
