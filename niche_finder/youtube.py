"""YouTube Data API v3 collection. Public metadata only.

Quota (default 10,000 units/day): search.list = 100 units per call;
videos.list and channels.list = 1 unit per call. `scan` prints its cost.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from .core import required


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class YouTube:
    ENDPOINTS = ('search', 'videos', 'channels')

    def __init__(self, key=None):
        self.key = key or os.environ.get('YOUTUBE_API_KEY')
        if not self.key:
            raise ValueError('Set YOUTUBE_API_KEY in .env (YouTube Data API v3), '
                             'or use vidIQ and `import` instead.')
        self.opener = urllib.request.build_opener(NoRedirect())
        self.units = 0

    def get(self, endpoint, params):
        if endpoint not in self.ENDPOINTS:
            raise ValueError('Unsupported endpoint.')
        self.units += 100 if endpoint == 'search' else 1
        url = 'https://www.googleapis.com/youtube/v3/' + endpoint + '?' + urllib.parse.urlencode(params)
        # Key in a header so it never appears in a logged URL.
        request = urllib.request.Request(url, headers={'X-Goog-Api-Key': self.key})
        try:
            with self.opener.open(request, timeout=45) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f'YouTube HTTP {exc.code}. Check API enablement, key restrictions and quota.') from None
        except (urllib.error.URLError, OSError):
            raise RuntimeError('YouTube request failed. No credentials or error body logged.') from None


def seconds(iso):
    match = re.fullmatch(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?', iso or '')
    if not match or not any(match.groups()):
        return None
    d, h, m, s = (float(x or 0) for x in match.groups())
    return 86400 * d + 3600 * h + 60 * m + s


def collect(client, query, language='en', region=None, days=180, pages=1, duration='any', clock=None):
    """Search by views and by date (two orders widen the sample), then hydrate
    videos and channels. Returns rows in the shared import format."""
    required(query, 'query')
    if not 7 <= days <= 3650 or not 1 <= pages <= 5:
        raise ValueError('Use days 7–3650 and pages 1–5.')
    if duration not in ('any', 'short', 'medium', 'long'):
        raise ValueError('duration: any, short, medium or long.')
    instant = clock or datetime.now(timezone.utc)
    after = (instant - timedelta(days=days)).isoformat().replace('+00:00', 'Z')
    ids, seen = [], set()
    for order in ('viewCount', 'date'):
        token = None
        for _ in range(pages):
            params = dict(part='snippet', type='video', q=query, order=order, publishedAfter=after,
                          maxResults=50, relevanceLanguage=language.split('-')[0], videoDuration=duration)
            if region:
                params['regionCode'] = region
            if token:
                params['pageToken'] = token
            response = client.get('search', params)
            for item in response.get('items', []):
                vid = item.get('id', {}).get('videoId')
                if vid and vid not in seen:
                    seen.add(vid)
                    ids.append(vid)
            token = response.get('nextPageToken')
            if not token:
                break
    videos = []
    for i in range(0, len(ids), 50):
        response = client.get('videos', {'part': 'snippet,contentDetails,statistics', 'id': ','.join(ids[i:i + 50])})
        videos += response.get('items', [])
    channel_ids = sorted({v['snippet']['channelId'] for v in videos})
    subs = {}
    for i in range(0, len(channel_ids), 50):
        response = client.get('channels', {'part': 'statistics', 'id': ','.join(channel_ids[i:i + 50])})
        for ch in response.get('items', []):
            st = ch.get('statistics', {})
            subs[ch['id']] = None if st.get('hiddenSubscriberCount') else _int(st.get('subscriberCount'))
    rows = []
    for v in videos:
        sn, st = v['snippet'], v.get('statistics', {})
        rows.append({
            'id': v['id'],
            'url': 'https://www.youtube.com/watch?v=' + v['id'],
            'title': sn.get('title', ''),
            'channel_id': sn.get('channelId'),
            'channel_title': sn.get('channelTitle'),
            'channel_subscribers': subs.get(sn.get('channelId')),
            'published_at': sn.get('publishedAt'),
            'duration_seconds': seconds(v.get('contentDetails', {}).get('duration')),
            'views': _int(st.get('viewCount')),
            'comments': _int(st.get('commentCount')),
            'tags': sn.get('tags', [])[:30],
            'language': sn.get('defaultAudioLanguage') or sn.get('defaultLanguage'),
        })
    return rows


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
