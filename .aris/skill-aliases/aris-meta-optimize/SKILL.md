---
name: aris-meta-optimize
description: "Analyze ARIS usage logs and propose optimizations to SKILL.md files, reviewer prompts, and workflow defaults. Outer-loop harness optimization inspired by Meta-Harness (Lee et al., 2026). Use when user says \"优化技能\", \"meta optimize\", \"improve skills\", \"分析使用记录\", or wants to optimize ARIS's own harness components based on accumulated experience."
argument-hint: [target-skill-or-all]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, mcp__codex__codex, mcp__codex__codex-reply
---

# ARIS Alias: aris-meta-optimize

This project-local skill is an alias for upstream ARIS skill `meta-optimize`.

Before doing any task for this skill:

1. Read `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/meta-optimize/SKILL.md`.
2. Follow that source skill exactly; treat the source file as authoritative.
3. If the source skill refers to another ARIS slash command such as `/foo`, use this project's aliased form `/aris-foo` when invoking slash commands.
4. If the source skill refers to `~/.claude/skills/foo` or `.claude/skills/foo`, resolve that ARIS skill to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/foo` or `.claude/skills/aris-foo`.
5. For support references such as `../shared-references/...`, read them from `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/shared-references` when needed.

Do not edit this generated alias. Re-run `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh` to refresh it.
