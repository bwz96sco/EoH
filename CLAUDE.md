# Claude Compatibility

Canonical project instructions live in `AGENTS.md`.

For Claude Code in this repository:
- repo-local runtime behavior is driven by `.claude/settings.json` and `.claude/hooks/`
- Trellis workflow/context comes from `.trellis/`
- GitNexus may update the managed block below during `npx gitnexus analyze`

Read `AGENTS.md` first, then use this file only for Claude-specific compatibility.
<!-- ARIS:BEGIN -->
## ARIS Skill Scope
ARIS skills installed in this project: 68 entries.
Manifest: `.aris/installed-skills.txt` (lists every skill ARIS installed and its upstream target).
Project-local aliases use the form `.claude/skills/aris-<skill>` (for example `.claude/skills/aris-research-pipeline`).
For ARIS workflows, prefer the project-local aliased skills under `.claude/skills/` over global skills.
Do not modify or delete files inside ARIS-managed aliases; generated wrappers live under `.aris/skill-aliases/` and point back to `/Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep`.
Update with: `bash /Users/zhangbowen/Projects/NewTools-Research/Auto-claude-code-research-in-sleep/tools/install_aris.sh`  (re-runnable; reconciles new/removed skills).
<!-- ARIS:END -->