---
name: aris-experiment-audit
description: "Audit experiment integrity before claiming results. Uses cross-model review (GPT-5.4) to check for fake ground truth, score normalization fraud, phantom results, and insufficient scope. Use when user says \"审计实验\", \"check experiment integrity\", \"audit results\", \"实验诚实度\", or after experiments complete before writing claims."
argument-hint: [experiment-dir-or-results-path]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Agent, mcp__codex__codex, mcp__codex__codex-reply
---

# ARIS Alias: aris-experiment-audit

This project-local skill is an alias for upstream ARIS skill `experiment-audit`.

Before doing any task for this skill:

1. Read `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/experiment-audit/SKILL.md`.
2. Follow that source skill exactly; treat the source file as authoritative.
3. If the source skill refers to another ARIS slash command such as `/foo`, use this project's aliased form `/aris-foo` when invoking slash commands.
4. If the source skill refers to `~/.claude/skills/foo` or `.claude/skills/foo`, resolve that ARIS skill to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/foo` or `.claude/skills/aris-foo`.
5. For support references such as `../shared-references/...`, read them from `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/shared-references` when needed.

Do not edit this generated alias. Re-run `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh` to refresh it.
