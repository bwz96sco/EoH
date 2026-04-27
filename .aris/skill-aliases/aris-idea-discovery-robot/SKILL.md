---
name: aris-idea-discovery-robot
description: "Workflow 1 adaptation for robotics and embodied AI. Orchestrates robotics-aware literature survey, idea generation, novelty check, and critical review to go from a broad robotics direction to benchmark-grounded, simulation-first ideas. Use when user says \"robotics idea discovery\", \"机器人找idea\", \"embodied AI idea\", \"机器人方向探索\", \"sim2real 选题\", or wants ideas for manipulation, locomotion, navigation, drones, humanoids, or general robot learning."
argument-hint: [robotics-direction]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Agent, Skill, mcp__codex__codex, mcp__codex__codex-reply
---

# ARIS Alias: aris-idea-discovery-robot

This project-local skill is an alias for upstream ARIS skill `idea-discovery-robot`.

Before doing any task for this skill:

1. Read `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/idea-discovery-robot/SKILL.md`.
2. Follow that source skill exactly; treat the source file as authoritative.
3. If the source skill refers to another ARIS slash command such as `/foo`, use this project's aliased form `/aris-foo` when invoking slash commands.
4. If the source skill refers to `~/.claude/skills/foo` or `.claude/skills/foo`, resolve that ARIS skill to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/foo` or `.claude/skills/aris-foo`.
5. For support references such as `../shared-references/...`, read them from `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/shared-references` when needed.

Do not edit this generated alias. Re-run `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh` to refresh it.
