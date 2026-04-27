---
name: aris-experiment-bridge
description: "Workflow 1.5: Bridge between idea discovery and auto review. Reads EXPERIMENT_PLAN.md, implements experiment code, deploys to GPU, collects initial results. Use when user says \"实现实验\", \"implement experiments\", \"bridge\", \"从计划到跑实验\", \"deploy the plan\", or has an experiment plan ready to execute."
argument-hint: [experiment-plan-path-or-topic]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, Skill, mcp__codex__codex, mcp__codex__codex-reply
---

# ARIS Alias: aris-experiment-bridge

This project-local skill is an alias for upstream ARIS skill `experiment-bridge`.

Before doing any task for this skill:

1. Read `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/experiment-bridge/SKILL.md`.
2. Follow that source skill exactly; treat the source file as authoritative.
3. If the source skill refers to another ARIS slash command such as `/foo`, use this project's aliased form `/aris-foo` when invoking slash commands.
4. If the source skill refers to `~/.claude/skills/foo` or `.claude/skills/foo`, resolve that ARIS skill to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/foo` or `.claude/skills/aris-foo`.
5. For support references such as `../shared-references/...`, read them from `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/shared-references` when needed.

Do not edit this generated alias. Re-run `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh` to refresh it.
