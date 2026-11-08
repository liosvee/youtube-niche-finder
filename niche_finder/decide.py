"""Gates, ranking, idea distinctness, scenario economics and the decision report.

The rubric is an equally weighted, explicitly subjective decision aid. It is
not a validated model and it predicts no earnings.
"""
from .analysis import tokens
from .core import CRITERIA, GATES, GATE_MIN, NICHE_TYPES, now

# "Favor the niche with the strongest evidence of demand and the clearest
# reason for viewers to choose your channel."
CHOICE_KEYS = ('audience_demand', 'new_channel_opportunity', 'original_contribution')
DUPLICATE_SIMILARITY = 0.6
IDEAS_TARGET = 20


def _score(niche, key):
    return ((niche.get('criteria') or {}).get(key) or {}).get('score')


def _mean(xs):
    xs = [x for x in xs if isinstance(x, int)]
    return round(sum(xs) / len(xs), 2) if xs else None


def gates(niche):
    failed = []
    for key in GATES:
        s = _score(niche, key)
        if s is None or s < GATE_MIN:
            label = next(c[1] for c in CRITERIA if c[0] == key)
            failed.append(f'{label} ({"unscored" if s is None else s} < {GATE_MIN})')
    return failed


def idea_check(ideas):
    """Flag near-duplicate titles (Jaccard on content words). Repetitive,
    mass-produced uploads risk monetization; 20 distinct ideas is the test."""
    ideas = [i if isinstance(i, str) else i.get('title', '') for i in ideas or []]
    ideas = [i.strip() for i in ideas if i and i.strip()]
    sets = [set(tokens(i)) for i in ideas]
    pairs = []
    for a in range(len(ideas)):
        for b in range(a + 1, len(ideas)):
            if not sets[a] or not sets[b]:
                continue
            sim = len(sets[a] & sets[b]) / len(sets[a] | sets[b])
            if sim >= DUPLICATE_SIMILARITY:
                pairs.append({'a': ideas[a], 'b': ideas[b], 'similarity': round(sim, 2)})
    dup_ids = {p['b'] for p in pairs}
    return {'count': len(ideas), 'distinct': len(ideas) - len(dup_ids),
            'target': IDEAS_TARGET, 'near_duplicates': pairs}


def economics(niche):
    """Estimated monthly operating profit = YouTube revenue + external revenue − operating costs.
    YouTube revenue = views / 1000 × RPM (creator revenue after share; Shorts use engaged views)."""
    e = niche.get('economics') or {}
    views, rpm = e.get('monthly_views') or {}, e.get('rpm_usd') or {}
    ext = e.get('external_revenue_usd') or {}
    costs = sum(v for v in (e.get('costs_usd') or {}).values() if isinstance(v, (int, float)))
    out = {'basis': e.get('basis') or 'scenario', 'rpm_source': e.get('rpm_source') or '',
           'monthly_costs_usd': round(costs, 2), 'scenarios': {}}
    for case in ('low', 'mid', 'high'):
        v, r = views.get(case), rpm.get(case)
        if not isinstance(v, (int, float)) or not isinstance(r, (int, float)):
            continue
        yt = v / 1000 * r
        x = ext.get(case) or 0
        out['scenarios'][case] = {'monthly_views': v, 'rpm_usd': r, 'youtube_revenue_usd': round(yt, 2),
                                  'external_revenue_usd': x, 'operating_profit_usd': round(yt + x - costs, 2)}
    vpm = e.get('videos_per_month')
    if isinstance(vpm, (int, float)) and vpm > 0:
        out['cost_per_video_usd'] = round(costs / vpm, 2)
    return out


def rank(data):
    rows = []
    for n in data.get('niches') or []:
        scores = {k: _score(n, k) for k, *_ in CRITERIA}
        failed = gates(n)
        rows.append({
            'id': n.get('id'),
            'niche': n,
            'scores': scores,
            'gates_failed': failed,
            'eligible': not failed,
            'choice_strength': _mean([scores[k] for k in CHOICE_KEYS]),
            'overall': _mean(list(scores.values())),
            'ideas': idea_check(n.get('ideas')),
            'economics': economics(n),
        })
    rows.sort(key=lambda r: (r['eligible'], r['choice_strength'] or 0, r['overall'] or 0), reverse=True)
    return rows


def _fmt(x):
    return '—' if x is None else (f'{x:,.0f}' if isinstance(x, (int, float)) and abs(x) >= 100 else str(x))


def report(data, project):
    rows = rank(data)
    L = [f'# Niche decision — {project}', '',
         f'Generated {now()}. Decision aid, not a validated scoring system or an earnings forecast.',
         'Gates (minimum requirements): original contribution, production economics, monetization & rights ≥ '
         f'{GATE_MIN}/5. Ranking among eligible niches: mean of demand, new-channel opportunity and original '
         'contribution, then the overall 10-criterion mean.', '',
         '| Rank | Niche | Type | Language | Gates | Choice strength | Overall | Distinct ideas |',
         '|---|---|---|---|---|---|---|---|']
    for i, r in enumerate(rows, 1):
        n = r['niche']
        L.append(f"| {i if r['eligible'] else '—'} | {n.get('niche_name') or r['id']} | {n.get('niche_type')} | "
                 f"{n.get('language')}{'-' + n['region'] if n.get('region') else ''} | "
                 f"{'pass' if r['eligible'] else 'FAIL'} | {_fmt(r['choice_strength'])} | {_fmt(r['overall'])} | "
                 f"{r['ideas']['distinct']}/{IDEAS_TARGET} |")
    eligible = [r for r in rows if r['eligible']]
    L.append('')
    if eligible:
        top = eligible[0]
        L.append(f"**Strongest candidate on current evidence:** {top['niche'].get('niche_name') or top['id']}. "
                 'Next step: produce a small pilot batch (3–5 videos) and re-score with measured results.')
        if len(eligible) > 1 and (top['choice_strength'] or 0) - (eligible[1]['choice_strength'] or 0) < 0.5:
            L.append(f"Close call with {eligible[1]['niche'].get('niche_name') or eligible[1]['id']} "
                     '(< 0.5 apart): the pilot should decide, not this table.')
    else:
        L.append('**No niche passes the minimum requirements yet.** Fix the failed gates or replace the niche.')
    sel = (data.get('decision') or {}).get('selected')
    if sel:
        L.append(f'\n**Your selection:** `{sel}`')
    for r in rows:
        n = r['niche']
        L += ['', '---', '', f"## {n.get('niche_name') or r['id']} (`{r['id']}`)", '',
              f"- **Niche type:** {n.get('niche_type')} — {NICHE_TYPES.get(n.get('niche_type'), '')}",
              f"- **Description:** {n.get('description') or '—'}",
              f"- **Channel promise:** {n.get('channel_promise') or '—'}",
              f"- **Audience:** {n.get('audience') or '—'}",
              f"- **Language / region:** {n.get('language')}{' / ' + n['region'] if n.get('region') else ''}"]
        L.append('- **Video types:**')
        for vt in n.get('video_types') or []:
            bits = [vt.get(k) for k in ('style', 'length', 'series', 'cadence') if vt.get(k)]
            L.append(f"  - {vt.get('format')}: {'; '.join(bits) or '—'}")
        kws = [k for k in n.get('keywords') or [] if k.get('term')]
        L.append('- **Keywords:** ' + (', '.join(f"{k['term']} _({k.get('source')})_" for k in kws) or '—'))
        if r['gates_failed']:
            L.append(f"- **Failed gates:** {'; '.join(r['gates_failed'])}")
        L += ['', '| Criterion | Score | Rationale | Evidence |', '|---|---|---|---|']
        for key, label, gate, _ in CRITERIA:
            c = (n.get('criteria') or {}).get(key) or {}
            ev = c.get('evidence') or []
            ev_txt = '<br>'.join(f"{e.get('supports')} ({e.get('url') or e.get('scan')}"
                                 f"{', ' + e['accessed_on'] if e.get('accessed_on') else ''})" for e in ev) or '—'
            L.append(f"| {label}{' ★' if gate else ''} | {_fmt(c.get('score'))} | "
                     f"{(c.get('rationale') or '—').replace('|', '/')} | {ev_txt.replace('|', '/')} |")
        e = r['economics']
        L += ['', f"**Economics ({e['basis']}; RPM source: {e['rpm_source'] or 'not given'})** — monthly costs "
                  f"${_fmt(e['monthly_costs_usd'])}" + (f", ≈ ${_fmt(e['cost_per_video_usd'])}/video"
                                                       if 'cost_per_video_usd' in e else '')]
        if e['scenarios']:
            L += ['', '| Case | Views/mo | RPM $ | YouTube $ | External $ | Profit $ |', '|---|---|---|---|---|---|']
            for case, s in e['scenarios'].items():
                L.append(f"| {case} | {_fmt(s['monthly_views'])} | {s['rpm_usd']} | {_fmt(s['youtube_revenue_usd'])}"
                         f" | {_fmt(s['external_revenue_usd'])} | {_fmt(s['operating_profit_usd'])} |")
            L.append('\n_Scenarios are assumptions until you have your own revenue data. A competitor\'s views do '
                     'not reveal their revenue or profit._')
        else:
            L.append('No scenarios yet (need monthly_views and rpm_usd).')
        ic = r['ideas']
        L.append(f"\n**Ideas:** {ic['count']} listed, {ic['distinct']} distinct (target {IDEAS_TARGET}).")
        for p in ic['near_duplicates'][:5]:
            L.append(f"- Near-duplicate ({p['similarity']}): “{p['a']}” ≈ “{p['b']}”")
        if n.get('unknowns'):
            L.append(f"\n**Unknowns:** {n['unknowns']}")
    return '\n'.join(L) + '\n', rows
