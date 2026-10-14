"""Receipts prove execution/provenance; recipient judgment is a separate step."""

from copy import deepcopy
from dataclasses import replace
import json

import pytest

from ant_colony.config import ColonyConfig
from ant_colony.context import request_size
from ant_colony.engine import ColonyMAS
from ant_colony.environment import Task
from ant_colony.structured import actions, flat_to_wire, response_format
from test_commit0 import fixture_task
from test_mechanism import Policy


def colony(tmp_path, **kwargs):
    bench, _ = fixture_task(tmp_path)
    cfg = replace(ColonyConfig(), initial_agents=1, context_bytes=64000,
                  coordination_context_bytes=64000, work_contracts=True, **kwargs)
    events = []
    c = ColonyMAS(cfg, Task("fixture", "Implement value() returning 42.", "original tests", "commit0"),
                  Policy(), lambda event, **data: events.append({"event": event, **data}), workbench=bench)
    c.events, c.round = events, 1
    a = c.agents["a0001"]
    c.grant(a, 18000)
    a.assignment = "Implement and verify value() == 42."
    bench.execute_command = lambda agent, action: {"status": "ok", "exit_code": 0, "output": "passed"}
    return c, a


def spec(**kwargs):
    return {"replaces": "", "objective": "Implement value() == 42", "inputs": [],
            "outputs": ["pkg/a.py"], "checks": ['python -c "from pkg.a import value; assert value() == 42"'],
            "acceptance": "value returns 42 without side effects", "stop_when": "Verified or blocked", **kwargs}


def observe(c, actor, phase="work"):
    required = {"schema": {}}
    c.contract_context(actor, phase, required)
    return required


def check(c, a):
    contract = c.work_contracts[a.name]
    c.execute_contract_tool(a, {"kind": "exec", "command": contract["spec"]["checks"][0]})
    observe(c, a.name)
    return next(iter(contract["receipts"].values()))["id"]


def handoff(c, a, status="ready", evidence=None):
    contract = c.work_contracts[a.name]
    if evidence is None:
        evidence = [r["id"] for r in contract["receipts"].values()]
    c.handoff_contract(a, {"contract_id": contract["id"], "status": status,
                          "evidence": evidence, "note": "Observed behavior and remaining coverage."}, {})


def accept(c, a):
    actor = a.parent or "bank"
    observe(c, actor, "bank" if actor == "bank" else "work")
    c.review_contract(actor, {"contract_id": c.work_contracts[a.name]["id"], "decision": "accept",
                              "feedback": "Verified commands cover the original assignment."})


def test_contract_spec_frozen_and_replacement_discards_evidence(tmp_path):
    c, a = colony(tmp_path)
    declaration = spec()
    c.declare_contract(a, declaration)
    declaration["checks"].append("true")
    old = deepcopy(c.work_contracts[a.name])
    assert len(old["spec"]["checks"]) == 1
    check(c, a)
    with pytest.raises(ValueError, match="replaces"):
        c.declare_contract(a, spec())
    c.declare_contract(a, spec(replaces=old["id"]))
    assert not c.work_contracts[a.name]["receipts"]
    assert c.work_contracts[a.name]["id"] != old["id"]


def test_original_spec_can_be_pinned_but_not_delivered_as_agent_output(tmp_path):
    c, a = colony(tmp_path)
    c.declare_contract(a, spec(inputs=["SPEC.md"]))
    assert c.work_contracts[a.name]["input_versions"]["SPEC.md"]
    assert not c.contract_reasons(c.work_contracts[a.name])
    (c.workbench.root / "SPEC.md").write_text("Changed specification")
    assert "Pinned inputs changed" in c.contract_reasons(c.work_contracts[a.name])[0]


@pytest.mark.parametrize("path", ["SPEC.md", "PROJECT_NOTES.md"])
def test_special_file_output_rejection_names_the_exact_problem(tmp_path, path):
    c, a = colony(tmp_path)
    with pytest.raises(ValueError, match=path):
        c.declare_contract(a, spec(outputs=[path]))


@pytest.mark.parametrize("fields", [
    {"outputs": []}, {"checks": []}, {"checks": ["true"] * 4}, {"checks": ["true", "true"]},
    {"outputs": ["../x"]}, {"outputs": ["tests/test_a.py"]}, {"outputs": ["pkg/./a.py"]},
    {"inputs": ["pkg/missing.py"]}, {"inputs": ["pkg/a.py"]}, {"acceptance": " "},
    {"objective": "x" * 601}, {"checks": ["true "]},
])
def test_contract_rejects_invalid_spec_without_partial_state(tmp_path, fields):
    c, a = colony(tmp_path)
    with pytest.raises(ValueError):
        c.declare_contract(a, spec(**fields))
    assert not c.work_contracts and c.contract_sequence == 0


def test_runtime_receipts_then_recipient_acceptance_gate_ready(tmp_path):
    c, a = colony(tmp_path, bank_finalization=True)
    with pytest.raises(ValueError, match="Declare"):
        c.execute_contract_tool(a, {"kind": "exec", "command": "true"})
    assert c.execute_contract_tool(a, {"kind": "read", "path": "pkg/a.py"})["sha256"]
    c.declare_contract(a, spec())
    check(c, a)
    handoff(c, a)
    with pytest.raises(ValueError, match="accepted"):
        c.mark_ready(a, {"ready": "Implemented"})
    with pytest.raises(ValueError, match="previously presented"):
        c.review_contract(a.name, {"contract_id": c.work_contracts[a.name]["id"], "decision": "accept", "feedback": "self"})
    accept(c, a)
    c.mark_ready(a, {"ready": "Implemented, with visible evidence"})
    assert c.teams[a.team].ready
    assert c.contract_report()["events"]["work_contract_reviewed"] == 1


@pytest.mark.parametrize("result", [
    {"status": "ok", "exit_code": 1}, {"status": "timeout", "exit_code": 0},
    {"status": "ok", "exit_code": False}, {"status": "ok"},
])
def test_failed_or_ambiguous_execution_cannot_be_handed_off(tmp_path, result):
    c, a = colony(tmp_path)
    c.declare_contract(a, spec())
    c.workbench.execute_command = lambda agent, action: result
    check(c, a)
    with pytest.raises(ValueError, match="passing receipt"):
        handoff(c, a)


def test_verification_cannot_modify_source_and_claim_a_pass(tmp_path):
    c, a = colony(tmp_path)
    c.declare_contract(a, spec())
    def execute(agent, action):
        (c.workbench.source(a.team) / "pkg/a.py").write_text("def value(): return 42\n")
        return {"status": "ok", "exit_code": 0}
    c.workbench.execute_command = execute
    check(c, a)
    with pytest.raises(ValueError, match="passing receipt"):
        handoff(c, a)


def test_receipts_must_be_seen_in_prior_observation_and_match_contract(tmp_path):
    c, a = colony(tmp_path)
    c.declare_contract(a, spec())
    contract = c.work_contracts[a.name]
    c.execute_contract_tool(a, {"kind": "exec", "command": contract["spec"]["checks"][0]})
    with pytest.raises(ValueError, match="previously observed"):
        handoff(c, a)
    observe(c, a.name)
    with pytest.raises(ValueError, match="previously observed"):
        handoff(c, a, evidence=["wr9999999"])
    payload = {"contract_id": contract["id"], "status": "ready", "evidence": [], "note": "done"}
    with pytest.raises(ValueError, match="do not combine"):
        c.handoff_contract(a, payload, {"tool": {"kind": "exec"}})
    handoff(c, a)
    with pytest.raises(ValueError, match="previously presented"):
        c.review_contract("bank", {"contract_id": contract["id"], "decision": "accept", "feedback": "done"})


def test_changes_invalidate_accepted_evidence_and_reopen_verification(tmp_path):
    c, a = colony(tmp_path, bank_finalization=True)
    c.declare_contract(a, spec())
    check(c, a)
    handoff(c, a)
    accept(c, a)
    c.mark_ready(a, {"ready": "done"})
    (c.workbench.source(a.team) / "pkg/other.py").write_text("x=1\n")
    c.refresh_work_contracts()
    assert c.work_contracts[a.name]["status"] == "revise"
    assert c.teams[a.team].ready is None
    check(c, a)
    handoff(c, a)
    accept(c, a)
    c.mark_ready(a, {"ready": "rechecked"})


@pytest.mark.parametrize("change", ["input", "assignment", "membership", "output"])
def test_dependency_scope_membership_and_missing_output_invalidate_acceptance(tmp_path, change):
    c, a = colony(tmp_path)
    source = c.workbench.source(a.team)
    (source / "pkg/input.py").write_text("x=1\n")
    c.declare_contract(a, spec(inputs=["pkg/input.py"]))
    check(c, a)
    handoff(c, a)
    observe(c, "bank", "bank")
    if change == "input":
        (source / "pkg/input.py").write_text("x=2\n")
    elif change == "assignment":
        a.assignment = "different scope"
    elif change == "membership":
        a.team = None
    else:
        (source / "pkg/a.py").unlink()
    with pytest.raises(ValueError):
        c.review_contract("bank", {"contract_id": c.work_contracts[a.name]["id"], "decision": "accept", "feedback": "done"})


def test_children_handoff_only_to_parent_and_root_waits_for_all_members(tmp_path):
    c, root = colony(tmp_path)
    child = c.new_agent("worker", "verify", root, 2000, "Verify value")
    for a in (root, child):
        c.declare_contract(a, spec())
        check(c, a)
        handoff(c, a)
    assert c.pending_contracts("bank")[0]["worker"] == root.name
    assert c.pending_contracts(root.name)[0]["worker"] == child.name
    accept(c, root)
    with pytest.raises(ValueError, match="Every current team member"):
        c.require_accepted_contracts(c.teams[root.team])
    accept(c, child)
    c.require_accepted_contracts(c.teams[root.team])


@pytest.mark.parametrize("status", ["blocked", "failed"])
def test_failure_handoff_is_honest_and_does_not_require_a_pass(tmp_path, status):
    c, a = colony(tmp_path)
    c.declare_contract(a, spec())
    handoff(c, a, status=status, evidence=[])
    assert c.work_contracts[a.name]["status"] == status
    assert c.pending_contracts("bank")[0]["status"] == status
    observe(c, "bank", "bank")
    with pytest.raises(ValueError, match="ready handoff"):
        accept(c, a)
    with pytest.raises(ValueError, match="Handoff stops"):
        c.execute_contract_tool(a, {"kind": "exec", "command": "true"})


def test_strict_schema_and_prompts_are_bounded_and_roundtrip(tmp_path):
    c, a = colony(tmp_path)
    c.declare_contract(a, spec())
    check(c, a)
    messages, _ = c.observation(a, "work")
    obs = json.loads(messages[-1]["content"])
    assert request_size(messages) <= c.config.context_bytes
    assert response_format(messages)["json_schema"]["strict"]
    catalog = obs["schema"]
    reply = {"contract": spec(replaces=c.work_contracts[a.name]["id"])}
    assert actions(flat_to_wire(reply, catalog), catalog) == reply
    assert "Never weaken the task" in messages[0]["content"]
    assert obs["work_contracts"]["own"]["receipts"][0]["current"]


def test_live_work_loop_contract_and_tool_then_handoff_then_bank_review(tmp_path):
    c, a = colony(tmp_path, event_driven_bank=True, progress_control=True)
    calls = []
    def policy(obs):
        calls.append(obs["phase"])
        if obs["phase"] == "bank":
            incoming = obs["work_contracts"]["incoming"][0]
            return {"review_handoff": {"contract_id": incoming["id"], "decision": "accept", "feedback": "Meets assigned behavior"}}
        own = obs["work_contracts"]["own"]
        if not own:
            return {"contract": spec(), "tool": {"kind": "exec", "command": spec()["checks"][0]}}
        return {"handoff": {"contract_id": own["id"], "status": "ready", "note": "Observed test pass", "evidence": [own["receipts"][0]["id"]]}}
    c.provider = Policy(policy)
    c.work()
    c.fund([])
    assert calls == ["work", "work", "bank"]
    assert c.work_contracts[a.name]["status"] == "accepted"
    assert not [e for e in c.events if e["event"] in {"invalid_reply", "action_rejected"}]


def test_invalid_replacement_does_not_execute_accompanying_tool(tmp_path):
    c, a = colony(tmp_path)
    c.declare_contract(a, spec())
    c.provider = Policy(lambda obs: {"contract": spec(), "tool": {"kind": "exec", "command": "true"}})
    c.work()
    assert not [e for e in c.events if e["event"] == "coding_tool"]


def test_waiting_handoff_does_not_buy_repeated_work_calls(tmp_path):
    c, a = colony(tmp_path)
    c.declare_contract(a, spec())
    check(c, a)
    handoff(c, a)
    c.work()
    assert c.calls == 0
    c.work_contracts[a.name]["status"] = "blocked"
    a.assignment = "New assignment needs a new contract"
    assert not c.contract_waiting(a)


def test_retired_worker_keeps_history_without_crashing_or_authorizing_handoffs(tmp_path):
    c, root = colony(tmp_path)
    child = c.new_agent("worker", "verify", root, 2000, "Verify")
    c.declare_contract(child, spec())
    check(c, child)
    handoff(c, child)
    c.phase = "formation"
    c.leave(child)
    c.population.remove_agent(child)
    del c.agents[child.name]
    c.refresh_work_contracts()
    assert not c.pending_contracts(root.name)
    assert c.contract_view(c.work_contracts[child.name])["reasons"] == [
        "Worker retired; historical evidence cannot authorize a new team."]


def test_done_task_with_stale_readiness_can_work_again(tmp_path):
    c, a = colony(tmp_path, bank_finalization=True)
    c.board.capacity = 1
    c.board.replace([{"id": "implement", "title": "Implement", "scope": "pkg", "acceptance": "Pass tests"}])
    c.board.claim("implement", a.name, a.team, c.round)
    c.teams[a.team].board_task_id = "implement"
    c.declare_contract(a, spec())
    check(c, a)
    handoff(c, a)
    accept(c, a)
    c.mark_ready(a, {"ready": "done"})
    c.board.items["implement"]["status"] = "done"
    c.workbench.progress[a.team]["revision"] += 1
    c.refresh_readiness()
    assert c.board.can_work(a.team)
    assert c.board.items["implement"]["owner"] == a.name
    assert c.board.items["implement"]["status"] == "blocked"
    assert any(e["event"] == "readiness_reopened" for e in c.events)


def test_allocation_rejects_whole_batch_before_moving_money_or_scope(tmp_path):
    c, root = colony(tmp_path)
    one = c.new_agent("worker", "one", root, 2000, "first")
    two = c.new_agent("worker", "two", root, 2000, "second")
    team = c.teams[root.team]
    before = team.allowances.copy()
    with pytest.raises(ValueError, match="exceeds"):
        c.allocate(root, [{"agent": one.name, "amount": 100, "assignment": "changed"},
                          {"agent": two.name, "amount": 1000000}])
    assert team.allowances == before and one.assignment == "first"
    c.check()


def test_accepted_public_selection_is_frozen_before_terminal_evaluation(tmp_path, monkeypatch):
    c, a = colony(tmp_path, bank_finalization=True, max_rounds=1)
    c.formation = lambda: []
    def finalize(*args, **kwargs):
        c.final_answer, c.final_author = "Reviewed artifact", "__public__"
        c.submission_mode = "bank_approved_public"
    c.fund = finalize
    def forbidden(*args, **kwargs):
        pytest.fail("The bank-approved public artifact must not integrate more changes before grading")
    c.workbench.finish_round = forbidden
    monkeypatch.setattr("ant_colony.engine.evaluate", lambda *args: 0.5)
    assert c.run()["score"] == 0.5


def test_large_contracts_and_incoming_review_fit_full_quality_prompt(tmp_path):
    c, root = colony(tmp_path)
    child = c.new_agent("worker", "verify", root, 2000, "x" * 900)
    c.config = replace(c.config, quality_first=True, team_sharing=True, hierarchy_bias=True,
                       request_pricing=True, text_bytes=1800, bank_contacts=3, max_children=3)
    for a in (root, child):
        a.assignment = "x" * 1800
        c.declare_contract(a, spec(objective="o" * 600, acceptance="a" * 600, stop_when="s" * 600,
                                  checks=["#" + str(i) + "x" * 1198 for i in range(3)]))
        for command in c.work_contracts[a.name]["spec"]["checks"]:
            c.execute_contract_tool(a, {"kind": "exec", "command": command})
        observe(c, a.name)
    handoff(c, child)
    messages, _ = c.observation(root, "work")
    assert request_size(messages) < 64000
    obs = json.loads(messages[-1]["content"])
    assert len(obs["work_contracts"]["incoming"]) == 1
    assert obs["work_contracts"]["incoming"][0]["spec"]["checks"][0] == "#0" + "x" * 1198
