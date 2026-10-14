"""Read-only run/accounting monitor: no inference and no protected test reads."""
from collections import Counter
from decimal import Decimal
import json
import os
from pathlib import Path
import sqlite3
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
launch = json.loads((HERE/'launch.json').read_text())
study = Path(launch['study'])
episode = study/launch['episode']
events = []
path = episode/'events.jsonl'
if path.exists():
    lines = path.read_text().splitlines()
    for i,line in enumerate(lines):
        try: events.append(json.loads(line))
        except json.JSONDecodeError:
            if i != len(lines)-1: raise
counts = Counter(e['event'] for e in events)
phases = {}
for e in events:
    if e['event'] != 'call': continue
    row = phases.setdefault(e['kind'],{'calls':0,'usd':0.0})
    row['calls'] += 1
    row['usd'] += float(e['cost_usd'])
ledger = ROOT/'runs/programbench-mixed-high-20261010/campaign.sqlite'
with sqlite3.connect(f'file:{ledger}?mode=ro',uri=True) as db:
    rows = db.execute('select status,reserved,actual from calls where run=?',(launch['episode'],)).fetchall()
    cap = db.execute('select cap from runs where id=?',(launch['episode'],)).fetchone()
    deadline = db.execute('select deadline from run_inference_authorizations where run=?',(launch['episode'],)).fetchone()
    old_deadline = db.execute("select value from campaign_settings where key='inference_deadline'").fetchone()[0]
    historical_holds = db.execute('select status,count(*),sum(reserved) from calls where actual is null and run!=? group by status',(launch['episode'],)).fetchall()
settled = sum((Decimal(str(a)) for _,_,a in rows if a is not None),Decimal(0))
held = sum((Decimal(str(r)) for _,r,a in rows if a is None),Decimal(0))
try: os.kill(launch['pid'],0); alive=True
except ProcessLookupError: alive=False
snap=next((e['state'] for e in reversed(events) if e['event']=='snapshot'),None)
latest=events[-1] if events else {}
reserved=next((e for e in reversed(events) if e['event']=='call_reserved'),{})
tool_counts=Counter(e.get('kind') for e in events if e['event']=='coding_tool')
rejections=[{k:e.get(k) for k in ('seq','event','round','actor','agent','action','reason') if k in e}
            for e in events if e['event'] in {'invalid_reply','action_rejected','review_rejected','runner_error','stopped'}]
checkpoint=next(({k:e.get(k) for k in ('version','status','passed','total')} for e in reversed(events) if e['event']=='checkpoint_test'),None)
record={'checked_epoch':time.time(),'study':str(study),'episode':launch['episode'],'controller_alive':alive,
        'study_status':json.loads((study/'study.json').read_text()).get('status') if (study/'study.json').exists() else None,
        'last_seq':latest.get('seq'),'round':max((e.get('round',0) for e in events),default=0),
        'last_event':latest.get('event'),'last_phase':latest.get('phase'),
        'last_request':{k:reserved.get(k) for k in ('call_id','actor','kind','round')},
        'accounting':{'cap_usd':cap[0] if cap else None,'settled_usd':str(settled),'held_usd':str(held),
                      'accounted_usd':str(settled+held),'statuses':dict(Counter(s for s,_,_ in rows))},
        'deadline_epoch':deadline[0] if deadline else None,'old_deadline_unchanged':old_deadline==launch['old_campaign_deadline_unchanged'],
        'historical_holds':historical_holds,'counts':dict(counts),'phase_totals':phases,
        'tool_counts':dict(tool_counts),'recent_rejections':rejections[-6:],'public_diagnostic':checkpoint,
        'snapshot_round':snap.get('round') if snap else None,
        'funded_teams':sum(bool(t.get('funded')) for t in snap['teams'].values()) if snap and isinstance(snap.get('teams'),dict) else None}
if (episode/'report.json').exists():
    report=json.loads((episode/'report.json').read_text())
    record['final_report']={k:report.get(k) for k in ('status','rounds','score','calls','api_usd','submission_mode','stop_reason')}
(HERE/'live-status.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
