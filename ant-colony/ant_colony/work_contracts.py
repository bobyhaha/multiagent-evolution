"""Opt-in artifact handoffs with frozen specifications and host-owned receipts.

These contracts establish provenance, not semantic correctness. A recipient still
has to review coverage against the original task. No check uses hidden grading.
"""

from collections import Counter
from copy import deepcopy
import hashlib
import json


CONTRACT_SCHEMA = {
    "replaces": "current contract ID to supersede, or empty string for the first contract",
    "objective": "concrete outcome within your original assignment",
    "inputs": ["SPEC.md or existing read-only implementation dependency; at most 4, disjoint from outputs"],
    "outputs": ["tracked source/test/documentation path to deliver; 1 to 4; never SPEC.md or PROJECT_NOTES.md"],
    "checks": ["exact exec command to verify the outcome; 1 to 3 commands, no source edits"],
    "acceptance": "observable behavior and coverage required by the original task",
    "stop_when": "completion criterion and when to report blocked or failed",
}
HANDOFF_SCHEMA = {
    "contract_id": "your current contract ID",
    "status": "ready|blocked|failed",
    "evidence": ["runtime receipt ID already visible to you; all declared checks required for ready"],
    "note": "coverage, limitations, or exact blocker and next step",
}
REVIEW_SCHEMA = {
    "contract_id": "visible ready handoff addressed to you",
    "decision": "accept|revise",
    "feedback": "why the evidence meets the original assignment, or the specific missing behavior",
}
RULES = """
WORK CONTRACTS
Before exec, edits, tests or probes, declare a contract for your current assignment.
You may inspect with list/read first. Specify 1-4 implementation outputs, up to 4
read-only inputs (SPEC.md or existing implementation paths), 1-3 exact exec verification commands, acceptance
and stop_when. objective, acceptance, stop_when and handoff/review notes each allow
600 UTF-8 bytes; paths allow 240 and each check command 1200 bytes.
Existing files you will edit belong in outputs, not inputs. Paths are relative to
/workspace. Keep objective, acceptance and stopping criteria faithful to the original
task and assigned scope. Never weaken the task, replace the real behavior with a
shortcut, or alter evaluation criteria to make a check pass.
For ProgramBench, list/read can inspect /reference-docs and /public before declaring
a contract. Use next_start for another page. These mounted directories are not
contract artifact paths. SPEC.md is allowed only as an input. PROJECT_NOTES.md is
auxiliary working memory, never a contract input/output; put deliverable coverage
or tests in ordinary tracked files such as COVERAGE.md or tests/regression.py.
Finish deliverable documentation before final checks. Use record for later reports
outside tracked source and read_result to inspect retained output. These agent
notes are not passing receipts. Every exec has a fresh sandbox; consume /tmp files
within the command that creates them. Do not rerun an unchanged check just to read
its saved output. All actual source and test changes still invalidate evidence.
The runtime freezes the specification and input hashes. Replacing it requires the
current ID in replaces and discards all prior evidence. Assignment, dependency or
source changes can invalidate evidence. Read the runtime's current/stale reasons.
Implement first, then run each declared command in a separate exec call without
source edits. Check commands must exercise the promised behavior, including failure
and boundary cases; exit zero alone does not establish meaningful coverage.
Use only runtime receipt IDs seen in a prior observation. A ready handoff requires
passing receipts for every check on the current source and all output files present.
Do not combine handoff with a tool or a replacement contract. Report blocked or
failed with a concrete reason when progress cannot continue; never invent evidence.
Your direct parent receives your handoff; the bank receives a root's handoff. Work
calls pause while you await review; blocked/failed reports can be returned for
revision but cannot be accepted. Read-only inspection remains available when working.
Recipients: review the frozen specification, original scope, file versions, check
commands and receipts. Accept only if they support the claimed behavior; otherwise
request revision with a specific missing check or behavior. A worker cannot accept
its own handoff. Re-run independent checks when useful; acceptance is a review
judgment, not an environment score. Only accepted, current contracts permit team
readiness or explicit submission. Deadlines may still export an incomplete checkpoint.
"""
REVIEW_RULES = """
WORK CONTRACT REVIEW
work_contracts.incoming presents one complete handoff addressed to you. Compare
its frozen specification with the original task and original_scope. Never weaken
requirements or substitute easier behavior. Runtime receipts establish that the
declared commands ran and whether tracked source changed; they do not prove that
the checks cover the promised behavior. Inspect commands, file versions, coverage
and limitations before choosing review_handoff. Accept only a ready handoff whose
evidence_current is true and whose evidence supports the original assignment.
Return revise with specific missing behavior or checks otherwise. Blocked/failed
handoffs can be returned for revision but cannot be accepted. Feedback allows 600
UTF-8 bytes. You cannot declare a worker's contract or fabricate test receipts.
Source, dependency or assignment changes invalidate accepted evidence; workers
must recheck or explicitly replace their specification. Replacements discard prior
receipts. All current team members need accepted, current contracts before team
readiness or explicit submission. Acceptance is not an environment score. Native
hidden tests remain terminal-only; a deadline may export an incomplete checkpoint.
No coding tools are available in this phase. Ask for independent verification
through an appropriately scoped assignment when the current evidence is weak.
"""


def bounded_text(value, label, cap=600):
    if not isinstance(value, str) or not value.strip() or len(value.encode()) > cap:
        raise ValueError(f"{label} must be nonempty text of at most {cap} bytes")
    return value


class WorkContracts:
    def init_work_contracts(self):
        self.work_contracts = {}
        self.contract_events = Counter()
        self.contract_sequence = self.receipt_sequence = 0
        self.contract_observations = {}

    def contract_event(self, event, **data):
        self.contract_events[event] += 1
        self.emit(event, **data)

    def refresh_work_contracts(self):
        if not self.config.work_contracts:
            return
        for contract in self.work_contracts.values():
            if contract["status"] not in {"ready", "accepted"}:
                continue
            reasons = self.contract_reasons(contract, evidence=True)
            if reasons:
                contract["status"] = "revise"
                contract["review"] = None
                agent = self.agents.get(contract["worker"])
                team = self.teams.get(contract["team"])
                if team:
                    team.ready = None
                if agent:
                    agent.wake_round = self.round
                self.force_bank_review = True
                self.contract_event("work_contract_invalidated", contract_id=contract["id"], reasons=reasons)

    def contract_scope(self, agent):
        team = self.teams.get(agent.team)
        item = self.board.items.get(team.board_task_id, {}) if team else {}
        return {"assignment": agent.assignment, "task_id": item.get("id"),
                "scope": item.get("scope"), "acceptance": item.get("acceptance")}

    def artifact_state(self, agent):
        versions = self.workbench.hashes(self.workbench.source(agent.team))
        # The original specification is mounted separately, never imported from
        # agent edits. Pin its actual bytes when used as a read-only dependency.
        versions["SPEC.md"] = hashlib.sha256((self.workbench.root / "SPEC.md").read_bytes()).hexdigest()
        fingerprint = hashlib.sha256(json.dumps(versions, sort_keys=True).encode()).hexdigest()
        return versions, fingerprint

    def contract_reasons(self, contract, *, evidence=False):
        agent = self.agents.get(contract["worker"])
        if not agent:
            return ["Worker retired; historical evidence cannot authorize a new team."]
        if agent.team != contract["team"] or (agent.parent or "bank") != contract["recipient"]:
            return ["Membership or recipient changed; replace the contract."]
        reasons = []
        if self.contract_scope(agent) != contract["original_scope"]:
            reasons.append("Assignment or board scope changed; replace the contract.")
        versions, fingerprint = self.artifact_state(agent)
        if any(versions.get(p) != h for p, h in contract["input_versions"].items()):
            reasons.append("Pinned inputs changed; inspect dependencies and replace the contract.")
        if evidence:
            if any(p not in versions for p in contract["spec"]["outputs"]):
                reasons.append("Some declared outputs are missing.")
            receipts = contract["receipts"]
            if any(command not in receipts or not receipts[command]["passed"]
                   or receipts[command]["fingerprint"] != fingerprint
                   for command in contract["spec"]["checks"]):
                reasons.append("Every check needs a passing receipt on the current source; re-run stale checks.")
        return reasons

    def declare_contract(self, agent, spec):
        if not self.config.work_contracts or not agent.team or not self.teams[agent.team].funded:
            raise ValueError("Work contracts require a funded coding worker")
        if not isinstance(spec, dict) or set(spec) != set(CONTRACT_SCHEMA):
            raise ValueError("Supply exactly the contract specification fields")
        old = self.work_contracts.get(agent.name)
        if spec["replaces"] != (old["id"] if old else ""):
            raise ValueError("replaces must name your current contract, or be empty for the first")
        for key in ("objective", "acceptance", "stop_when"):
            bounded_text(spec[key], key)
        for key, low, high, cap in (("inputs", 0, 4, 240), ("outputs", 1, 4, 240), ("checks", 1, 3, 1200)):
            entries = spec[key]
            if not isinstance(entries, list) or not low <= len(entries) <= high:
                raise ValueError(f"{key} requires {low} to {high} entries")
            for entry in entries:
                bounded_text(entry, key, cap)
                if entry != entry.strip():
                    raise ValueError(f"{key} entries cannot have leading or trailing whitespace")
            if len(set(entries)) != len(entries):
                raise ValueError(f"Duplicate {key}")
        if set(spec["inputs"]) & set(spec["outputs"]):
            raise ValueError("Read-only inputs and editable outputs must be disjoint")
        versions, _ = self.artifact_state(agent)
        for path in spec["inputs"] + spec["outputs"]:
            rel = self.workbench.safe_relative(path)
            if path == "PROJECT_NOTES.md":
                raise ValueError("PROJECT_NOTES.md is auxiliary memory, not a contract artifact; use a tracked coverage/test file instead")
            spec_input = path == "SPEC.md" and path in spec["inputs"]
            if str(rel) != path or not (spec_input or self.workbench.writable_path(rel)):
                raise ValueError(f"Invalid contract path {path!r}: use a canonical tracked source/test path; SPEC.md is input-only")
        if any(path not in versions for path in spec["inputs"]):
            missing = next(path for path in spec["inputs"] if path not in versions)
            raise ValueError(f"Input {missing!r} does not exist; use existing dependencies or leave inputs empty")
        self.contract_sequence += 1
        contract = {"id": f"wc{self.contract_sequence:06d}", "worker": agent.name,
                    "team": agent.team, "recipient": agent.parent or "bank",
                    "original_scope": self.contract_scope(agent), "spec": deepcopy(spec),
                    "input_versions": {p: versions[p] for p in spec["inputs"]},
                    "receipts": {}, "status": "working", "handoff": None, "review": None}
        self.work_contracts[agent.name] = contract
        self.teams[agent.team].ready = None
        self.contract_event("work_contract_created", **deepcopy(contract))

    def execute_contract_tool(self, agent, action):
        if not isinstance(action, dict):
            raise ValueError("Tool must be an object")
        enabled = self.config.work_contracts
        contract = self.work_contracts.get(agent.name) if enabled else None
        if enabled and action.get("kind") not in {"list", "read", "read_result", "record"}:
            if not contract or self.contract_reasons(contract):
                raise ValueError("Declare a current work contract before exec, edits, tests or probes")
            if contract["status"] not in {"working", "revise"}:
                raise ValueError("Handoff stops work; wait for review or explicitly replace the contract")
        command = action.get("command") if action.get("kind") == "exec" else None
        checking = contract and command in contract["spec"]["checks"]
        before = self.artifact_state(agent)[1] if checking else None
        result = (self.execute_with_progress(agent, action)
                  if self.config.progress_control or self.config.standing_grants
                  else self.workbench.execute(agent, action))
        if checking:
            after = self.artifact_state(agent)[1]
            self.receipt_sequence += 1
            receipt = {"id": f"wr{self.receipt_sequence:07d}", "command": command,
                       "passed": result.get("status") == "ok" and type(result.get("exit_code")) is int
                       and result["exit_code"] == 0 and before == after,
                       "fingerprint": after, "source_unchanged": before == after,
                       "status": result.get("status"), "exit_code": result.get("exit_code"),
                       "round": self.round}
            contract["receipts"][command] = receipt
            self.contract_event("work_contract_receipt", contract_id=contract["id"],
                                worker=agent.name, **receipt)
        return result

    def contract_view(self, contract):
        reasons = self.contract_reasons(contract, evidence=True)
        agent = self.agents.get(contract["worker"])
        versions, fingerprint = self.artifact_state(agent) if agent and agent.team == contract["team"] else ({}, None)
        return {k: deepcopy(contract[k]) for k in ("id", "worker", "recipient", "original_scope", "spec",
                                                  "input_versions", "status", "handoff", "review")} | {
            "output_versions": {p: versions.get(p) for p in contract["spec"]["outputs"]},
            "evidence_current": not reasons, "reasons": reasons,
            "receipts": [{k: v for k, v in r.items() if k not in {"fingerprint", "command"}}
                         | {"check_index": contract["spec"]["checks"].index(r["command"]),
                            "current": r["fingerprint"] == fingerprint}
                         for r in contract["receipts"].values()]}

    def pending_contracts(self, recipient):
        return [c for c in self.work_contracts.values() if c["recipient"] == recipient
                and c["worker"] in self.agents
                and c["status"] in {"ready", "blocked", "failed"} and self.agents[c["worker"]].team == c["team"]
                and (self.agents[c["worker"]].parent or "bank") == recipient]

    def contract_waiting(self, agent):
        """Do not buy repeated work calls while an unchanged handoff awaits review."""
        if not self.config.work_contracts or self.pending_contracts(agent.name):
            return False
        contract = self.work_contracts.get(agent.name)
        if contract and self.contract_reasons(contract):
            return False
        return bool(contract and (contract["status"] in {"ready", "blocked", "failed"}
                    or (contract["status"] == "accepted" and (agent.parent or self.teams[agent.team].ready))))

    def contract_context(self, actor, phase, required):
        if not self.config.work_contracts or phase not in {"work", "bank", "review"}:
            return ""
        self.refresh_work_contracts()
        own = self.work_contracts.get(actor)
        incoming = self.pending_contracts(actor)
        # One review action per reply: admit one complete specification rather
        # than duplicating every descendant's long commands in bounded context.
        limit = 1
        start = ((self.round - 1) * limit) % max(1, len(incoming))
        incoming = (incoming[start:] + incoming[:start])[:limit]
        views = [self.contract_view(c) for c in incoming]
        required["work_contracts"] = {"own": self.contract_view(own) if own else None, "incoming": views}
        required["schema"]["review_handoff"] = REVIEW_SCHEMA
        if phase == "work":
            required["schema"].update(contract=CONTRACT_SCHEMA, handoff=HANDOFF_SCHEMA)
        self.contract_observations[actor] = {
            "receipts": {r["id"] for r in own["receipts"].values()} if own else set(),
            "incoming": {c["id"]: tuple(r["id"] for r in c["receipts"].values()) for c in incoming}}
        return RULES if phase == "work" else REVIEW_RULES

    def handoff_contract(self, agent, handoff, reply):
        if not isinstance(handoff, dict) or set(handoff) != set(HANDOFF_SCHEMA):
            raise ValueError("Supply exactly the handoff fields")
        if "tool" in reply or "contract" in reply:
            raise ValueError("Handoff requires prior observed receipts; do not combine with tool or contract")
        contract = self.work_contracts.get(agent.name)
        if not contract or handoff.get("contract_id") != contract["id"]:
            raise ValueError("Handoff must name your current contract")
        if contract["status"] not in {"working", "revise"}:
            raise ValueError("This contract has already been handed off")
        status = handoff.get("status")
        if status not in {"ready", "blocked", "failed"}:
            raise ValueError("Invalid handoff status")
        bounded_text(handoff.get("note"), "handoff note")
        evidence = handoff.get("evidence")
        if (not isinstance(evidence, list) or len(evidence) > 3
                or any(not isinstance(r, str) for r in evidence) or len(set(evidence)) != len(evidence)):
            raise ValueError("Evidence must contain at most 3 distinct runtime receipt IDs")
        observed = self.contract_observations.get(agent.name, {}).get("receipts", set())
        receipts = {r["id"] for r in contract["receipts"].values()}
        if not set(evidence) <= (observed & receipts):
            raise ValueError("Use only your current contract's previously observed runtime receipts")
        if status == "ready":
            reasons = self.contract_reasons(contract, evidence=True)
            if reasons or set(evidence) != receipts:
                raise ValueError("; ".join(reasons) or "Include receipts for every declared check")
        contract.update(status=status, handoff=deepcopy(handoff), review=None)
        self.contract_event("work_contract_handoff", worker=agent.name, recipient=contract["recipient"], **handoff)
        if contract["recipient"] == "bank":
            self.force_bank_review = True
        else:
            self.deliver([(agent.name, contract["recipient"],
                           f"Contract {contract['id']}: {status}. {handoff['note']}", "contract")])

    def review_contract(self, actor, review):
        if not isinstance(review, dict) or set(review) != set(REVIEW_SCHEMA):
            raise ValueError("Supply exactly the review_handoff fields")
        candidates = {c["id"]: c for c in self.pending_contracts(actor)}
        contract = candidates.get(review.get("contract_id"))
        observed = self.contract_observations.get(actor, {}).get("incoming", {})
        if (not contract or observed.get(contract["id"]) !=
                tuple(r["id"] for r in contract["receipts"].values())):
            raise ValueError("Review only a ready handoff previously presented to you")
        decision = review.get("decision")
        if decision not in {"accept", "revise"}:
            raise ValueError("Review decision must be accept or revise")
        bounded_text(review.get("feedback"), "review feedback")
        reasons = self.contract_reasons(contract, evidence=True)
        if decision == "accept" and (contract["status"] != "ready" or reasons):
            raise ValueError("Accept requires a ready handoff with current evidence: " + "; ".join(reasons))
        contract.update(status="accepted" if decision == "accept" else "revise", review=deepcopy(review))
        self.contract_event("work_contract_reviewed", recipient=actor, worker=contract["worker"], **review)
        self.deliver([(actor, contract["worker"], f"Contract {contract['id']}: {decision}. {review['feedback']}", "contract")])

    def require_accepted_contracts(self, team):
        if not self.config.work_contracts:
            return
        contracts = [self.work_contracts.get(n) for n in team.members]
        if any(not c or c["status"] != "accepted" or self.contract_reasons(c, evidence=True) for c in contracts):
            raise ValueError("Every current team member needs an accepted contract with current evidence")

    def contract_report(self):
        return {"enabled": self.config.work_contracts, "events": dict(self.contract_events),
                "latest_status_counts": dict(Counter(c["status"] for c in self.work_contracts.values())),
                "acceptance_is_not_benchmark_score": True}
