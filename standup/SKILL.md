---
name: standup
description: Generate a standup update by reviewing recent GitHub PRs and Linear issues
argument-hint: "[since-date-or-day, e.g. 'friday' or '2026-03-13']"
disable-model-invocation: true
allowed-tools: Bash(gh pr list *), mcp__linear-server__list_issues
---

# Standup Update

Generate a concise standup update for the user based on their recent activity across GitHub and Linear.

## Parameters

Read GitHub username, GitHub repo, Linear team, and Linear user (email, ID, and assignee name) from `standup/config.local.md` in this skill's directory. That file is gitignored — create it from the example if it doesn't exist.

## Time range

The user will specify a "since" reference (e.g. "friday", "yesterday", "2026-03-13"). Convert relative references to absolute dates. If no argument is given, default to the last working day at 14:30 UTC. The argument is: $ARGUMENTS

## Steps

1. **GitHub PRs**: Use `gh pr list` to fetch recent PRs (all states) authored by the configured GitHub username in the configured repo, filtered to the relevant time range using `--search "updated:>=<date>"`.

2. **Linear issues**: Use the `mcp__linear-server__list_issues` tool to fetch issues assigned to the configured Linear user in the configured team, updated since the relevant date.

3. **Compose the update** with these sections:
   - **Done**: Completed/merged items (link Linear issues to their corresponding PRs where possible)
   - **In Review**: Open PRs and issues in review
   - **Todo/Backlog**: Upcoming items from Linear
   - **TL;DR for standup**: A 2-3 sentence summary suitable for a synchronous standup

Keep it concise and group related PRs and Linear issues together. Lead with the Linear issue ID when available.
