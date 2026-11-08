"""python -m niche_finder <command> ...  (run from the repository root)"""
import argparse
import json
import os
import sys
from pathlib import Path

from . import analysis, decide
from .core import CRITERIA, NICHE_TYPES, blank_niche, init_project, load, now, project_dir, save, validate


def _load_env():
    env = Path(__file__).resolve().parent.parent / '.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))


def _niches_path(project):
    path = project_dir(project) / 'niches.json'
    if not path.exists():
        sys.exit(f'No project "{project}". Run: python -m niche_finder init {project}')
    return path


def _write_scan(project, niche_id, label, rows, meta):
    result = analysis.analyze(rows)
    stamp = now().replace(':', '').replace('-', '')
    base = project_dir(project) / 'scans' / f'{niche_id}-{label}-{stamp}'
    save(base.with_suffix('.raw.json'), {'meta': meta, 'rows': rows})
    save(base.with_suffix('.json'), {'meta': meta, 'analysis': result})
    o = result['overall']
    print(f"Scan saved: {base.with_suffix('.json').relative_to(project_dir(project).parent.parent)}")
    print(f"  {o['videos']} videos / {o['channels']} channels · median views {o['median_views']} · "
          f"p90 {o['p90_views']} · median views/day {o['median_views_per_day']}")
    print(f"  top-channel view share {result['concentration']['top_channel_view_share']} · small channels ≥ median: "
          f"{result['small_channels']['small_channels_at_or_above_median']}")
    print('  keyword candidates: ' + ', '.join(k['term'] for k in result['keyword_candidates'][:12]))
    for f in result['flags']:
        print('  ! ' + f)


def main(argv=None):
    _load_env()
    ap = argparse.ArgumentParser(prog='niche_finder')
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('init'); s.add_argument('project')
    s = sub.add_parser('add'); s.add_argument('project'); s.add_argument('niche_id')
    s = sub.add_parser('scan', help='YouTube Data API sample (needs YOUTUBE_API_KEY)')
    s.add_argument('project'); s.add_argument('niche_id'); s.add_argument('--query', required=True)
    s.add_argument('--language', default='en'); s.add_argument('--region')
    s.add_argument('--days', type=int, default=180); s.add_argument('--pages', type=int, default=1)
    s.add_argument('--duration', default='any', choices=['any', 'short', 'medium', 'long'])
    s = sub.add_parser('import', help='Analyze rows from vidIQ or an export (JSON list or {"rows": [...]})')
    s.add_argument('project'); s.add_argument('niche_id'); s.add_argument('file')
    s.add_argument('--label', default='import'); s.add_argument('--source', default='vidIQ')
    s = sub.add_parser('validate'); s.add_argument('project'); s.add_argument('--strict', action='store_true')
    s = sub.add_parser('decide'); s.add_argument('project')
    s = sub.add_parser('select'); s.add_argument('project'); s.add_argument('niche_id'); s.add_argument('--note', default='')
    sub.add_parser('criteria')
    a = ap.parse_args(argv)

    if a.cmd == 'criteria':
        for key, label, gate, ev in CRITERIA:
            print(f"{'★' if gate else ' '} {key:26} {label}: {ev}")
        print('\nNiche types: ' + ', '.join(NICHE_TYPES))
        return 0
    if a.cmd == 'init':
        path, created = init_project(a.project)
        print(('Created ' if created else 'Exists: ') + str(path))
        return 0

    path = _niches_path(a.project)
    data = load(path)
    if a.cmd == 'add':
        if any(n.get('id') == a.niche_id for n in data['niches']):
            sys.exit('That id already exists.')
        data['niches'] = [n for n in data['niches'] if n.get('id') != 'replace-with-niche-id']
        data['niches'].append(blank_niche(a.niche_id))
        save(path, data)
        print(f'Added {a.niche_id}. Fill it in {path}.')
    elif a.cmd == 'scan':
        from .youtube import YouTube, collect
        client = YouTube()
        rows = collect(client, a.query, a.language, a.region, a.days, a.pages, a.duration)
        meta = {'source': 'YouTube Data API v3', 'query': a.query, 'language': a.language, 'region': a.region,
                'days': a.days, 'collected_at': now(), 'quota_units': client.units,
                'note': 'Search sample, not exhaustive.'}
        print(f'Quota used: {client.units} units.')
        _write_scan(a.project, a.niche_id, 'api', rows, meta)
    elif a.cmd == 'import':
        raw = load(a.file)
        rows = analysis.from_vidiq(raw)
        if rows is None:
            rows = raw.get('rows', raw.get('videos')) if isinstance(raw, dict) else raw
        if not isinstance(rows, list):
            sys.exit('Expected a JSON list of videos or {"rows": [...]}.')
        meta = {'source': a.source, 'file': os.path.basename(a.file), 'collected_at': now(),
                'note': 'Imported sample, not exhaustive.'}
        _write_scan(a.project, a.niche_id, a.label, rows, meta)
    elif a.cmd == 'validate':
        problems = validate(data, strict=a.strict)
        print('\n'.join(problems) if problems else 'OK')
        return 1 if problems else 0
    elif a.cmd == 'decide':
        problems = validate(data, strict=True)
        if problems:
            print('Not ready for a decision:\n' + '\n'.join(problems))
            return 1
        md, rows = decide.report(data, a.project)
        out = project_dir(a.project)
        (out / 'decision.md').write_text(md, encoding='utf-8')
        save(out / 'decision.json', [{k: v for k, v in r.items() if k != 'niche'} for r in rows])
        print(md)
        print(f'Saved {out / "decision.md"}')
    elif a.cmd == 'select':
        if not any(n.get('id') == a.niche_id for n in data['niches']):
            sys.exit('Unknown niche id.')
        data['decision'] = {'selected': a.niche_id, 'selected_at': now(), 'note': a.note}
        save(path, data)
        print(f'Recorded your selection: {a.niche_id}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
