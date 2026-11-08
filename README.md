# YouTube Niche Finder

A Claude Code pack that scans YouTube and helps you **decide a channel niche**,
producing for each candidate:

- **Niche type** (education, explainer, storytelling, self-improvement, …)
- **Niche name** — specific, not a broad category
- **Description** and **channel promise**
- **Language** (and region)
- **Video types** — long-form / Shorts / live / podcast, style, length, series, cadence
- **Keywords** — each tied to a source (scan, vidIQ, comments)

Decisions follow the 10-criterion framework in [`docs/framework.md`](docs/framework.md):
demonstrated demand, realistic earning routes and your ability to produce
original content consistently. A decision aid, not a validated model or an
earnings forecast.

## How it decides

1. **Gates.** Original contribution, production economics and monetization &
   rights must each score ≥ 3/5. Failing niches are not ranked.
2. **Rank eligible niches** by demand + new-channel opportunity + original
   contribution, then by the overall 10-criterion mean.
3. **Evidence rule.** Any score ≥ 3 must cite a URL or a saved scan.
4. **Scan checks** flag single-channel "demand", breakout-skewed samples,
   too few channels and too few months of uploads.
5. **Economics** use RPM scenarios: profit = YouTube revenue + external
   revenue − operating costs.
6. **20 distinct ideas** per niche; near-duplicates are flagged (inauthentic /
   mass-produced content risk for faceless AI-assisted channels).
7. **You choose.** The report recommends; selection is recorded only when you say so.

## Setup (WSL/Ubuntu)

```bash
git clone https://github.com/liosvee/youtube-niche-finder && cd youtube-niche-finder
cp .env.example .env              # optional: YOUTUBE_API_KEY for direct scans
cp MASTER_CONTEXT.template.md MASTER_CONTEXT.md   # your constraints
claude                            # vidIQ MCP is configured in .mcp.json
```

Then tell Claude: **"Find a niche"**.

## Commands

```bash
python -m niche_finder init PROJECT
python -m niche_finder add PROJECT niche-id
python -m niche_finder scan PROJECT niche-id --query "..." --language en --region US --days 180
python -m niche_finder import PROJECT niche-id vidiq-results.json --source vidIQ
python -m niche_finder validate PROJECT [--strict]
python -m niche_finder decide PROJECT        # writes projects/PROJECT/decision.md
python -m niche_finder select PROJECT niche-id
python -m niche_finder criteria
python -m unittest discover -s tests -v
```

`scan` uses ~200–400 YouTube API quota units per query (10,000/day default).
Import format: [`docs/import-format.md`](docs/import-format.md).

## Layout

```
niche_finder/   core (schema, criteria, validation) · youtube (API) · analysis (scan metrics) · decide (gates, rank, economics, report)
prompts/        01-shortlist → 02-scan → 03-assess → 04-ideas-economics → 05-decide → 06-pilot
templates/      niches.json schema
docs/           framework, sources, import format
.claude/skills/niche-finder/SKILL.md
```

`projects/` and `.env` are git-ignored.
