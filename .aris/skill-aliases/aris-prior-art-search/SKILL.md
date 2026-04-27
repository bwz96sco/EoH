---
name: aris-prior-art-search
description: "Search patent databases and academic literature for prior art relevant to an invention. Use when user says \"现有技术检索\", \"prior art search\", \"专利检索\", \"check patents\", or wants to find relevant prior art."
argument-hint: [invention-description-or-path]
allowed-tools: Bash(*), Read, Glob, Grep, WebSearch, WebFetch, Write, Agent
---

# ARIS Alias: aris-prior-art-search

This project-local skill is an alias for upstream ARIS skill `prior-art-search`.

Before doing any task for this skill:

1. Read `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/prior-art-search/SKILL.md`.
2. Follow that source skill exactly; treat the source file as authoritative.
3. If the source skill refers to another ARIS slash command such as `/foo`, use this project's aliased form `/aris-foo` when invoking slash commands.
4. If the source skill refers to `~/.claude/skills/foo` or `.claude/skills/foo`, resolve that ARIS skill to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/foo` or `.claude/skills/aris-foo`.
5. For support references such as `../shared-references/...`, read them from `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/shared-references` when needed.

Do not edit this generated alias. Re-run `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh` to refresh it.
