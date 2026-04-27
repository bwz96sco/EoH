---
name: aris-citation-audit
description: "Zero-context verification that every bibliographic entry in the paper is real, correctly attributed, and used in a context the cited paper actually supports. Uses a fresh cross-model reviewer with web/DBLP/arXiv lookup to catch hallucinated authors, wrong years, fabricated venues, version mismatches, and wrong-context citations (cite present but the cited paper does not establish the claim). Use when user says \"审查引用\", \"check citations\", \"citation audit\", \"verify references\", \"引用核对\", or before submission to ensure bibliography integrity."
argument-hint: [paper-directory-or-bib-file]
allowed-tools: Bash(*), Read, Grep, Glob, Edit, Write, Agent, mcp__codex__codex, WebSearch, WebFetch
---

# ARIS Alias: aris-citation-audit

This project-local skill is an alias for upstream ARIS skill `citation-audit`.

Before doing any task for this skill:

1. Read `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/citation-audit/SKILL.md`.
2. Follow that source skill exactly; treat the source file as authoritative.
3. If the source skill refers to another ARIS slash command such as `/foo`, use this project's aliased form `/aris-foo` when invoking slash commands.
4. If the source skill refers to `~/.claude/skills/foo` or `.claude/skills/foo`, resolve that ARIS skill to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/foo` or `.claude/skills/aris-foo`.
5. For support references such as `../shared-references/...`, read them from `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/skills/shared-references` when needed.

Do not edit this generated alias. Re-run `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh` to refresh it.
