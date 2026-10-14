"""Bounded paid recovery decisions; no free inference or automatic money transfers."""

import json

from .context import build_context, clip


CONTROL_RULES = """Resolve the concrete execution bottleneck in the observation.
This is a small paid control call, not a coding turn. Transfer existing allowance
only between yourself and your direct children. Negative amounts reclaim rights;
assignments, membership and contract acceptance remain unchanged. Retain the
displayed control reserve when giving money away. Pool enough for a useful work
call rather than leaving every worker below its minimum. Route one specific task
or evidence request to a listed sleeping descendant when useful; delivery wakes
it without requiring intermediate managers to buy calls. Routing grants no money
and changes no assignment. Cancel an obsolete funding request explicitly. Do not
repeat status, fabricate evidence, weaken checks or recruit to increase headcount.
If no useful transition exists, return no actions. This decision is not repeated
until relevant state changes. All amounts are integer spending rights.
"""

CONTROL_SCHEMA = {
    "allocate": [{"agent": "direct child ID", "amount": 1000}],
    "route": [{"to": "listed sleeping descendant ID", "text": "specific next task within existing scope"}],
    "cancel_proposal": False,
    "memory": "compact blocker, changed fact and next useful action",
}


class RuntimeControl:
    def descendants(self, agent):
        pending = list(agent.children)
        while pending:
            name = pending.pop(0)
            child = self.agents.get(name)
            if child and not child.retired and child.team == agent.team:
                yield child
                pending.extend(child.children)

    def route_targets(self, agent):
        return [a for a in self.descendants(agent)
                if a.wake_round > self.round and self.rights(a) >= self.working_minimum(a.model)
                and not self.contract_waiting(a)][:self.config.max_children]

    def route_control(self, agent, rows):
        allowed = {a.name for a in self.route_targets(agent)}
        if not isinstance(rows, list) or len(rows) > self.config.max_children:
            raise ValueError("Routing exceeds local control bound")
        deliveries, seen = [], set()
        for row in rows:
            if not isinstance(row, dict) or row.get("to") not in allowed or row["to"] in seen:
                raise ValueError("Route only once to a listed sleeping descendant")
            value = clip(row.get("text"), self.config.text_bytes)
            if not value.strip():
                raise ValueError("Routing needs a concrete task or evidence request")
            seen.add(row["to"])
            deliveries.append((agent.name, row["to"], value, "control"))
        self.deliver(deliveries)

    def cancel_proposal(self, agent, value):
        if value is not True:
            return
        old = agent.application
        agent.application = None
        agent.recruitment_plan = None
        agent.recovery_paused = True
        self.emit("proposal_cancelled", agent=agent.name, target=(old or {}).get("target"))

    def control_state(self, agent):
        return {"allowance": self.rights(agent),
                "children": [{"id": name, "allowance": self.rights(self.agents[name]),
                              "minimum_work": self.working_minimum(self.agents[name].model),
                              "assignment": self.agents[name].assignment}
                             for name in agent.children],
                "route_targets": [{"id": a.name, "allowance": self.rights(a),
                                   "assignment": a.assignment, "wake_round": a.wake_round}
                                  for a in self.route_targets(agent)],
                "application": agent.application,
                "revision": self.workbench.summary(agent.team)["revision"] if self.workbench else None}

    def recover_controls(self):
        if not self.config.runtime_control:
            return
        for agent in list(self.agents.values()):
            if not agent.team or not agent.match_wakeup_condition(self) or agent.born_round >= self.round:
                continue
            if not self.board.can_work(agent.team):
                continue
            state = self.control_state(agent)
            reserve = self.call_budget(agent.model, "control")
            pooled = state["allowance"] + sum(c["allowance"] for c in state["children"])
            minima = [self.working_minimum(agent.model), *[c["minimum_work"] for c in state["children"]]]
            stranded = (bool(agent.children) and state["allowance"] < minima[0] + reserve
                        and pooled - reserve >= min(minima))
            if not (stranded or state["route_targets"]) or state["allowance"] < reserve:
                continue
            signature = json.dumps(state, sort_keys=True)
            if signature == getattr(agent, "last_control_state", None):
                continue
            required = {"phase": "control", "self": agent.name, "task": self.task.problem,
                        "assignment": agent.assignment, "minimum_work": minima[0],
                        "control_reserve": reserve, "state": state, "schema": CONTROL_SCHEMA,
                        "last_action_errors": self.action_errors.get(agent.name, []),
                        "last_protocol_error": self.format_errors.get(agent.name),
                        "_strict_outputs": self.config.strict_outputs}
            messages, _ = build_context(CONTROL_RULES, required, [{"memory": agent.memory}],
                                        self.context_limit("control"))
            reply = self.parse(self.call(agent.model, messages, agent=agent, wallet=agent.team,
                                         kind="control"), set(CONTROL_SCHEMA), agent.name)
            if "allocate" in reply:
                self.attempt(agent, "allocate", lambda: self.allocate(agent, reply["allocate"]))
            if "route" in reply:
                self.attempt(agent, "route", lambda: self.route_control(agent, reply["route"]))
            if "cancel_proposal" in reply:
                self.cancel_proposal(agent, reply["cancel_proposal"])
            if "memory" in reply:
                self.attempt(agent, "memory", lambda: setattr(agent, "memory", clip(reply["memory"], self.config.text_bytes)))
            # Remember post-payment/action state: the call's own fee cannot trigger polling.
            agent.last_control_state = json.dumps(self.control_state(agent), sort_keys=True)
            self.check()

    def select_incomplete_checkpoint(self, reason):
        if not isinstance(reason, str) or not reason.strip() or not self.workbench:
            self.defer_finalization("Incomplete checkpoint needs a reason and coding artifact")
            return
        self.final_answer, self.final_author = clip(reason, self.config.answer_bytes), "__public__"
        self.submission_mode = "bank_selected_incomplete_checkpoint"
        self.emit("submission", author="__public__", team="public", text=self.final_answer,
                  candidates=1, selection=self.submission_mode, verified_complete=False,
                  blockers=self.readiness_receipts())
