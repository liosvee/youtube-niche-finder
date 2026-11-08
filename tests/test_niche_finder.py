import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from niche_finder import analysis, core, decide
from niche_finder.__main__ import main
from niche_finder.youtube import seconds, collect

ROOT = Path(__file__).resolve().parent.parent
CLOCK = datetime(2026, 11, 1, tzinfo=timezone.utc)
EV = [{'url': 'https://example.com/evidence', 'accessed_on': '2026-11-01', 'supports': 'example'}]


def niche(nid, scores, ideas=None):
    n = core.blank_niche(nid)
    n.update(niche_type='education', niche_name=nid.title(), description='d', channel_promise='p',
             audience='a', language='en')
    n['video_types'] = [{'format': 'long-form', 'style': 'screen demo'}]
    n['keywords'] = [{'term': f'k{i}', 'source': 'scan', 'evidence': 'x'} for i in range(5)]
    for key, s in zip(core.CRITERIA_KEYS, scores):
        n['criteria'][key] = {'score': s, 'rationale': 'r', 'evidence': EV if s >= 3 else []}
    n['ideas'] = ideas or [f'Idea number {i} about topic{i} subject{i}' for i in range(20)]
    return n


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.rows = json.loads((ROOT / 'examples' / 'import.example.json').read_text())['rows']

    def test_summary_and_formats(self):
        r = analysis.analyze(self.rows, CLOCK)
        self.assertEqual(r['overall']['videos'], 30)
        self.assertEqual(r['overall']['channels'], 8)
        self.assertIsNotNone(r['by_format']['shorts'])
        self.assertIsNotNone(r['by_format']['long-form'])
        self.assertTrue(r['keyword_candidates'])
        self.assertTrue(all(k['channels'] >= 2 for k in r['keyword_candidates']))

    def test_single_channel_concentration_flag(self):
        rows = copy.deepcopy(self.rows)
        rows[0]['views'] = 10 ** 9
        r = analysis.analyze(rows, CLOCK)
        self.assertGreater(r['concentration']['top_channel_view_share'], 0.5)
        self.assertTrue(any('One channel' in f for f in r['flags']))

    def test_bad_rows_skipped(self):
        rows = self.rows + [{'id': 'x'}, dict(self.rows[0])]
        r = analysis.analyze(rows, CLOCK)
        self.assertEqual(r['collected_videos'], 30)
        self.assertTrue(any('skipped' in f for f in r['flags']))

    def test_iso_duration(self):
        self.assertEqual(seconds('PT1M5S'), 65)
        self.assertEqual(seconds('PT2H'), 7200)
        self.assertIsNone(seconds('bad'))


class FakeClient:
    units = 0

    def get(self, endpoint, params):
        if endpoint == 'search':
            return {'items': [{'id': {'videoId': 'v1'}}, {'id': {'videoId': 'v2'}}]}
        if endpoint == 'videos':
            return {'items': [{'id': v, 'snippet': {'title': 't ' + v, 'channelId': 'c1', 'channelTitle': 'C',
                                                     'publishedAt': '2026-10-01T00:00:00Z'},
                               'contentDetails': {'duration': 'PT10M'}, 'statistics': {'viewCount': '100'}}
                              for v in params['id'].split(',')]}
        return {'items': [{'id': 'c1', 'statistics': {'subscriberCount': '500'}}]}


class CollectTests(unittest.TestCase):
    def test_collect_dedupes_and_hydrates(self):
        rows = collect(FakeClient(), 'laptop fix', clock=CLOCK)
        self.assertEqual([r['id'] for r in rows], ['v1', 'v2'])
        self.assertEqual(rows[0]['channel_subscribers'], 500)
        self.assertEqual(rows[0]['duration_seconds'], 600)


class ValidationTests(unittest.TestCase):
    def test_high_score_requires_evidence(self):
        n = niche('alpha', [4] * 10)
        n['criteria']['audience_demand']['evidence'] = []
        self.assertTrue(any('needs at least one evidence' in p for p in core.validate_niche(n)))

    def test_strict_requires_keywords_and_scores(self):
        n = core.blank_niche('beta')
        problems = core.validate_niche(n, strict=True)
        self.assertTrue(any('keywords' in p for p in problems))
        self.assertTrue(any('not scored' in p for p in problems))

    def test_bad_language_and_type(self):
        n = niche('gamma', [3] * 10)
        n['language'] = 'English'
        n['niche_type'] = 'tech'
        problems = core.validate_niche(n)
        self.assertTrue(any('language' in p for p in problems))
        self.assertTrue(any('niche_type' in p for p in problems))


class DecideTests(unittest.TestCase):
    def test_gate_failure_not_ranked_first(self):
        strong_but_unoriginal = niche('viral', [5, 5, 5, 5, 2, 5, 5, 5, 5, 5])
        modest = niche('modest', [3] * 10)
        rows = decide.rank({'niches': [strong_but_unoriginal, modest]})
        self.assertEqual(rows[0]['id'], 'modest')
        self.assertFalse(rows[1]['eligible'])
        self.assertIn('Original contribution', rows[1]['gates_failed'][0])

    def test_choice_strength_orders_eligible(self):
        a = niche('a', [3, 3, 5, 5, 3, 5, 5, 5, 5, 5])   # high overall, weak demand
        b = niche('b', [5, 5, 3, 3, 5, 3, 3, 3, 3, 3])   # strong demand + reason to choose
        rows = decide.rank({'niches': [a, b]})
        self.assertEqual(rows[0]['id'], 'b')

    def test_near_duplicate_ideas(self):
        r = decide.idea_check(['Fix slow laptop fast', 'Fix slow laptop fast today', 'Printer offline guide'])
        self.assertEqual(r['count'], 3)
        self.assertEqual(r['distinct'], 2)

    def test_profit_formula(self):
        n = niche('eco', [3] * 10)
        n['economics'].update(monthly_views={'low': 10000, 'mid': 50000, 'high': None},
                              rpm_usd={'low': 2, 'mid': 4, 'high': 6},
                              external_revenue_usd={'low': 0, 'mid': 50, 'high': 0},
                              costs_usd={'narration': 22, 'editing': 30}, videos_per_month=8)
        e = decide.economics(n)
        self.assertEqual(e['scenarios']['low']['operating_profit_usd'], 20 - 52)
        self.assertEqual(e['scenarios']['mid']['operating_profit_usd'], 200 + 50 - 52)
        self.assertNotIn('high', e['scenarios'])
        self.assertEqual(e['cost_per_video_usd'], 6.5)

    def test_report_contains_profile(self):
        md, _ = decide.report({'niches': [niche('aa', [3] * 10), niche('bb', [4] * 10)]}, 'demo')
        for text in ('Niche type', 'Description', 'Language', 'Video types', 'Keywords', 'Strongest candidate'):
            self.assertIn(text, md)


class CliTests(unittest.TestCase):
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(core, 'PROJECTS', Path(tmp)):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(['init', 'demo']), 0)
                self.assertEqual(main(['add', 'demo', 'pc-fixes']), 0)
                self.assertEqual(main(['import', 'demo', 'pc-fixes', str(ROOT / 'examples' / 'import.example.json')]), 0)
                self.assertEqual(main(['decide', 'demo']), 1)  # not filled yet
            path = Path(tmp) / 'demo' / 'niches.json'
            data = json.loads(path.read_text())
            data['niches'] = [niche('pc-fixes', [4, 3, 3, 4, 3, 4, 4, 3, 3, 4]), niche('sleep-stories', [3] * 10)]
            path.write_text(json.dumps(data))
            with redirect_stdout(out):
                self.assertEqual(main(['decide', 'demo']), 0)
                self.assertEqual(main(['select', 'demo', 'pc-fixes']), 0)
            self.assertTrue((Path(tmp) / 'demo' / 'decision.md').exists())
            self.assertEqual(len(list((Path(tmp) / 'demo' / 'scans').glob('*.json'))), 2)
            self.assertEqual(json.loads(path.read_text())['decision']['selected'], 'pc-fixes')


if __name__ == '__main__':
    unittest.main()
