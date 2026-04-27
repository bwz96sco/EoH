---
name: aris-experiment-queue
description: SSH job queue for multi-seed/multi-config ML experiments with OOM-aware retry, stale-screen cleanup, and wave-transition race prevention. Use when user says "batch experiments", "队列实验", "run grid", "multi-seed sweep", "auto-chain experiments", or when /run-experiment is insufficient for 10+ jobs that need orchestration.
argument-hint: [manifest-or-grid-spec]
allowed-tools: Bash(*), Read, Grep, Glob, Edit, Write, Agent, Skill(run-experiment), Skill(monitor-experiment)
---

# ARIS Alias: aris-experiment-queue

This project-local skill is an alias for upstream ARIS skill `experiment-queue`.

Before doing any task for this skill:

1. Read `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/experiment-queue/SKILL.md`.
2. Follow that source skill exactly; treat the source file as authoritative.
3. If the source skill refers to another ARIS slash command such as `/foo`, use this project's aliased form `/aris-foo` when invoking slash commands.
4. If the source skill refers to `~/.claude/skills/foo` or `.claude/skills/foo`, resolve that ARIS skill to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/foo` or `.claude/skills/aris-foo`.
5. For support references such as `../shared-references/...`, read them from `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/shared-references` when needed.

Do not edit this generated alias. Re-run `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh` to refresh it.
