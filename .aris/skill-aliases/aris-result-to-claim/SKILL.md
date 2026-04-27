---
name: aris-result-to-claim
description: Use when experiments complete to judge what claims the results support, what they don't, and what evidence is still missing. Codex MCP evaluates results against intended claims and routes to next action (pivot, supplement, or confirm). Use after experiments finish — before writing the paper or running ablations.
argument-hint: [experiment-description-or-wandb-run]
allowed-tools: Bash(*), Read, Grep, Glob, Write, Edit, mcp__codex__codex, mcp__codex__codex-reply
---

# ARIS Alias: aris-result-to-claim

This project-local skill is an alias for upstream ARIS skill `result-to-claim`.

Before doing any task for this skill:

1. Read `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/result-to-claim/SKILL.md`.
2. Follow that source skill exactly; treat the source file as authoritative.
3. If the source skill refers to another ARIS slash command such as `/foo`, use this project's aliased form `/aris-foo` when invoking slash commands.
4. If the source skill refers to `~/.claude/skills/foo` or `.claude/skills/foo`, resolve that ARIS skill to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/foo` or `.claude/skills/aris-foo`.
5. For support references such as `../shared-references/...`, read them from `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/shared-references` when needed.

Do not edit this generated alias. Re-run `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh` to refresh it.
