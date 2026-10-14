"""Read-only trace summary for this operator-assisted experiment; no API calls."""
import collections
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
EPISODE = ROOT / 'runs/programbench-astra10-work-contracts-high-20261012-v18/v18-astra10-work-contracts-xsv'
OUT = Path(__file__).resolve().parent


def main():
    events = []
    lines = (EPISODE / 'events.jsonl').read_text().splitlines()
    for i, line in enumerate(lines):
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            if i != len(lines) - 1:
                raise
    reserved = {e['call_id']: e for e in events if e['event'] == 'call_reserved'}
    deliveries = []
    saved = set()
    (OUT / 'requests').mkdir(exist_ok=True)
    for r in reserved.values():
        obs = json.loads(r['messages'][-1]['content'])
        notes = '\n'.join(x['project_notes'] for x in obs.get('context', []) if 'project_notes' in x)
        versions = sorted(set(re.findall(r'\[OPERATOR_GUIDANCE (v[0-9]{3})\]', notes)))
        if versions:
            deliveries.append({'call': r['call_id'], 'actor': r['actor'], 'round': r['round'], 'versions': versions})
            for version in versions:
                key = (r['actor'], version)
                if key not in saved:
                    path = OUT / 'requests' / f"{r['call_id']}-{r['actor']}-{version}.json"
                    if not path.exists():
                        path.write_text(json.dumps(r, indent=2) + '\n')
                    saved.add(key)
    delivered = {x['call']: x['versions'] for x in deliveries}
    rows = []
    for e in events:
        if e['event'] != 'call':
            continue
        try:
            actions = {x['action']: x['value'] for x in json.loads(e['text'])['actions']}
        except (ValueError, KeyError, TypeError):
            actions = {}
        rows.append({'call': e['call_id'], 'round': e['round'], 'actor': e['actor'], 'kind': e['kind'],
                     'usd': float(e['cost_usd']), 'input_tokens': e['input_tokens'],
                     'output_tokens': e['output_tokens'], 'guidance': delivered.get(e['call_id'], []),
                     'actions': list(actions), 'tool_kind': (actions.get('tool') or {}).get('kind'),
                     'memory_bytes': len((actions.get('memory') or '').encode()),
                     'text_bytes': len(e['text'].encode())})
    phase = {}
    for k in sorted(set(x['kind'] for x in rows)):
        group = [x for x in rows if x['kind'] == k]
        phase[k] = {'calls': len(group), 'usd': round(sum(x['usd'] for x in group), 6),
                    'input_tokens': sum(x['input_tokens'] for x in group),
                    'output_tokens': sum(x['output_tokens'] for x in group)}
    rounds = {}
    for k in sorted(set(x['round'] for x in rows)):
        group = [x for x in rows if x['round'] == k]
        relevant = [e for e in events if e.get('round') == k]
        tool_calls = [e for e in relevant if e['event'] == 'coding_tool']
        rounds[k] = {'calls': len(group), 'usd': round(sum(x['usd'] for x in group), 6),
                     'tools': len(tool_calls),
                     'changed_tool_calls': sum(bool(e['result'].get('changed')) for e in tool_calls),
                     'invalid_replies': sum(e['event'] == 'invalid_reply' for e in relevant),
                     'receipts': sum(e['event'] == 'work_contract_receipt' for e in relevant),
                     'handoffs': sum(e['event'] == 'work_contract_handoff' for e in relevant),
                     'reviews': sum(e['event'] == 'work_contract_reviewed' for e in relevant)}
    report = {'last_seq': events[-1]['seq'], 'phase_totals': phase, 'rounds': rounds,
              'guidance_deliveries': deliveries, 'calls': rows}
    (OUT / 'trace-analysis.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'seq': events[-1]['seq'], 'last': events[-1]['event'],
                      'guidance_calls': len(deliveries),
                      'guidance_by_actor': dict(collections.Counter(x['actor'] for x in deliveries)),
                      'latest_deliveries': deliveries[-7:], 'recent_rounds': dict(list(rounds.items())[-3:]),
                      'recent_work': [x for x in rows if x['kind'] == 'work'][-3:]}))


if __name__ == '__main__':
    main()
