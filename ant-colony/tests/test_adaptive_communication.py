"""Cycles, bilateral consent, expiration, context bounds, and no free work."""

from dataclasses import replace
import json

import pytest

from ant_colony.communication import communication_window
from ant_colony.context import byte_size
from ant_colony.quality import rules
from test_team_sharing import teams, send


def setup():
    return teams(open_contact_rounds=2, adaptive_communication=True)


def request(c, a, b):
    c.sharing_actions(a, {"bridge_request": {"to": b.name, "reason": "Reproduce incompatible shared interface"}})


def test_four_local_rounds_then_one_exchange_repeat_without_resetting_teams():
    c, a, b, child, other, free = setup()
    original = [(x.name, x.team, x.parent, list(x.children)) for x in c.agents.values()]
    money = c.ledger.wealth
    for r in range(1, 18):
        c.round = r
        c.begin_communication_round()
        expected = r in {1, 2, 7, 12, 17}
        assert c.open_contacts() is expected
        assert bool(send(c, child, other)) is expected
        assert bool(send(c, free, child)) is expected
        messages, _ = c.observation(child, "work")
        obs = json.loads(messages[-1]["content"])
        assert obs['communication']['open_contact_window'] is expected
        assert ('OPEN CONTACT WINDOW' in messages[0]['content']) is expected
        assert obs['communication']['cycle'] == communication_window(c.config, r)
    assert [(x.name, x.team, x.parent, list(x.children)) for x in c.agents.values()] == original
    assert c.ledger.wealth == money and c.calls == 0
    assert len([e for e in c.events if e['event'] == 'communication_phase']) == 17


def test_bridge_requires_consent_and_opens_only_the_two_endpoints():
    c, a, b, child, other, free = setup()
    c.round = 3
    request(c, child, other)
    assert not send(c, child, other)
    c.sharing_actions(a, {'bridge_accept': child.name})
    assert not c.communication_bridges
    c.sharing_actions(other, {'bridge_accept': child.name})
    assert send(c, child, other) and send(c, other, child)
    assert not send(c, child, b) and not send(c, a, other)
    assert not c.bridge_requests and len(c.communication_bridges) == 1
    assert c.calls == 0


def test_bridge_expires_without_refresh_from_messages_or_progress_credit():
    c, a, b, child, other, free = setup()
    c.round = 3
    request(c, child, other)
    c.sharing_actions(other, {'bridge_accept': child.name})
    c.round = 4
    assert send(c, other, child)
    c.round = 5
    assert not send(c, other, child)
    c.begin_communication_round()
    assert not c.communication_bridges and child.productive_steps == 0
    assert any(e['event'] == 'bridge_closed' for e in c.events)


def test_expired_request_cannot_be_accepted_and_duplicate_cannot_extend_it():
    c, a, b, child, other, free = setup()
    c.round = 3
    request(c, child, other)
    c.round = 4
    request(c, child, other)
    assert c.bridge_requests[child.name]['expires'] == 4
    c.round = 5
    c.sharing_actions(other, {'bridge_accept': child.name})
    assert not c.communication_bridges and not c.bridge_requests


@pytest.mark.parametrize('mutation', ['retire', 'change_team', 'defund'])
def test_bridge_revoked_on_membership_or_funding_change(mutation):
    c, a, b, child, other, free = setup()
    c.round = 3
    request(c, child, other)
    c.sharing_actions(other, {'bridge_accept': child.name})
    if mutation == 'retire':
        other.retired = True
    elif mutation == 'change_team':
        other.team = None
    else:
        c.teams[other.team].funded = False
    assert not send(c, child, other)
    c.prune_bridges()
    assert not c.communication_bridges


def test_one_bridge_slot_and_no_unfunded_or_same_team_bridge():
    c, a, b, child, other, free = setup()
    c.round = 3
    request(c, child, free)
    request(c, child, a)
    assert not c.bridge_requests
    request(c, child, other)
    request(c, a, other)
    request(c, child, b)
    assert len(c.bridge_requests) == 1
    c.sharing_actions(other, {'bridge_accept': child.name})
    request(c, a, other)
    assert not c.bridge_requests
    c.sharing_actions(child, {'bridge_close': True})
    assert not c.communication_bridges
    request(c, a, other)
    assert len(c.bridge_requests) == 1


def test_lookup_exposes_specialists_and_context_explains_bridge_permission():
    c, a, b, child, other, free = setup()
    c.round = 3
    other.assignment = 'Unique interface verification'
    c.lookup_collaborators(child, 'Unique interface verification')
    assert other.name in {row['id'] for row in child.directory}
    assert free.name not in {row['id'] for row in child.directory}
    request(c, child, other)
    messages, _ = c.observation(other, 'work')
    obs = json.loads(messages[-1]['content'])
    assert obs['communication']['bridge']['pending']['requested_by'] == child.name
    assert 'bridge_accept' in obs['schema']
    assert byte_size(messages) <= c.config.context_bytes
    c.sharing_actions(other, {'bridge_accept': child.name})
    messages, _ = c.observation(child, 'work', peers=[other.name])
    obs = json.loads(messages[-1]['content'])
    assert obs['work_peers'][0]['id'] == other.name
    assert 'bridge peer' in obs['schema']['messages'][0]['to']


def test_open_exchange_preserves_volume_and_inbox_bounds():
    c, a, b, child, other, free = setup()
    c.round = 7
    with pytest.raises(ValueError, match='Too many'):
        c.outbound(child, {'messages': [{'to': other.name, 'text': 'x'}] * 5}, set(), 'work')
    for _ in range(20):
        c.deliver(send(c, child, other))
    assert len(other.inbox) == c.config.inbox_size
    assert c.calls == 0


def test_custom_period_and_disabled_mode_are_explicit():
    c, *_ = setup()
    custom = replace(c.config, open_contact_rounds=0, communication_local_rounds=2,
                     communication_exchange_rounds=2)
    assert [communication_window(custom, r)['open'] for r in range(1, 9)] == [False, False, True, True] * 2
    disabled = replace(c.config, adaptive_communication=False)
    assert not communication_window(disabled, 7)['open']
    assert 'RECURRING COORDINATION' not in rules(disabled, 'work', 7)
    with pytest.raises(ValueError, match='requires team_sharing'):
        replace(c.config, team_sharing=False)
    with pytest.raises(ValueError):
        replace(c.config, communication_local_rounds=0)


def test_runner_opt_in_changes_only_new_mechanism_flag(monkeypatch):
    from test_colony40_plan import module
    from test_programbench import config
    m = module(monkeypatch)
    args = dict(model_mix='all-astra', quality_first=True, team_sharing=True, open_contact_rounds=2)
    old = m.experiment_config(config().to_dict(), **args)
    new = m.experiment_config(config().to_dict(), **args, adaptive_communication=True)
    assert {k for k in old if old[k] != new[k]} == {'adaptive_communication'}


def test_bridge_actions_flow_through_normal_paid_schema_and_accounting():
    from test_providers_and_evaluation import response
    c, a, b, child, other, free = setup()
    c.round = 3
    def transport(payload):
        obs = json.loads(payload['messages'][-1]['content'])
        reply = ({'bridge_request': {'to': other.name, 'reason': 'Interface reproduction'}}
                 if obs['self'] == child.name else {'bridge_accept': child.name})
        from test_mechanism import encode_reply
        return response(encode_reply(obs, reply), tokens=30, cost=0.001)
    c.provider.transport = transport
    before = c.ledger.wealth
    for worker in (child, other):
        c.remember_and_sleep(worker, c.ask(worker, 'work'))
    assert c.bridge_allows(child, other.name)
    assert c.calls == 2 and before - c.ledger.wealth == 2000
    assert not any(e['event'] == 'invalid_reply' for e in c.events)
    c.check()
