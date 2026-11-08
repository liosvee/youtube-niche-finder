"""Project files, the niche schema and validation. Standard library only."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / 'projects'

# The 10 criteria from docs/framework.md. `gate=True` marks the framework's
# minimum requirements: policy/rights compliance, originality and affordable
# production. A niche that fails any gate is not ranked, whatever its demand.
CRITERIA = [
    ('audience_demand', 'Audience demand', False,
     'Recent videos attracting views across several channels, recurring questions, search interest over time.'),
    ('new_channel_opportunity', 'Opportunity for a new channel', False,
     'Smaller channels gaining traction repeatedly; unanswered questions; gaps in clarity, language, demos or coverage.'),
    ('revenue_opportunities', 'Revenue opportunities', False,
     'Affiliate programs, active sponsors, fitting products/services. Existence does not establish earnings.'),
    ('audience_specificity', 'Audience specificity', False,
     'A defined audience, language, recurring problem or entertainment interest.'),
    ('original_contribution', 'Original contribution', True,
     'Own demonstrations, research, explanations, comparisons, interviews or storytelling.'),
    ('content_depth', 'Content depth', False,
     'A topic map with multiple series and follow-up questions, not repeats of one idea.'),
    ('return_viewing', 'Return-viewing potential', False,
     'Connected lessons, recurring formats, character-driven stories, related problems.'),
    ('production_economics', 'Production economics', True,
     'Measured research, scripting, narration, editing, licensing and revision costs from pilot videos.'),
    ('knowledge_credibility', 'Knowledge and credibility', False,
     'Relevant experience, dependable sources, expert access, a fact-checking process.'),
    ('monetization_rights', 'Monetization and rights suitability', True,
     'Original scripts and visuals, documented permissions, advertiser-suitable content.'),
]
CRITERIA_KEYS = [c[0] for c in CRITERIA]
GATES = [c[0] for c in CRITERIA if c[2]]
GATE_MIN = 3
# A score at or above this needs at least one evidence entry. Opinion alone
# can only say "weak/unknown".
EVIDENCE_REQUIRED_FROM = 3

NICHE_TYPES = {
    'education': 'Tutorials, how-to, lessons, troubleshooting',
    'explainer': 'Explainers, documentaries, deep dives',
    'storytelling': 'Narrated stories, history, true events, fiction series',
    'commentary': 'Analysis, opinion, essays on a subject',
    'reviews': 'Reviews, comparisons, buying guides',
    'self-improvement': 'Motivation, psychology, productivity, relationships',
    'news': 'Updates and recaps in a defined field',
    'entertainment': 'Compilations, rankings, quizzes, facts (reused-content risk: check policy)',
    'ambient': 'Music, relaxation, sleep, study background',
    'kids': 'Made-for-kids content (COPPA limits: personalised ads and comments off)',
    'other': 'Explain in description',
}
VIDEO_FORMATS = {'long-form', 'shorts', 'live', 'podcast'}
LANG_RE = re.compile(r'^[a-z]{2,3}(-[A-Za-z]{2,4})?$')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def required(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} is required.')
    return value.strip()


def project_dir(name):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', name or ''):
        raise ValueError('Project names: letters, digits, - and _ only.')
    return PROJECTS / name


def load(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write('\n')
    tmp.replace(path)


def blank_niche(niche_id):
    template = load(ROOT / 'templates' / 'niches.json')['niches'][0]
    template = json.loads(json.dumps(template))
    template['id'] = niche_id
    return template


def init_project(name, root=None):
    base = Path(root) / name if root else project_dir(name)
    target = base / 'niches.json'
    if target.exists():
        return target, False
    data = load(ROOT / 'templates' / 'niches.json')
    data['created_at'] = now()
    save(target, data)
    (base / 'scans').mkdir(parents=True, exist_ok=True)
    return target, True


def validate_niche(niche, strict=False):
    """Return a list of problems. strict=True is used before a decision."""
    problems = []
    nid = niche.get('id') or '?'
    p = lambda msg: problems.append(f'[{nid}] {msg}')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,48}', niche.get('id') or ''):
        p('id must be lowercase-kebab (2–49 chars).')
    if niche.get('niche_type') not in NICHE_TYPES:
        p(f'niche_type must be one of: {", ".join(NICHE_TYPES)}.')
    for field in ('niche_name', 'description', 'audience', 'channel_promise'):
        if strict and not str(niche.get(field) or '').strip():
            p(f'{field} is empty.')
    lang = niche.get('language') or ''
    if not LANG_RE.match(lang):
        p('language must be a code like "en", "ja", "ko", "fj" or "en-US".')
    vts = niche.get('video_types') or []
    if strict and not vts:
        p('video_types needs at least one format.')
    for vt in vts:
        if vt.get('format') not in VIDEO_FORMATS:
            p(f'video_types.format must be one of {sorted(VIDEO_FORMATS)}.')
    kws = [k for k in niche.get('keywords') or [] if str(k.get('term') or '').strip()]
    if strict and len(kws) < 5:
        p('Give at least 5 keywords, each with a source.')
    for k in kws:
        if not str(k.get('source') or '').strip():
            p(f'keyword "{k.get("term")}" has no source (scan, vidIQ, autocomplete, comments…).')
    criteria = niche.get('criteria') or {}
    for key, label, gate, _ in CRITERIA:
        c = criteria.get(key) or {}
        score = c.get('score')
        if score is None:
            if strict:
                p(f'{label}: not scored.')
            continue
        if not isinstance(score, int) or not 0 <= score <= 5:
            p(f'{label}: score must be an integer 0–5.')
            continue
        if not str(c.get('rationale') or '').strip():
            p(f'{label}: rationale missing.')
        ev = [e for e in c.get('evidence') or [] if str(e.get('supports') or '').strip()]
        if score >= EVIDENCE_REQUIRED_FROM and not ev:
            p(f'{label}: score {score} needs at least one evidence entry; otherwise score ≤ 2.')
        for e in ev:
            if not (e.get('url') or e.get('scan')):
                p(f'{label}: each evidence entry needs a url or a scan file reference.')
    return problems


def validate(data, strict=False):
    niches = data.get('niches') or []
    problems = []
    ids = [n.get('id') for n in niches]
    if len(ids) != len(set(ids)):
        problems.append('Duplicate niche ids.')
    if strict and len(niches) < 2:
        problems.append('Shortlist at least 2 niches (the framework recommends 3).')
    for n in niches:
        problems += validate_niche(n, strict)
    return problems
