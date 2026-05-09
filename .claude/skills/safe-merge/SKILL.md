---
name: safe-merge
description: Safely merge a GitHub PR after verifying CI is green. Runs `gh pr checks <pr>`, only merges if every check passes (or non-required checks are explicitly skipped), then `gh pr merge <pr> --merge --delete-branch`, syncs local main, deletes the local branch. Pass the PR number as the argument. Refuses to use `--auto` (queues unattended merges) or `--squash` unless the user explicitly asks for that strategy.
---

# safe-merge

You are landing PR `$ARGUMENTS` to main using the verified-CI-then-merge pattern this project uses. Refuse to run if `$ARGUMENTS` is empty or not a number.

## Steps

1. **Fetch latest CI status.** Run `gh pr checks $ARGUMENTS`. Parse the output:
   - "pass" / "skipping" → fine
   - "fail" / "ERROR" → STOP and report the failing check(s) with the link from the output. Do not merge.
   - "pending" / "in_progress" / "queued" → wait. Use `gh pr checks $ARGUMENTS --watch --interval 15` (Bash timeout 300000) to block until terminal. Then re-evaluate.

2. **Confirm mergeability.** Run `gh pr view $ARGUMENTS --json mergeable,mergeStateStatus,baseRefName,headRefName,isDraft`. If `isDraft` is true, STOP — do not flip drafts to ready without explicit user authorization. If `mergeable` is not `MERGEABLE`, STOP and report why.

3. **Merge.** Run `gh pr merge $ARGUMENTS --merge --delete-branch`. Use `--merge` (preserves commit history) by default. Only use `--squash` if the user has stated that preference for this PR. Never use `--auto` from this skill — that queues an unattended merge, which the project's reviewer chain blocks.

4. **Sync local.** Run these as a single Bash chain:
   ```
   git fetch origin --prune --quiet && \
   git checkout main && \
   git pull --ff-only origin main && \
   git branch -D <head-branch-name> 2>&1 | tail -1
   ```
   The head branch name comes from step 2's output. The `git branch -D` may error if the branch was already cleaned up — that's fine, swallow it.

5. **Report.** One line. Format: `Merged #N as <main-sha-short>. <head branch> deleted locally and remotely.`

## When NOT to use this skill

- PR is in draft → don't unflip; tell the user the PR is draft and stop.
- CI is failing → don't merge; report the failure.
- User wants `--squash` or `--rebase` strategy → check the user has actually said so for this specific PR; if not, ask.
- User wants `--auto` (merge-on-green-eventually) → ask first, since the auto-mode classifier blocks it.
- The PR base is not `main` → flag it; this skill is meant for landing to main only.

## Anti-patterns to avoid

- Don't add `--admin` to bypass branch protection. If checks fail, fix the cause.
- Don't `git push --force` to fix a stuck merge. If the PR can't merge, ask.
- Don't delete remote branches the PR's `--delete-branch` flag would have handled — let `gh` do it.
