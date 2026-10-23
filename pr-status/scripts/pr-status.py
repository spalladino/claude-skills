#!/usr/bin/env python3
"""Status of the viewer's open PRs, grouped by what they need next.

Read-only: it only queries GitHub (gh api graphql), never changes anything.

Usage: pr-status.py [--json] [owner/repo ...]
  (default repos: AztecProtocol/aztec-packages aztec-labs-eng/aztec-node)

Each PR gets a verdict:
  ACT    something is on the author: conflicts, red CI, changes requested,
         unanswered review threads, no reviewer, ready to merge, parent merged
  NUDGE  waiting on requested reviewers; the age is how long since the request.
         Conflicts on a PR awaiting review are deferred ("later"), since the
         review may need another rebase anyway
  WAIT   nothing to do yet: CI running, auto-merge or merge queue pending,
         or approved but stacked on a PR that has not merged

Output groups PRs by verdict, then repo, then stack (bottom of the stack first).
  DRAFT  draft PRs, with their CI and conflict state for reference
"""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone

DEFAULT_REPOS = ["AztecProtocol/aztec-packages", "aztec-labs-eng/aztec-node"]
# Checks whose skip means "CI did not run" (aztec CI skips `ci` on drafts).
MAIN_CI_CHECKS = {"ci"}
# Bases that are not another PR's branch, besides the default branch.
NON_STACK_BASE_PREFIXES = ("merge-train/", "backport-to-")

VERDICTS = ["ACT", "NUDGE", "WAIT", "DRAFT"]
FAILED = {"FAILURE", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE", "ERROR"}
IGNORED = {"SKIPPED", "NEUTRAL", "STALE"}

PR_FIELDS = """
  number title url isDraft createdAt updatedAt
  baseRefName headRefName mergeable mergeStateStatus reviewDecision isInMergeQueue
  autoMergeRequest { enabledAt }
  repository { nameWithOwner defaultBranchRef { name } }
  reviewRequests(first: 20) { nodes { requestedReviewer {
    __typename ... on User { login } ... on Team { name } } } }
  reviews(last: 50) { nodes { author { __typename login } state submittedAt } }
  reviewThreads(first: 100) { nodes { isResolved isOutdated
    comments(last: 1) { nodes { author { __typename login } createdAt } } } }
  timelineItems(last: 50, itemTypes: [REVIEW_REQUESTED_EVENT]) { nodes {
    ... on ReviewRequestedEvent { createdAt requestedReviewer {
      __typename ... on User { login } ... on Team { name } } } } }
  commits(last: 1) { nodes { commit { committedDate statusCheckRollup { state
    contexts(first: 100) { nodes {
      __typename
      ... on CheckRun { name status conclusion startedAt }
      ... on StatusContext { context state createdAt } } } } } } }
"""

QUERY = """
query($q: String!) {
  viewer { login }
  search(type: ISSUE, query: $q, first: 100) { nodes { ... on PullRequest { %s } } }
}
""" % PR_FIELDS

PARENT_QUERY = """
query($owner: String!, $name: String!, $head: String!) {
  repository(owner: $owner, name: $name) {
    pullRequests(headRefName: $head, first: 5, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes { number state author { login } }
    }
  }
}
"""


def gql(query, **variables):
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        args += ["-F", f"{k}={v}"]
    out = subprocess.run(args, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"gh api graphql failed: {out.stderr.strip()}")
    return json.loads(out.stdout)["data"]


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def age(s):
    d = datetime.now(timezone.utc) - ts(s)
    if d.days >= 1:
        return f"{d.days}d"
    return f"{d.seconds // 3600}h"


def is_bot(actor):
    return not actor or actor.get("__typename") == "Bot" or actor.get("login", "").endswith("[bot]")


def reviewer_name(r):
    return (r or {}).get("login") or (r or {}).get("name") or "?"


def ci_status(commit):
    """Return (state, detail) with state in green/red/running/cancelled/not-run/none."""
    rollup = commit.get("statusCheckRollup")
    if not rollup:
        return "none", ""
    latest = {}
    for c in rollup["contexts"]["nodes"]:
        if c["__typename"] == "CheckRun":
            key, when = c["name"], c.get("startedAt") or ""
            if c["status"] != "COMPLETED":
                state = "PENDING"
            else:
                state = c["conclusion"] or "PENDING"
        else:
            key, when, state = c["context"], c.get("createdAt") or "", c["state"]
        if key not in latest or when >= latest[key][0]:
            latest[key] = (when, state)
    states = {k: s for k, (_, s) in latest.items()}
    failed = sorted(k for k, s in states.items() if s in FAILED)
    cancelled = sorted(k for k, s in states.items() if s == "CANCELLED")
    pending = sorted(k for k, s in states.items() if s in ("PENDING", "EXPECTED", "QUEUED", "IN_PROGRESS"))
    if failed:
        return "red", ", ".join(failed)
    if pending:
        return "running", ", ".join(pending)
    if cancelled:
        return "cancelled", ", ".join(cancelled)
    main = [k for k in states if k in MAIN_CI_CHECKS]
    if main and all(states[k] in IGNORED for k in main):
        return "not-run", ""
    return "green", ""


def find_parent(pr, mine_by_head):
    """For a stacked PR, return (number, state) of the PR whose head is its base."""
    repo, base = pr["repository"]["nameWithOwner"], pr["baseRefName"]
    if (repo, base) in mine_by_head:
        return mine_by_head[(repo, base)], "OPEN"
    owner, name = repo.split("/")
    nodes = gql(PARENT_QUERY, owner=owner, name=name, head=base)["repository"]["pullRequests"]["nodes"]
    open_ = [n for n in nodes if n["state"] == "OPEN"]
    n = (open_ or nodes or [None])[0]
    return (n["number"], n["state"]) if n else (None, None)


def analyze(pr, me, mine_by_head):
    default = pr["repository"]["defaultBranchRef"]["name"]
    commit = pr["commits"]["nodes"][0]["commit"]
    last_commit = commit["committedDate"]
    ci, ci_detail = ci_status(commit)

    # Stacking
    base = pr["baseRefName"]
    stacked = base != default and not base.startswith(NON_STACK_BASE_PREFIXES)
    parent = find_parent(pr, mine_by_head) if stacked else (None, None)

    # Reviews: latest per human reviewer
    latest_review = {}
    for r in pr["reviews"]["nodes"]:
        a = r["author"]
        if is_bot(a) or a["login"] == me or r["state"] in ("PENDING", "DISMISSED"):
            continue
        prev = latest_review.get(a["login"])
        # A COMMENTED review after an APPROVED/CHANGES_REQUESTED does not replace the verdict.
        if prev and r["state"] == "COMMENTED" and prev["state"] != "COMMENTED":
            continue
        latest_review[a["login"]] = r
    approved = sorted(k for k, r in latest_review.items() if r["state"] == "APPROVED")
    changes = sorted(k for k, r in latest_review.items() if r["state"] == "CHANGES_REQUESTED")
    commented = sorted(k for k, r in latest_review.items() if r["state"] == "COMMENTED")

    requested_at = {}
    for ev in pr["timelineItems"]["nodes"]:
        if ev:
            requested_at[reviewer_name(ev.get("requestedReviewer"))] = ev["createdAt"]
    pending = []
    for n in pr["reviewRequests"]["nodes"]:
        name = reviewer_name(n["requestedReviewer"])
        pending.append((name, requested_at.get(name)))

    # Unresolved threads, split by who spoke last
    threads_me, threads_them = 0, 0
    for t in pr["reviewThreads"]["nodes"]:
        if t["isResolved"] or not t["comments"]["nodes"]:
            continue
        last = t["comments"]["nodes"][0]["author"]
        if last and last.get("login") == me:
            threads_them += 1
        else:
            threads_me += 1

    conflicts = pr["mergeable"] == "CONFLICTING"
    merge_state = pr["mergeStateStatus"]
    queued = pr["isInMergeQueue"] or pr["autoMergeRequest"] is not None
    pending_names = {p for p, _ in pending}

    act, nudge, wait, later = [], [], [], []
    if parent[1] in ("MERGED", "CLOSED"):
        act.append(f"parent #{parent[0]} is {parent[1].lower()}: retarget to {default} and rebase")
    if conflicts:
        # Rebasing before a pending review is wasted work: review changes will need another one.
        if pending and not pr["isDraft"]:
            later.append(f"conflicts with {base}: rebase after review")
        else:
            act.append(f"conflicts with {base}: rebase")
    if ci == "red":
        act.append(f"CI red: {ci_detail}")
    elif ci == "cancelled":
        act.append(f"CI cancelled: {ci_detail}")
    elif ci == "not-run" and not pr["isDraft"]:
        act.append("CI has not run")
    for who in changes:
        if who in pending_names:
            continue
        if ts(last_commit) > ts(latest_review[who]["submittedAt"]):
            act.append(f"re-request review from {who} (changes requested, pushed since)")
        else:
            act.append(f"address changes requested by {who}")
    for who in commented:
        if who not in pending_names and not approved and ts(last_commit) > ts(latest_review[who]["submittedAt"]):
            act.append(f"re-request review from {who} (commented, pushed since)")
    if threads_me:
        act.append(f"{threads_me} unresolved thread(s) awaiting your reply")
    if not pending and not latest_review and not pr["isDraft"]:
        act.append("no reviewer requested")
    if pr["reviewDecision"] == "APPROVED" and not conflicts and ci == "green" and not queued:
        if stacked and parent[1] == "OPEN":
            wait.append(f"approved; merges after parent #{parent[0]}")
        else:
            act.append("approved and green: merge")

    for who, when in pending:
        nudge.append(f"{who} (requested {age(when)} ago)" if when else who)
    if ci == "running":
        wait.append(f"CI running: {ci_detail}")
    if queued:
        wait.append("in merge queue" if pr["isInMergeQueue"] else "auto-merge enabled")

    if pr["isDraft"]:
        verdict = "DRAFT"
    elif act:
        verdict = "ACT"
    elif nudge:
        verdict = "NUDGE"
    else:
        verdict = "WAIT"

    review_bits = []
    if approved:
        review_bits.append("approved by " + ", ".join(approved))
    if changes:
        review_bits.append("changes requested by " + ", ".join(changes))
    if commented:
        review_bits.append("commented by " + ", ".join(commented))
    if pending:
        review_bits.append("awaiting " + ", ".join(nudge))
    if threads_them:
        review_bits.append(f"{threads_them} thread(s) awaiting reviewer")

    return {
        "verdict": verdict,
        "repo": pr["repository"]["nameWithOwner"],
        "number": pr["number"],
        "title": pr["title"],
        "url": pr["url"],
        "draft": pr["isDraft"],
        "base": base,
        "stacked_on": parent[0],
        "parent_state": parent[1],
        "ci": ci,
        "ci_detail": ci_detail,
        "conflicts": conflicts,
        "merge_state": merge_state,
        "review_decision": pr["reviewDecision"],
        "reviews": "; ".join(review_bits) or "no reviews",
        "act": act,
        "nudge": nudge,
        "wait": wait,
        "later": later,
        "last_commit_age": age(last_commit),
        "updated_age": age(pr["updatedAt"]),
    }


def assign_stacks(rows):
    """Set each row's stack root (the lowest of the user's open PRs in its chain) and depth."""
    by_key = {(r["repo"], r["number"]): r for r in rows}
    for r in rows:
        node, depth = r, 0
        while node["stacked_on"] and (node["repo"], node["stacked_on"]) in by_key:
            node, depth = by_key[(node["repo"], node["stacked_on"])], depth + 1
        r["stack_root"], r["stack_depth"] = node["number"], depth
    stacks = {}
    for r in rows:
        stacks.setdefault((r["repo"], r["stack_root"]), []).append(r)
    for members in stacks.values():
        members.sort(key=lambda m: (m["stack_depth"], m["number"]))
        chain = [m["number"] for m in members] if len(members) > 1 else []
        for m in members:
            m["stack"] = chain


def render_pr(r, indent):
    pad = " " * indent
    out = [f"{pad}- **#{r['number']}** {r['title']}  \n{pad}  {r['url']}"]
    facts = [f"CI {r['ci']}" + (f" ({r['ci_detail']})" if r["ci_detail"] else "")]
    if r["conflicts"]:
        facts.append("CONFLICTS")
    elif r["merge_state"] == "UNKNOWN":
        facts.append("conflicts unknown")
    elif r["merge_state"] == "BEHIND":
        facts.append("behind base")
    if r["stacked_on"]:
        facts.append(f"stacked on #{r['stacked_on']} ({r['parent_state'].lower()})")
    elif r["base"] not in ("main", "next", "master"):
        facts.append(f"base {r['base']}")
    facts.append(r["reviews"])
    facts.append(f"last commit {r['last_commit_age']} ago")
    out.append(f"{pad}  " + " · ".join(facts))
    for label in ("act", "wait", "later"):
        for i in r[label]:
            out.append(f"{pad}  - {label}: {i}")
    return out


def render(rows):
    """Group by verdict, then repo, then stack (bottom of the stack first)."""
    out = []
    for v in VERDICTS:
        group = [r for r in rows if r["verdict"] == v]
        if not group:
            continue
        out.append(f"## {v} ({len(group)})\n")
        for repo in sorted({r["repo"] for r in group}):
            out.append(f"### {repo}\n")
            stacks = {}
            for r in group:
                if r["repo"] == repo:
                    stacks.setdefault(r["stack_root"], []).append(r)
            for members in sorted(stacks.values(), key=lambda ms: -max(m["number"] for m in ms)):
                members.sort(key=lambda m: (m["stack_depth"], m["number"]))
                chain = members[0]["stack"]
                if chain:
                    out.append("- Stack " + " → ".join(f"#{n}" for n in chain))
                    for m in members:
                        out += render_pr(m, 2)
                else:
                    out += render_pr(members[0], 0)
            out.append("")
    return "\n".join(out) if out else "No open PRs."


def main():
    argv = sys.argv[1:]
    as_json = "--json" in argv
    repos = [a for a in argv if a != "--json"] or DEFAULT_REPOS
    q = "is:pr is:open author:@me archived:false " + " ".join(f"repo:{r}" for r in repos)
    data = gql(QUERY, q=q)
    # GitHub computes mergeability lazily; the first query kicks it off.
    if any(p and p["mergeable"] == "UNKNOWN" for p in data["search"]["nodes"]):
        time.sleep(5)
        data = gql(QUERY, q=q)
    me = data["viewer"]["login"]
    prs = [p for p in data["search"]["nodes"] if p]
    mine_by_head = {(p["repository"]["nameWithOwner"], p["headRefName"]): p["number"] for p in prs}
    rows = [analyze(p, me, mine_by_head) for p in prs]
    assign_stacks(rows)
    rows.sort(key=lambda r: (VERDICTS.index(r["verdict"]), r["repo"], -r["stack_root"], r["stack_depth"]))
    print(json.dumps(rows, indent=2) if as_json else render(rows))


if __name__ == "__main__":
    main()
