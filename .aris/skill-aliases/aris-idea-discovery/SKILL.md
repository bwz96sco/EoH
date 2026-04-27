---
name: aris-idea-discovery
description: "Workflow 1: Full idea discovery pipeline. Orchestrates research-lit → idea-creator → novelty-check → research-review to go from a broad research direction to validated, pilot-tested ideas. Use when user says \"找idea全流程\", \"idea discovery pipeline\", \"从零开始找方向\", or wants the complete idea exploration workflow."
argument-hint: [research-direction]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, Agent, Skill, mcp__codex__codex, mcp__codex__codex-reply
---

# ARIS Alias: aris-idea-discovery

This project-local skill is an alias for upstream ARIS skill `idea-discovery`.

Before doing any task for this skill:

1. Read `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/idea-discovery/SKILL.md`.
2. Follow that source skill exactly; treat the source file as authoritative.
3. If the source skill refers to another ARIS slash command such as `/foo`, use this project's aliased form `/aris-foo` when invoking slash commands.
4. If the source skill refers to `~/.claude/skills/foo` or `.claude/skills/foo`, resolve that ARIS skill to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/foo` or `.claude/skills/aris-foo`.
5. For support references such as `../shared-references/...`, read them from `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/shared-references` when needed.

Do not edit this generated alias. Re-run `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh` to refresh it.
