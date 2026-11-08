"""Turn a sample of videos into demand / opportunity / keyword evidence.

These are observations about a search sample, not a census of YouTube and not
revenue. Every figure is stamped with the sample size and collection date.
"""
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone

SHORTS_MAX_SECONDS = 180
SMALL_CHANNEL_SUBS = 10_000
AGE_BUCKETS = [(0, 30), (31, 90), (91, 365), (366, 100_000)]
STOPWORDS = set('''
a an the and or but of to in on for with at by from as is are was were be been it its this that these those
you your yours i me my we our they their he she his her them how what why when where who which vs vs.
do does did not no yes can will just so if than then too very more most all any some new best top
shorts short video videos official full part ep episode 2023 2024 2025 2026
'''.split())
REQUIRED = ('id', 'title', 'channel_id', 'published_at', 'views')


def from_vidiq(raw):
    """Accept vidIQ `vidiq_youtube_search` output as saved by an MCP client:
    either the tool's JSON ({"results": [...]}) or the client wrapper
    ([{"type": "text", "text": "<that JSON>"}]). Returns rows or None."""
    import json
    from .youtube import seconds
    if isinstance(raw, list) and raw and isinstance(raw[0], dict) and raw[0].get('type') == 'text':
        try:
            raw = json.loads(raw[0]['text'])
        except (ValueError, KeyError):
            return None
    if not isinstance(raw, dict) or not isinstance(raw.get('results'), list):
        return None
    rows = []
    for v in raw['results']:
        if v.get('kind', 'video') != 'video':
            continue
        rows.append({
            'id': v.get('id'), 'url': f"https://www.youtube.com/watch?v={v.get('id')}",
            'title': v.get('title'), 'channel_id': v.get('channelId'), 'channel_title': v.get('channelTitle'),
            'channel_subscribers': v.get('subscriberCount'), 'published_at': v.get('publishedAt'),
            'duration_seconds': seconds(v.get('duration')), 'views': v.get('viewCount'),
            'comments': v.get('commentCount'), 'tags': [],
        })
    return rows


def normalise(rows):
    """Validate imported rows (from the API, vidIQ or a manual export)."""
    clean, skipped = [], 0
    seen = set()
    for r in rows:
        if not all(r.get(k) not in (None, '') for k in REQUIRED) or r['id'] in seen:
            skipped += 1
            continue
        try:
            views = int(r['views'])
            published = _parse_time(r['published_at'])
        except (TypeError, ValueError):
            skipped += 1
            continue
        seen.add(r['id'])
        row = dict(r)
        row['views'] = views
        row['published_at'] = published.isoformat().replace('+00:00', 'Z')
        clean.append(row)
    return clean, skipped


def _parse_time(value):
    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _median(xs):
    return round(statistics.median(xs), 1) if xs else None


def _pct(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (k - lo), 1)


def tokens(text):
    words = [w.lower() for w in re.findall(r'[^\W\d_][\w\'’-]*', text or '', re.UNICODE)]
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def keyword_candidates(rows, limit=25):
    """Terms and two-word phrases ranked by how many *distinct channels* use
    them in titles/tags — one channel repeating itself is not demand."""
    by_term = defaultdict(set)
    views = Counter()
    for r in rows:
        words = tokens(r.get('title'))
        grams = set(words) | {' '.join(p) for p in zip(words, words[1:])}
        grams |= {t.lower().strip() for t in r.get('tags') or [] if 2 < len(t) < 40}
        for g in grams:
            by_term[g].add(r['channel_id'])
            views[g] += r['views']
    ranked = sorted(by_term, key=lambda g: (len(by_term[g]), views[g]), reverse=True)
    out = []
    for g in ranked:
        if len(by_term[g]) < 2:
            break
        out.append({'term': g, 'channels': len(by_term[g]), 'sample_views': views[g]})
        if len(out) >= limit:
            break
    return out


def _summary(rows, clock):
    views = [r['views'] for r in rows]
    vpd = []
    buckets = {f'{a}-{b}d' if b < 100_000 else f'{a}d+': [] for a, b in AGE_BUCKETS}
    for r in rows:
        age = max((clock - _parse_time(r['published_at'])).total_seconds() / 86400, 1)
        vpd.append(r['views'] / age)
        for (a, b), key in zip(AGE_BUCKETS, buckets):
            if a <= age <= b:
                buckets[key].append(r['views'])
    med, p90 = _median(views), _pct(views, 0.9)
    return {
        'videos': len(rows),
        'channels': len({r['channel_id'] for r in rows}),
        'median_views': med,
        'p90_views': p90,
        'breakout_ratio_p90_to_median': round(p90 / med, 1) if med else None,
        'median_views_per_day': _median(vpd),
        'median_views_by_age': {k: {'n': len(v), 'median': _median(v)} for k, v in buckets.items()},
    }


def analyze(rows, clock=None):
    clock = clock or datetime.now(timezone.utc)
    rows, skipped = normalise(rows)
    if not rows:
        raise ValueError('No usable rows (need id, title, channel_id, published_at, views).')
    shorts = [r for r in rows if r.get('duration_seconds') and r['duration_seconds'] <= SHORTS_MAX_SECONDS]
    longs = [r for r in rows if r.get('duration_seconds') and r['duration_seconds'] > SHORTS_MAX_SECONDS]
    overall = _summary(rows, clock)
    median_all = overall['median_views'] or 0

    # Concentration: is "demand" really one viral channel?
    by_channel = Counter()
    for r in rows:
        by_channel[r['channel_id']] += r['views']
    total = sum(by_channel.values()) or 1
    top_channel_share = round(max(by_channel.values()) / total, 3)
    top3_share = round(sum(v for _, v in by_channel.most_common(3)) / total, 3)

    # Smaller channels that reach typical-or-better results.
    small = {r['channel_id'] for r in rows
             if r.get('channel_subscribers') is not None and r['channel_subscribers'] < SMALL_CHANNEL_SUBS}
    small_hits = {r['channel_id'] for r in rows if r['channel_id'] in small and r['views'] >= median_all}
    known_subs = sum(1 for r in rows if r.get('channel_subscribers') is not None)

    # Outliers: views far above channel size (only where subscribers are known).
    outliers = []
    for r in rows:
        s = r.get('channel_subscribers')
        if s and r['views'] >= 3 * s and r['views'] >= median_all:
            outliers.append({'title': r['title'], 'url': r.get('url'), 'views': r['views'],
                             'subscribers': s, 'views_to_subs': round(r['views'] / s, 1)})
    outliers.sort(key=lambda o: o['views_to_subs'], reverse=True)

    months = sorted({r['published_at'][:7] for r in rows})
    comments = [r['comments'] for r in rows if r.get('comments') is not None]
    flags = []
    if top_channel_share > 0.5:
        flags.append('One channel holds >50% of sample views: demand may be one creator, not the topic.')
    if overall['breakout_ratio_p90_to_median'] and overall['breakout_ratio_p90_to_median'] > 20:
        flags.append('Top results are >20x the median: judge by typical results, not breakouts.')
    if overall['channels'] < 5:
        flags.append('Fewer than 5 channels in sample: not enough to show sustained, multi-channel demand.')
    if len(months) < 3:
        flags.append('Uploads span <3 months: cannot show sustained interest; check seasonality.')
    if known_subs < len(rows) / 2:
        flags.append('Subscriber counts missing for most rows: small-channel and outlier signals are weak.')
    if skipped:
        flags.append(f'{skipped} rows skipped (missing fields or duplicates).')

    return {
        'collected_videos': len(rows),
        'overall': overall,
        'by_format': {
            'shorts': _summary(shorts, clock) if shorts else None,
            'long-form': _summary(longs, clock) if longs else None,
        },
        'concentration': {'top_channel_view_share': top_channel_share, 'top3_channel_view_share': top3_share},
        'small_channels': {
            'definition': f'< {SMALL_CHANNEL_SUBS:,} subscribers',
            'small_channels_in_sample': len(small),
            'small_channels_at_or_above_median': len(small_hits),
        },
        'outliers_views_ge_3x_subs': outliers[:15],
        'upload_months': months,
        'median_comments': _median(comments),
        'keyword_candidates': keyword_candidates(rows),
        'flags': flags,
    }
