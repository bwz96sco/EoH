---
name: aris-feishu-notify
description: "Send notifications to Feishu/Lark. Internal utility used by other skills, or manually via /feishu-notify. Supports push-only (webhook) and interactive (bidirectional) modes. Use when user says \"发飞书\", \"notify feishu\", or other skills need to send status updates."
argument-hint: [message-text]
allowed-tools: Bash(curl *), Bash(cat *), Read, Glob
---

# ARIS Alias: aris-feishu-notify

This project-local skill is an alias for upstream ARIS skill `feishu-notify`.

Before doing any task for this skill:

1. Read `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/feishu-notify/SKILL.md`.
2. Follow that source skill exactly; treat the source file as authoritative.
3. If the source skill refers to another ARIS slash command such as `/foo`, use this project's aliased form `/aris-foo` when invoking slash commands.
4. If the source skill refers to `~/.claude/skills/foo` or `.claude/skills/foo`, resolve that ARIS skill to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/foo` or `.claude/skills/aris-foo`.
5. For support references such as `../shared-references/...`, read them from `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/shared-references` when needed.

Do not edit this generated alias. Re-run `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh` to refresh it.
