# Step 1 — Shortlist three niches

1. Read `docs/framework.md`. Run `python -m niche_finder init PROJECT`
   (default project: `first-niche`). Ask for or confirm `constraints` in
   `niches.json`: faceless, AI-assisted, publishable languages, hours/week,
   monthly budget. Don't re-ask what MASTER_CONTEXT.md already says.
2. If the user gave seed ideas, start from them. If not, run broad discovery:
   vidIQ `vidiq_trend_categories`, `vidiq_trending_videos`, `vidiq_outliers`
   and `vidiq_keyword_research` on 5–8 broad seed topics that fit the
   constraints. Keep discovery cheap; state the vidIQ credit cost before
   larger calls.
3. Pick 3 candidates (up to 5 if the user asks). For each, `python -m
   niche_finder add PROJECT niche-id` and fill the profile:
   - `niche_type` (see `python -m niche_finder criteria`)
   - `niche_name` — a specific name, not a category ("Beginner PC fixes",
     not "Technology")
   - `description` — 1–2 sentences: what the channel covers
   - `channel_promise` — why a viewer picks this channel over others
   - `audience` — who, what problem or interest, what level
   - `language` (+ `region` if it matters)
   - `video_types` — format (long-form/shorts/live/podcast), style, length,
     series, cadence
4. Continue to step 2 without waiting for confirmation unless a constraint is
   unknown and changes the shortlist.
