---
name: aris-claims-drafting
description: "Draft patent claims for an invention. Use when user says \"撰写权利要求\", \"draft claims\", \"写权利要求书\", \"claim drafting\", or wants to create patent claims. The core skill of the patent pipeline."
argument-hint: [invention-disclosure-path]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, WebSearch, WebFetch, mcp__codex__codex, mcp__codex__codex-reply
---

# ARIS Alias: aris-claims-drafting

This project-local skill is an alias for upstream ARIS skill `claims-drafting`.

Before doing any task for this skill:

1. Read `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/claims-drafting/SKILL.md`.
2. Follow that source skill exactly; treat the source file as authoritative.
3. If the source skill refers to another ARIS slash command such as `/foo`, use this project's aliased form `/aris-foo` when invoking slash commands.
4. If the source skill refers to `~/.claude/skills/foo` or `.claude/skills/foo`, resolve that ARIS skill to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/foo` or `.claude/skills/aris-foo`.
5. For support references such as `../shared-references/...`, read them from `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/shared-references` when needed.

Do not edit this generated alias. Re-run `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh` to refresh it.
