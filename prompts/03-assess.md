# Step 3 — Score the 10 criteria

For each niche fill `criteria` in `niches.json`. Per criterion:
- `score` integer 0–5 (0 = evidence against, 1–2 = weak/unknown,
  3 = adequate, 4 = strong, 5 = very strong).
- `rationale` — one or two sentences explaining the score.
- `evidence` — list of `{ "url" or "scan", "accessed_on", "supports" }`.
  Scores of 3+ **require** evidence. Opinion alone caps at 2.

Notes per criterion:
- **Demand**: several channels, recent, sustained across months. One viral
  video or a single keyword score is not enough.
- **New-channel opportunity**: small channels at/above median, outliers vs
  subscriber count, unanswered comment questions, language/clarity gaps.
- **Revenue**: name specific affiliate programs, sponsors seen in niche
  videos, products. Existence ≠ earnings.
- **Original contribution ★**: what *this* faceless, AI-assisted channel adds
  that others don't — own research, demonstrations, comparisons, storytelling.
- **Production economics ★**: until a pilot exists, estimate from the user's
  stated tools/time and say so; score ≤ 3 before measured pilot costs.
- **Knowledge/credibility**: sources and a fact-checking process the user can
  actually run.
- **Monetization & rights ★**: original scripts and visuals, licensed media,
  advertiser-friendly topic. Check reused/inauthentic content risk and
  made-for-kids status. Cite `docs/sources.md`.

Run `python -m niche_finder validate PROJECT` and fix every problem.
