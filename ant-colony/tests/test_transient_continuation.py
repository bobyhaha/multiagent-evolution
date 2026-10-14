from decimal import Decimal
from http.client import IncompleteRead
import json
import time
from urllib.error import HTTPError

import pytest

from ant_colony.campaign_budget import Ledger, BudgetStop
from ant_colony.config import ColonyConfig
from ant_colony.engine import ColonyMAS
from ant_colony.environment import Task
from ant_colony.providers import OpenRouterProvider, RetainedTransportError
from ant_colony.storage import RunStore, audit
from ant_colony.transient import TransientPolicy
from test_providers_and_evaluation import MODELS, response


def http(code):
    return HTTPError("https://provider.invalid", code, "", {}, None)


@pytest.mark.parametrize("error", [http(429), http(502), http(503), http(504), IncompleteRead(b'')])
def test_only_recognized_finished_transports_may_skip_a_turn(error):
    p = TransientPolicy(time.time() + 100, enabled=True)
    assert p.retain_and_continue(error, Decimal('1.2'))
    assert p.held == Decimal('1.2') and p.not_before > time.time()
    assert p.retain_and_continue(error, Decimal('1.2'))
    assert not p.retain_and_continue(error, Decimal('1.2'))
    p.success()
    assert p.retain_and_continue(error, Decimal('1.2'))


@pytest.mark.parametrize("error", [http(400), http(401), http(403), http(500), TimeoutError(), ValueError(), KeyError()])
def test_unknown_contract_auth_and_inflight_timeout_fail_closed(error):
    assert not TransientPolicy(time.time() + 100, enabled=True).retain_and_continue(error, 1)


def test_hold_error_and_deadline_limits():
    assert not TransientPolicy(time.time() + 100).retain_and_continue(http(502), 1)
    assert not TransientPolicy(time.time() - 1, enabled=True).retain_and_continue(http(502), 1)
    p = TransientPolicy(time.time() + 100, enabled=True)
    assert not p.retain_and_continue(http(502), Decimal('10.01'))
    for _ in range(8):
        assert p.retain_and_continue(http(502), 1)
        p.success()
    assert not p.retain_and_continue(http(502), 1)


def test_durable_deadline_blocks_another_ledger_instance_without_releasing_hold(tmp_path, monkeypatch):
    ledger = Ledger(tmp_path / 'campaign.sqlite')
    ledger.register('run', 100)
    now = time.time()
    ledger.set_inference_deadline(now + 60, 'User authorized a fixed five-hour monitoring and repair window')
    call = ledger.reserve('run', 5, 'work', 'a1', 'astra')
    ledger.uncertain(call)
    ledger.retain_failed_reservation(call, 'Explicitly authorized inspection; full maximum remains reserved')
    other = Ledger(ledger.path)
    monkeypatch.setattr('ant_colony.campaign_budget.time.time', lambda: now + 61)
    with pytest.raises(BudgetStop, match='deadline'):
        other.reserve('run', 1, 'work', 'a1', 'astra')
    assert other.summary()['unconfirmed_usd'] == 5


def test_turn_failure_retains_provider_and_society_reserves_then_run_audits(tmp_path):
    store = RunStore(tmp_path / 'run')
    requests = []
    def transport(payload):
        obs = json.loads(payload['messages'][-1]['content'])
        requests.append(obs)
        if len(requests) == 1:
            raise RetainedTransportError('recognized HTTP failure; reservation retained')
        result = {}
        if obs['phase'] == 'application':
            result = {'proposal': {'plan': 'Compute', 'amount': 6000}, 'accept': True}
        elif obs['phase'] == 'bank':
            result = {'decisions': [{'agent': p['agent'], 'amount': p['amount'],
                                     'decision': 'approve', 'feedback': 'Proceed'} for p in obs['proposals']]}
        elif obs['phase'] == 'work':
            result = {'submit': '2'}
        from test_mechanism import encode_reply
        return response(encode_reply(obs, result))
    provider = OpenRouterProvider(MODELS, 1, store.emit, transport=transport)
    c = ColonyMAS(ColonyConfig(initial_agents=2), Task('t', '1+1?', '2'), provider, store.emit)
    report = c.run()
    store.close()
    assert report['status'] == 'completed' and not provider.blocked
    assert provider.reserved > 0 and c.uncertain_credits == c.config.max_output_tokens
    events = [json.loads(l) for l in store.path.read_text().splitlines()]
    assert len([e for e in events if e['event'] == 'transport_turn_skipped']) == 1
    assert len(requests) == c.calls
    check = audit(store.path)
    assert check['accounting_valid'] and check['unresolved_api_calls'] == 1


def test_fresh_run_deadline_does_not_reopen_old_runs_or_raise_caps(tmp_path, monkeypatch):
    ledger = Ledger(tmp_path / 'campaign.sqlite')
    now = time.time()
    ledger.set_inference_deadline(now+10, 'Original bounded experiment authorization')
    ledger.register('old', 10)
    ledger.authorize_new_run_deadline('new', now+100, 'User authorized a new separate $100 experiment')
    ledger.register('new', 100)
    other = Ledger(ledger.path)
    monkeypatch.setattr('ant_colony.campaign_budget.time.time', lambda: now+11)
    with pytest.raises(BudgetStop, match='deadline'):
        other.reserve('old', 1, 'work', 'a1', 'astra')
    call = other.reserve('new', 1, 'work', 'a1', 'astra')
    other.settle(call, 1, {})
    with pytest.raises(BudgetStop, match='budget'):
        other.reserve('new', 100, 'work', 'a1', 'astra')
    with pytest.raises(ValueError, match='existing'):
        other.authorize_new_run_deadline('old', now+100, 'Must not reopen historical episodes')
    monkeypatch.setattr('ant_colony.campaign_budget.time.time', lambda: now+101)
    with pytest.raises(BudgetStop, match='deadline'):
        other.reserve('new', 1, 'work', 'a1', 'astra')
    with ledger.connect() as db:
        assert db.execute("SELECT value FROM campaign_settings WHERE key='inference_deadline'").fetchone()[0] == now+10
