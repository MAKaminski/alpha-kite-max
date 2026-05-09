---
name: verify-vercel
description: Query the last N Vercel deploys for alpha-kite-max and report build times in a sortable table. Use when the user asks to verify a Vercel build-time change, compare deploy speeds across commits, or check whether a recent change regressed Vercel performance. Optionally takes a baseline target (e.g. "verify against 38s baseline").
---

# verify-vercel

You are running a Vercel build-time verification for the alpha-kite-max project.

## Project IDs (do not look up — these are stable)

- projectId: `prj_nfufcN3XCf7ZMhPhcEEPT0StFAa5`
- teamId: `team_3wz9UVlAlA9u7ZmvEFEAIhad`

## Steps

1. **Load the Vercel MCP tools you need.** Call `ToolSearch` with `query: "select:mcp__claude_ai_Vercel__list_deployments,mcp__claude_ai_Vercel__get_deployment"` and `max_results: 3`. Wait for the tools to load.

2. **List recent deployments.** Call `mcp__claude_ai_Vercel__list_deployments` with the project + team IDs. Take the 6 most-recent deployments unless the user asked for a different N.

3. **Fetch full details for each.** For every deployment in the list, call `mcp__claude_ai_Vercel__get_deployment` with the deployment ID and team ID. Capture `createdAt`, `buildingAt`, `ready`, `readyState`, source commit SHA (under `meta.githubCommitSha` typically), and the deployment URL hostname prefix.

4. **Compute build duration.** `build_seconds = (ready - buildingAt) / 1000`. If `buildingAt` is missing or `ready == buildingAt`, mark the deployment as "in flight" — do not invent a number.

5. **Render a table** sorted oldest → newest with columns: Time (UTC HH:MM:SS), Short ID (first 7 chars), Commit (first 7 chars), Build (s, 1 decimal), State.

6. **Report the verdict.** If the user gave a baseline (e.g. "38s baseline") or named a commit to compare against, compute the delta vs baseline for each post-baseline deploy and state plainly whether the trend is at/under/above baseline. If no baseline was given, just report the average of the last 3 READY deploys.

## Style

Keep the response under 250 words total. Lead with the verdict in bold, follow with the table, end with one or two sentences of context. Don't speculate about why a build was slow unless the user asks — just report the numbers.

## When NOT to use this skill

- The user wants to *trigger* a deploy → use `vercel deploy` instead, or ask the user how they want it triggered.
- The user wants logs from a specific failed deploy → use `mcp__claude_ai_Vercel__get_deployment_build_logs` directly, not this skill.
- The user is asking about *Railway* deploys → Railway uses the CLI (`railway status`, `railway logs`), not this skill.
