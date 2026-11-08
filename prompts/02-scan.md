# Step 2 — Scan YouTube for each candidate

For each niche, run 2–4 queries that a real viewer would type (in the niche's
language), using one or both routes:

**A. YouTube Data API** (if `YOUTUBE_API_KEY` is set):
`python -m niche_finder scan PROJECT niche-id --query "..." --language en --region US --days 180`
Each call costs ~200–400 quota units of 10,000/day; the command prints usage.

**B. vidIQ** (via `.mcp.json`): `vidiq_youtube_search`, `vidiq_outliers`,
`vidiq_keyword_research`, `vidiq_channel_search`, `vidiq_similar_channels`.
Save the video results in the import format (`docs/import-format.md`) under
`projects/PROJECT/scans/` and run
`python -m niche_finder import PROJECT niche-id FILE --source vidIQ --label query-slug`.

Then, for every niche:
- Read the scan output: multi-channel demand, median vs p90 (typical vs
  breakout), views/day by age bucket, Shorts vs long-form, top-channel
  concentration, small channels at/above median, outliers, upload-month spread
  and every **flag**.
- Compare like with like: same format, similar age.
- Read comments on 3–5 representative videos (`vidiq_comment_insights` or
  `vidiq_video_comments`) for recurring, unanswered questions.
- Use `vidiq_keyword_research` for search volume/competition. Keep YouTube and
  Google data separate; never invent volumes.
- Build `keywords` (≥ 5 per niche): each with `term`, `source` (scan file,
  vidIQ, comments) and `evidence` (e.g. "used by 9 channels in scan").
