---
name: aris-system-profile
description: Profile a target (script, process, GPU, memory, interconnect) using external tools and code instrumentation. Produces structured performance reports with actionable recommendations. Use when user says "profile", "benchmark", "bottleneck", or wants performance analysis.
argument-hint: <target, e.g. "train.py", "gpu", "pid 1234", "vllm serving">
---

# ARIS Alias: aris-system-profile

This project-local skill is an alias for upstream ARIS skill `system-profile`.

Before doing any task for this skill:

1. Read `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/system-profile/SKILL.md`.
2. Follow that source skill exactly; treat the source file as authoritative.
3. If the source skill refers to another ARIS slash command such as `/foo`, use this project's aliased form `/aris-foo` when invoking slash commands.
4. If the source skill refers to `~/.claude/skills/foo` or `.claude/skills/foo`, resolve that ARIS skill to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/foo` or `.claude/skills/aris-foo`.
5. For support references such as `../shared-references/...`, read them from `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/shared-references` when needed.

Do not edit this generated alias. Re-run `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh` to refresh it.
