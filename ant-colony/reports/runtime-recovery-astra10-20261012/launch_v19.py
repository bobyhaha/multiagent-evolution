"""Launch this explicitly authorized experiment; credentials remain in process memory."""
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from ant_colony.campaign_budget import Ledger

root = Path(__file__).resolve().parents[2]
report = Path(__file__).resolve().parent
study = root / 'runs/programbench-astra10-runtime-recovery-high-20261012-v19'
ident = 'v19-astra10-runtime-recovery-xsv'
validation = json.loads((report / 'validation.json').read_text())
for name, digest in validation['source_hashes'].items():
    if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
        raise RuntimeError('Validated file changed: ' + name)
if study.exists() or (report / 'launch.json').exists():
    raise RuntimeError('Launch already attempted; inspect recorded state, never launch twice')
ledger = Ledger(root / 'runs/programbench-mixed-high-20261010/campaign.sqlite', parallel=True)
before = ledger.summary()
if before['blocked'] or before['pending'] or before['accounted_usd'] + 100 > before['ceiling_usd']:
    raise RuntimeError('Shared accounting does not admit this run')
with ledger.connect() as db:
    if db.execute('SELECT 1 FROM runs WHERE id=?', (ident,)).fetchone():
        raise RuntimeError('Episode already registered')
    old_deadline = db.execute("SELECT value FROM campaign_settings WHERE key='inference_deadline'").fetchone()[0]
key = os.environ.get('OPENROUTER_API_KEY') or getpass.getpass('OpenRouter key (memory only, no echo): ')
if not key.strip():
    raise RuntimeError('Credential absent; no launch')
started = time.time()
deadline = started + 5*60*60
reason = ('User explicitly authorized a new $100 experiment in this chat after the completed v17/v18 experiment. '
          'One fresh 10-Astra v19 episode, five-hour inference limit; old episode deadlines/caps and all historical holds remain unchanged.')
authorization = ledger.authorize_new_run_deadline(ident, deadline, reason)
command = [sys.executable, str(root/'scripts/run_programbench_colony40.py'),
           '--out',str(study), '--prior-study',str(root/'runs/programbench-astra10-work-contracts-high-20261012-v18'),
           '--episode-id',ident,'--max-usd','100','--inference-deadline',str(deadline),
           '--tolerate-transient-errors', *validation['launch_flags']]
environment = dict(os.environ, PYTHONPATH=str(root), OPENROUTER_API_KEY=key)
with (report/'controller.log').open('x') as log:
    process = subprocess.Popen(command, cwd=root, env=environment, stdin=subprocess.DEVNULL,
                               stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
del key, environment
record = {'pid':process.pid,'started_epoch':started,'episode':ident,'study':str(study),
          'new_cap_usd':100,'deadline_epoch':deadline,
          'deadline_utc':datetime.fromtimestamp(deadline,timezone.utc).isoformat(),
          'old_campaign_deadline_unchanged':old_deadline,'accounting_before':before,
          'authorization':authorization,'command':command,'frozen_prompts':True}
(report/'launch.json').write_text(json.dumps(record,indent=2)+'\n')
ledger.close()
print(json.dumps({'pid':process.pid,'study':str(study),'cap_usd':100,'deadline_utc':record['deadline_utc']}))
