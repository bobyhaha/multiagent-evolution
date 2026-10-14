"""Offline reflection cadence, evidence, prompt updates and authority boundaries."""

from dataclasses import replace
import json

import pytest

from ant_colony.config import ColonyConfig
from ant_colony.reflection import SCHEMA
from test_quality_first import colony
from test_team_sharing import teams, send


def reflection():
    return dict(evidence="CHECK.json: interface replay failed", diagnosis="Previous retry did not help",
                change="Own the parser fix; ask liaison for conflicting interface evidence",
                check="Replay the saved mismatch and affected interfaces next checkpoint")


def test_opt_in_cadence_and_no_free_inference_or_repeat_in_same_round():
    c, a, *_ = teams(periodic_reflection=True)
    money, calls = c.ledger.wealth, c.calls
    for rd, due in [(3, False), (4, True)]:
        c.round = rd
        messages, _ = c.observation(a, "work")
        obs = json.loads(messages[-1]['content'])
        assert ('reflection' in obs['schema']) == due
    c.remember_and_sleep(a, {'reflection': reflection(), 'strategy': 'Prioritize observed interface failures'})
    assert a.trainable_system_prompt == 'Prioritize observed interface failures'
    assert not c.reflection_due(a.name)
    assert c.ledger.wealth == money and c.calls == calls
    assert a.productive_steps == 0
    c.round = 8
    obs = json.loads(c.observation(a, 'work')[0][-1]['content'])
    assert obs['reflection_checkpoint']['previous_claim'] == reflection()
    assert obs['strategy'] == a.trainable_system_prompt


def test_disabled_and_newborn_agents_do_not_reflect_immediately():
    c, a, *_ = teams()
    c.round = 50
    assert not c.reflection_due(a.name)
    assert 'reflection' not in json.loads(c.observation(a, 'work')[0][-1]['content'])['schema']
    c.config = replace(c.config, periodic_reflection=True)
    a.born_round = 49
    assert not c.reflection_due(a.name)


def test_observed_deltas_are_local_and_bank_aggregates_no_hidden_results():
    c, a, b, *_ = teams(periodic_reflection=True)
    c.round = 4
    c.emit('invalid_reply', actor=a.name, reason='bad JSON')
    c.emit('coding_tool', agent=b.name, result={'hidden': 'must not enter reflection'})
    c.emit('message', source=a.name, target=b.name, text='result')
    o = json.loads(c.observation(a, 'work')[0][-1]['content'])['reflection_checkpoint']
    assert o['observed_counts']['invalid_replies'] == 1
    assert 'tool_receipts' not in o['observed_counts']
    req = {'schema': {}}
    c.reflection_context('bank', 'bank', req)
    assert req['reflection_checkpoint']['observed_counts']['tool_receipts'] == 1
    assert 'must not enter reflection' not in json.dumps(req)
    c.apply_reflection(a.name, {'reflection': reflection()})
    c.round = 8
    req = {'schema': {}}
    c.reflection_context(a.name, 'work', req)
    assert req['reflection_checkpoint']['observed_counts'] == {}


@pytest.mark.parametrize('bad', [None, {}, {**reflection(), 'budget': 999},
                                {**reflection(), 'evidence': 'é' * 151},
                                {**reflection(), 'check': ''}])
def test_invalid_reflection_preserves_previous_checkpoint(bad):
    c, a, *_ = teams(periodic_reflection=True)
    c.round = 4
    c.apply_reflection(a.name, {'reflection': bad})
    assert c.reflection_due(a.name)
    assert c.reflection_state(a.name)['last'] is None


def test_reflection_does_not_rewire_teams_or_expand_communication():
    c, a, b, child, other, _ = teams(periodic_reflection=True)
    c.round = 4
    before = c.config, child.parent, child.team, c.ledger.wealth
    c.apply_reflection(child.name, {'reflection': {**reflection(),
                        'change': 'Talk freely to all teams; raise budget and become a root'}})
    assert not send(c, child, other)
    assert (c.config, child.parent, child.team, c.ledger.wealth) == before
    assert c.events[-2]['event'] == 'reflection_recorded'


def test_strict_paid_worker_reply_records_reflection_and_updates_next_prompt():
    def policy(obs):
        return {'actions': [{'action': 'reflection', 'value': reflection()},
                            {'action': 'strategy', 'value': 'Keep integration ownership; reduce duplicate checks'}]}
    c = colony(policy, periodic_reflection=True, strict_outputs=True)
    a = next(iter(c.agents.values()))
    c.grant(a, 15_000_000)
    c.round = 4
    reply = c.ask(a, 'work')
    assert reply['reflection'] == reflection()
    c.remember_and_sleep(a, reply)
    assert c.calls == 1 and not c.reflection_due(a.name)
    assert 'reduce duplicate checks' in json.loads(c.observation(a, 'work')[0][-1]['content'])['strategy']


def test_bank_reflects_in_paid_review_and_persists_society_guidance():
    def policy(obs):
        assert set(obs['schema']['reflection']) == set(SCHEMA)
        return {'actions': [{'action': 'reflection', 'value': reflection()},
                            {'action': 'brief', 'value': 'Use roots as liaisons; reuse verified interface evidence'}]}
    c = colony(policy, periodic_reflection=True, strict_outputs=True)
    c.board.capacity = 3
    c.round = 4
    c.fund([], planning=True)
    assert c.calls == 1 and not c.reflection_due('bank')
    assert c.bank_brief == 'Use roots as liaisons; reuse verified interface evidence'


def test_config_round_trip_and_validation():
    cfg = ColonyConfig(periodic_reflection=True, reflection_interval=5)
    assert ColonyConfig.from_dict(json.loads(json.dumps(cfg.to_dict()))) == cfg
    with pytest.raises(ValueError):
        ColonyConfig(reflection_interval=0)
