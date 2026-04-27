---
name: aris-overleaf-sync
description: "Two-way sync between a local paper directory and an Overleaf project via the Overleaf Git bridge (Premium feature). Lets you keep ARIS audit/edit workflows on the local copy while collaborators edit in the Overleaf web UI. Token never touches the agent — user does the one-time auth via macOS Keychain. Use when user says \"同步 overleaf\", \"overleaf sync\", \"推送到 overleaf\", \"connect overleaf\", \"Overleaf 桥接\", \"pull overleaf\", \"push overleaf\", or wants to bridge their ARIS paper directory with an Overleaf project."
argument-hint: [setup <project-id> | pull | push | status]
allowed-tools: Bash(*), Read, Grep, Glob, Edit, Write
---

# ARIS Alias: aris-overleaf-sync

This project-local skill is an alias for upstream ARIS skill `overleaf-sync`.

Before doing any task for this skill:

1. Read `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/overleaf-sync/SKILL.md`.
2. Follow that source skill exactly; treat the source file as authoritative.
3. If the source skill refers to another ARIS slash command such as `/foo`, use this project's aliased form `/aris-foo` when invoking slash commands.
4. If the source skill refers to `~/.claude/skills/foo` or `.claude/skills/foo`, resolve that ARIS skill to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/foo` or `.claude/skills/aris-foo`.
5. For support references such as `../shared-references/...`, read them from `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/shared-references` when needed.

Do not edit this generated alias. Re-run `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh` to refresh it.
