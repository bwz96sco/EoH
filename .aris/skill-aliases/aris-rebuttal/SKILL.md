---
name: aris-rebuttal
description: "Workflow 4: Submission rebuttal pipeline. Parses external reviews, enforces coverage and grounding, drafts a safe text-only rebuttal under venue limits, and manages follow-up rounds. Use when user says \"rebuttal\", \"reply to reviewers\", \"ICML rebuttal\", \"OpenReview response\", or wants to answer external reviews safely."
argument-hint: [paper-path-or-review-bundle]
allowed-tools: Bash(*), Read, Grep, Glob, Write, Edit, Agent, Skill, mcp__codex__codex, mcp__codex__codex-reply
---

# ARIS Alias: aris-rebuttal

This project-local skill is an alias for upstream ARIS skill `rebuttal`.

Before doing any task for this skill:

1. Read `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/rebuttal/SKILL.md`.
2. Follow that source skill exactly; treat the source file as authoritative.
3. If the source skill refers to another ARIS slash command such as `/foo`, use this project's aliased form `/aris-foo` when invoking slash commands.
4. If the source skill refers to `~/.claude/skills/foo` or `.claude/skills/foo`, resolve that ARIS skill to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/foo` or `.claude/skills/aris-foo`.
5. For support references such as `../shared-references/...`, read them from `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/shared-references` when needed.

Do not edit this generated alias. Re-run `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh` to refresh it.
