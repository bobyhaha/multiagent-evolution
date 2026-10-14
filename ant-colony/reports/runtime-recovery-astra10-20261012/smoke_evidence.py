"""No API calls, no reference queries, no protected evaluation."""
from pathlib import Path
from types import SimpleNamespace
import json
import tempfile

from ant_colony.programbench import ProgramBenchWorkbench

root = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='runtime-evidence-smoke-') as temp:
    bench = ProgramBenchWorkbench(root.parent / 'code-testing-v1/datasets/programbench-xsv/task.json',
                                  Path(temp) / 'coding', root.parent / 'code-testing-v1/.venv/bin/python')
    actor = SimpleNamespace(name='smoke', team='smoke')
    bench.observation(actor)
    first = bench.execute(actor, {'kind': 'exec', 'command': "python3 - <<'INNER'\nfrom pathlib import Path\np=Path('/tmp/runtime-evidence.txt')\np.write_text(''.join(f'row-{n:04}: durable output observation\\n' for n in range(1800)))\nprint(p.read_text(),end='')\nINNER"})
    assert first['exit_code'] == 0 and not first['output_truncated']
    assert len(first['output'].encode()) > 12000
    artifact = first['artifact']
    second = bench.execute(actor, {'kind': 'exec', 'command': 'test ! -e /tmp/runtime-evidence.txt && printf fresh-sandbox'})
    assert second['exit_code'] == 0 and second['output'] == 'fresh-sandbox'
    text, start, pages = '', 1, 0
    while start:
        page = bench.execute(actor, {'kind': 'read_result', 'path': artifact, 'start': start, 'lines': 100})
        text += page['text'] + '\n'
        start, pages = page['next_start'], pages+1
    assert 'row-1799: durable output observation' in text
    hashes = bench.hashes(bench.source(actor.team))
    note = bench.execute(actor, {'kind': 'record', 'content': 'Report-only artifact, separate from accepted source.'})
    assert bench.hashes(bench.source(actor.team)) == hashes
    result = {'status': 'passed', 'api_calls': 0, 'reference_queries': 0, 'native_evaluation': False,
              'real_disposable_containers': 2, 'retained_output_bytes': len(first['output'].encode()),
              'read_pages': pages, 'recovered_last_line': True, 'source_unchanged': first['source_unchanged'],
              'temporary_file_absent_in_next_exec': True, 'host_report_preserved_hashes': True}
    (Path(__file__).parent / 'smoke-result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
