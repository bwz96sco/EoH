---
name: aris-vast-gpu
description: "Rent, manage, and destroy GPU instances on vast.ai. Use when user says \"rent gpu\", \"vast.ai\", \"rent a server\", \"cloud gpu\", or needs on-demand GPU without owning hardware."
argument-hint: [task-description or action]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent
---

# ARIS Alias: aris-vast-gpu

This project-local skill is an alias for upstream ARIS skill `vast-gpu`.

Before doing any task for this skill:

1. Read `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/vast-gpu/SKILL.md`.
2. Follow that source skill exactly; treat the source file as authoritative.
3. If the source skill refers to another ARIS slash command such as `/foo`, use this project's aliased form `/aris-foo` when invoking slash commands.
4. If the source skill refers to `~/.claude/skills/foo` or `.claude/skills/foo`, resolve that ARIS skill to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/foo` or `.claude/skills/aris-foo`.
5. For support references such as `../shared-references/...`, read them from `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/shared-references` when needed.

Do not edit this generated alias. Re-run `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh` to refresh it.
