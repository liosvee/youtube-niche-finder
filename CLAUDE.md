# YouTube Niche Finder

Read AGENTS.md, MASTER_CONTEXT.md if present, and docs/framework.md. You are
the research agent; Python validates, analyses scans, ranks and writes the
report. This project runs no separate LLM service.

When the user says "Find a niche" (or similar), use the `niche-finder` skill:
prompts/01-shortlist.md → 02-scan.md → 03-assess.md → 04-ideas-economics.md →
05-decide.md. Stop for the user's choice. After they choose, record it with
`select` and continue with prompts/06-pilot.md when they're ready.

The decision output for each niche is: **niche type, niche name,
description, language, video types and keywords**, backed by the 10
criteria, scans and scenario economics.

For "resume", inspect `projects/*/niches.json`, `scans/` and `decision.md`
before deciding the next step. Reuse saved scans; never repeat paid vidIQ
calls without asking. Never replace the user's niche choice with your own.
