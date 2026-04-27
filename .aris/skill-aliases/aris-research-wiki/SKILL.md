---
name: aris-research-wiki
description: "Persistent research knowledge base that accumulates papers, ideas, experiments, claims, and their relationships across the entire research lifecycle. Inspired by Karpathy's LLM Wiki pattern. Use when user says \"知识库\", \"research wiki\", \"add paper\", \"wiki query\", \"查知识库\", or wants to build/query a persistent field map."
argument-hint: [subcommand: init|ingest|sync|query|update|lint|stats]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, WebSearch, WebFetch, mcp__codex__codex, mcp__codex__codex-reply
---

# ARIS Alias: aris-research-wiki

This project-local skill is an alias for upstream ARIS skill `research-wiki`.

Before doing any task for this skill:

1. Read `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/research-wiki/SKILL.md`.
2. Follow that source skill exactly; treat the source file as authoritative.
3. If the source skill refers to another ARIS slash command such as `/foo`, use this project's aliased form `/aris-foo` when invoking slash commands.
4. If the source skill refers to `~/.claude/skills/foo` or `.claude/skills/foo`, resolve that ARIS skill to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/foo` or `.claude/skills/aris-foo`.
5. For support references such as `../shared-references/...`, read them from `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/shared-references` when needed.

Do not edit this generated alias. Re-run `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh` to refresh it.
