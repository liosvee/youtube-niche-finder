# Import format (vidIQ or any export)

`python -m niche_finder import PROJECT NICHE_ID FILE --source vidIQ`

FILE is a JSON list (or `{"rows": [...]}`) of videos:

| Field | Required | Notes |
|---|---|---|
| id | yes | YouTube video id |
| title | yes | |
| channel_id | yes | Channel id or a stable channel name |
| published_at | yes | ISO date/time |
| views | yes | Integer |
| channel_title | no | |
| channel_subscribers | no | Enables small-channel and outlier signals |
| duration_seconds | no | Enables Shorts vs long-form comparison (≤180 s = Shorts) |
| comments | no | |
| tags | no | List of strings |
| url | no | |

Map vidIQ fields honestly. If vidIQ doesn't return a field, leave it out —
never estimate it. See `examples/import.example.json`.
