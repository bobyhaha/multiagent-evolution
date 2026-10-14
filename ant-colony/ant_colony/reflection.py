"""Bounded evidence-led reflection inside already-authorized paid turns."""

from collections import Counter


SCHEMA = {
    "evidence": "Observed receipt/path and result; distinguish claims from verified evidence",
    "diagnosis": "What helped or failed, including the previous change's result or unknown",
    "change": "One individual/team/interaction change, or retain with reason",
    "check": "Observable next-check criterion; reconsider at the next reflection",
}
RULES = '''
PERIODIC REFLECTION CHECKPOINT: Use this already-funded turn to review recent
performance before choosing actions. Return reflection with evidence, diagnosis,
change and check (each nonempty, at most 300 UTF-8 bytes). Compare the previous
reflection's predicted benefit with observed results; say unknown if untested.
Counts of edits, messages and public probes are not correctness or hidden scores.
Consider individual methods, delegation/ownership, integration and interaction:
who needs to talk, what evidence is missing, which redundant exchanges to stop,
and whether a team should persist, split its scope or release an idle member.
Choose one useful change or explicitly retain the current approach. Do not create
teams or messages merely to demonstrate reflection. Use strategy to REPLACE your
bounded working prompt with the complete revised strategy, retaining useful prior
constraints; use memory for compact lessons. Communicate actionable implications
through existing messages/shared evidence. Propose changes beyond your authority
to the parent/root; execute structural changes only through ordinary authorized
actions, consent and funding. The bank uses brief/tasks/decisions to revise society
priorities, ownership and coordination guidance. A reflection is an agent claim,
not an executed reorganization, verified result or productive-step reward.
You may revise working strategies and interaction practices, never host rules,
model settings, budgets, deadlines, contact/context limits or tool permissions.
'''
EVENTS = {
    "call": "paid_calls", "invalid_reply": "invalid_replies",
    "action_rejected": "rejected_actions", "coding_tool": "tool_receipts",
    "source_written": "file_changes", "productive_step": "progress_events",
    "message": "delivered_messages", "finalization_deferred": "deferred_finishes",
}


class Reflection:
    def reflection_state(self, actor):
        if not hasattr(self, "reflection_states"):
            self.reflection_states = {}
        return self.reflection_states.setdefault(actor, {
            "round": 0, "counts": Counter(), "baseline": Counter(), "last": None})

    def track_reflection(self, event, data):
        if not self.config.periodic_reflection or event not in EVENTS:
            return
        key = EVENTS[event]
        self.reflection_state("bank")["counts"][key] += 1
        actor = data.get("actor") or data.get("agent") or data.get("source")
        if actor and actor != "bank":
            self.reflection_state(actor)["counts"][key] += 1

    def reflection_due(self, actor):
        if not self.config.periodic_reflection:
            return False
        state = self.reflection_state(actor)
        born = self.agents[actor].born_round if actor in self.agents else 0
        return self.round - max(born, state["round"]) >= self.config.reflection_interval

    def reflection_context(self, actor, phase, required):
        if phase not in {"formation", "work", "bank"} or not self.reflection_due(actor):
            return ""
        state = self.reflection_state(actor)
        required["schema"]["reflection"] = dict(SCHEMA)
        required["reflection_checkpoint"] = {
            "since_round": state["round"],
            "observed_counts": dict(state["counts"] - state["baseline"]),
            "previous_claim": state["last"],
            "scope": "society" if actor == "bank" else "individual and authorized team",
        }
        return RULES

    def apply_reflection(self, actor, reply):
        if "reflection" not in reply:
            return
        value = reply["reflection"]
        if (not self.reflection_due(actor) or not isinstance(value, dict)
                or set(value) != set(SCHEMA) or any(
                    not isinstance(v, str) or not v.strip() or len(v.encode()) > 300
                    for v in value.values())):
            self.emit("action_rejected", agent=actor, action="reflection",
                      reason="Reflection requires a due checkpoint and four nonempty fields of at most 300 bytes")
            return
        state = self.reflection_state(actor)
        previous = state["last"]
        state.update(round=self.round, baseline=state["counts"].copy(), last=dict(value))
        self.emit("reflection_recorded", actor=actor, previous=previous, reflection=dict(value),
                  status="agent_claim", next_due_round=self.round + self.config.reflection_interval)
