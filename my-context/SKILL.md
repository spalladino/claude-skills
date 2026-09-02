---
name: my-context
description: Look up who the user is on GitHub and Linear — usernames, IDs, repos, team — whenever a task needs to query or filter GitHub PRs, Linear issues, or team activity for the user or their team. Use before running gh or Linear MCP calls that need the user's handle, repo, or team ID.
---

# My Context

Identity and config values live in `config.local.md` next to this SKILL.md, in this
skill's own directory. That file is gitignored — if it doesn't exist, create it from
`config.local.md.example`. Read it and use its values whenever a task needs the
user's GitHub handle, repos, Linear team, or Linear user identity.

Note: `GitHub repos` is a **list**. Any `gh` command must be run once per repo in the
list, not just against the first one.

## Common uses

- **Filtering GitHub PRs**: use `gh pr list` or `gh search prs` with `--author
  <github-username>`, looping over each repo in the config's repo list.
- **Listing Linear issues**: use `mcp__linear-server__list_issues` filtered to the
  configured Linear user (assignee) and team.
- **Standup-style summaries**: if asked to summarize recent activity, compose it as
  Done / In Review / Todo, leading each item with the Linear issue ID when available
  and linking Linear issues to their corresponding PRs where possible.
