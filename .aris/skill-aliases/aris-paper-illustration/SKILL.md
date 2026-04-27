---
name: aris-paper-illustration
description: "Generate publication-quality AI illustrations for academic papers using Gemini image generation. Creates architecture diagrams, method illustrations with Claude-supervised iterative refinement loop. Use when user says \"生成图表\", \"画架构图\", \"AI绘图\", \"paper illustration\", \"generate diagram\", or needs visual figures for papers."
argument-hint: [description-or-method-file]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, mcp__codex__codex, mcp__codex__codex-reply, WebSearch
---

# ARIS Alias: aris-paper-illustration

This project-local skill is an alias for upstream ARIS skill `paper-illustration`.

Before doing any task for this skill:

1. Read `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/paper-illustration/SKILL.md`.
2. Follow that source skill exactly; treat the source file as authoritative.
3. If the source skill refers to another ARIS slash command such as `/foo`, use this project's aliased form `/aris-foo` when invoking slash commands.
4. If the source skill refers to `~/.claude/skills/foo` or `.claude/skills/foo`, resolve that ARIS skill to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/foo` or `.claude/skills/aris-foo`.
5. For support references such as `../shared-references/...`, read them from `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/shared-references` when needed.

Do not edit this generated alias. Re-run `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh` to refresh it.
