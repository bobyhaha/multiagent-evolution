"""Recurring exchange windows and consensual, expiring peer bridges."""

from .context import clip


def communication_window(config, round_number):
    r = round_number or 0
    opening = config.open_contact_rounds
    if config.team_sharing and 1 <= r <= opening:
        return {"mode": "opening", "open": True, "through_round": opening}
    if config.adaptive_communication and r > opening:
        local, exchange = config.communication_local_rounds, config.communication_exchange_rounds
        start = opening + 1 + ((r - opening - 1) // (local + exchange)) * (local + exchange)
        if r >= start + local:
            return {"mode": "exchange", "open": True, "through_round": start + local + exchange - 1}
        return {"mode": "local", "open": False, "through_round": start + local - 1,
                "next_exchange_round": start + local}
    return {"mode": "local", "open": False, "through_round": None}


ADAPTIVE_RULES = """
RECURRING COORDINATION: Preserve useful teams and ownership across communication
cycles. During local phases implement and test; during exchange windows share
compact new evidence, negotiate dependencies and revise plans, then resume local
work. Exchange is optional, not a requirement to chat or reorganize. Existing
funding, consent, child caps and editing authority still govern hiring/changes.
Outside open windows, use bridge_request with a known funded external worker ID
and a concrete dependency/reproduction. That worker must explicitly bridge_accept
your ID before direct peer messages are permitted. One pending request OR active
bridge per agent; requests and bridges expire after the configured short lifetime.
Use bridge_close=true when done. This temporarily connects two workers, not their
whole teams, and never changes membership, money, roles or editing permissions.
Lookup may return external specialists: request their bridge or contact your
liaison instead of sending unauthorized direct messages. Publish reusable results
to the common scratchpad and report to your team. Contact windows and bridges do
not wake the whole population, buy calls, count as progress, or postpone stopping.
"""


class AdaptiveCommunication:
    def communication_state(self):
        return communication_window(self.config, self.round)

    def bridge_record_valid(self, row):
        if row["expires"] < self.round:
            return False
        for name, team in zip(row["agents"], row["teams"]):
            a = self.agents.get(name)
            if not a or a.retired or a.team != team or not self.teams.get(team) or not self.teams[team].funded:
                return False
        return row["teams"][0] != row["teams"][1]

    def prune_bridges(self):
        for collection, event in ((self.bridge_requests, "bridge_request_expired"),
                                  (self.communication_bridges, "bridge_closed")):
            for key, row in list(collection.items()):
                if not self.bridge_record_valid(row):
                    del collection[key]
                    self.emit(event, agents=row["agents"], reason="expired or membership/funding changed")

    def active_bridge(self, agent):
        return next((row for row in self.communication_bridges.values()
                     if agent.name in row["agents"] and self.bridge_record_valid(row)), None)

    def bridge_allows(self, source, target):
        row = self.active_bridge(source)
        return bool(row and target != source.name and target in row["agents"])

    def bridge_context(self, agent):
        pending = next((r for r in self.bridge_requests.values()
                        if agent.name in r["agents"] and self.bridge_record_valid(r)), None)
        return {"active": self.active_bridge(agent), "pending": pending,
                "lifetime_rounds": self.config.communication_bridge_rounds,
                "max_pending_or_active": 1}

    def begin_communication_round(self):
        if self.config.adaptive_communication:
            self.prune_bridges()
            self.emit("communication_phase", **self.communication_state())

    def bridge_busy(self, name):
        return any(name in r["agents"] for r in
                   [*self.bridge_requests.values(), *self.communication_bridges.values()])

    def request_bridge(self, agent, data):
        self.prune_bridges()
        if not isinstance(data, dict) or set(data) != {"to", "reason"} or not isinstance(data["to"], str):
            raise ValueError("bridge_request requires a worker ID and dependency reason")
        peer = self.agents.get(data["to"])
        reason = clip(data["reason"], self.config.shared_entry_bytes).strip()
        if not reason or not peer or peer is agent:
            raise ValueError("Bridge needs a distinct live worker and concrete reason")
        row = {"agents": [agent.name, peer.name], "teams": [agent.team, peer.team],
               "requested_by": agent.name, "reason": reason,
               "expires": self.round + self.config.communication_bridge_rounds - 1}
        if not self.bridge_record_valid(row):
            raise ValueError("Bridge endpoints must be live funded members of different teams")
        if self.bridge_busy(agent.name) or self.bridge_busy(peer.name):
            raise ValueError("A bridge endpoint already has a pending or active bridge")
        self.bridge_requests[agent.name] = row
        peer.wake_round = min(peer.wake_round, self.round)
        self.emit("bridge_requested", **row)

    def accept_bridge(self, agent, requester):
        self.prune_bridges()
        if not isinstance(requester, str):
            raise ValueError("bridge_accept requires the requester ID")
        row = self.bridge_requests.get(requester)
        if not row or row["agents"][1] != agent.name:
            raise ValueError("Only the addressed worker can accept a pending bridge")
        del self.bridge_requests[requester]
        row = {**row, "expires": self.round + self.config.communication_bridge_rounds - 1}
        self.communication_bridges[requester] = row
        self.emit("bridge_opened", **row)

    def close_bridge(self, agent, value):
        if value is not True:
            raise ValueError("bridge_close must be true")
        for collection in (self.bridge_requests, self.communication_bridges):
            for key, row in list(collection.items()):
                if agent.name in row["agents"]:
                    del collection[key]
                    self.emit("bridge_closed", agents=row["agents"], reason="closed by endpoint")

    def bridge_actions(self, agent, reply):
        for key, fn in (("bridge_close", self.close_bridge), ("bridge_accept", self.accept_bridge),
                        ("bridge_request", self.request_bridge)):
            if key in reply:
                self.attempt(agent, key, lambda key=key, fn=fn: fn(agent, reply[key]))
