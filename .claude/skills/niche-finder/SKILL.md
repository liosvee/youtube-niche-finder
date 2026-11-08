---
name: niche-finder
description: Scan YouTube and decide a channel niche — type, name, description, language, video types and keywords — using the 10-criterion framework in docs/framework.md. Use when the user asks to find, choose, compare or validate a YouTube niche.
---

# Niche finder

Run from the repository root. Follow, in order:

1. `prompts/01-shortlist.md` — constraints + 3 candidate niches with full profiles
2. `prompts/02-scan.md` — YouTube Data API and/or vidIQ scans, comments, keywords
3. `prompts/03-assess.md` — score the 10 criteria with evidence
4. `prompts/04-ideas-economics.md` — 20 distinct ideas, revenue routes, cost/RPM scenarios
5. `prompts/05-decide.md` — `python -m niche_finder decide`, present, **user chooses**
6. `prompts/06-pilot.md` — after selection: pilot batch, then re-score

Hard rules: gates (original contribution, production economics, monetization &
rights) must be ≥ 3; scores ≥ 3 need evidence; RPM not CPM; scenarios are
labelled assumptions; never choose for the user; never promise earnings.
Resume from saved files — don't repeat paid vidIQ calls.
