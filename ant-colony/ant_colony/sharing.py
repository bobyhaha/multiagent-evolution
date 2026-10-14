"""Shared evidence with bounded retrieval; direct chat follows team boundaries."""

from .context import clip
from .communication import AdaptiveCommunication, ADAPTIVE_RULES, communication_window
from .recruitment import keywords


SHARING_RULES = """
COLLABORATION CONTRACT: Keep useful teams and recursive outcome ownership. Use
team-local direct messages for detailed work. Cross-team direct messages are only
between designated liaisons: the team root plus at most one temporary teammate
appointed by the root using liaison during formation (null clears it). This is
a temporary communication duty, not a specialist role. Route requests through
your own liaison; use lookup to find an external team's current liaison.
Roots are already liaisons and can message other roots without appointing them.
liaison must name a member of YOUR OWN team; never put an external root ID there.
Unfunded applicants use offers and the shared scratchpad, not direct work chat.
Every worker can append one shared_post per reply: topic, status
(finding|blocker|resolved|interface|coverage), concise text, and evidence path or
command. These are attributed claims, not verified facts. Never paste full logs.
Posts are immutable; correct them by a new post on the same topic. Shared_search
selects a bounded set of relevant latest posts next turn. Global storage is not
global context: you see at most scratch_reads entries, including one recent
blocker. Use team note/read_keys for details. Publish interfaces, reproductions,
coverage gaps and verified findings that another team can act on. Team roots own
integration. Messages addressed to bank are published as shared updates, not
immediate bank conversations; the bank reads bounded evidence at review time.
Do not equate green public probes with completeness. Maintain a compact coverage
matrix derived from the specification: implemented behavior, independently
checked behavior, known failures and untested boundaries. Use local regression
and metamorphic checks when reference probes are exhausted; label uncertainty.
After a stagnation review you have one bank-review interval to produce a changed
artifact or fresh test of a changed revision; otherwise the current integrated
checkpoint is selected. Messages, scratchpad posts and appointments are not
productive steps. Do not fill time with status-only calls or cosmetic changes.
Return exactly ONE JSON object, then STOP. Never simulate the next tool result or
subsequent turn. Put simultaneous actions inside the same object. An ambiguous
multi-object reply executes nothing; there is no automatic paid retry.
"""


def sharing_rules(config, round_number=None):
    window = communication_window(config, round_number)
    rules = SHARING_RULES
    if window["open"]:
        common = SHARING_RULES.split("Every worker can append", 1)[1]
        rules = ("\nCOLLABORATION CONTRACT: Keep useful teams and recursive outcome ownership. "
                 f"OPEN CONTACT WINDOW ({window['mode']}): through round {window['through_round']} inclusive. "
                 "Any worker may message any other known live worker, including unfunded applicants "
                 "and members of other teams. Use bounded topic lookup to find collaborators. "
                 "Message count, inbox, context and spending limits still apply. Contact does not "
                 "grant money, membership, editing permissions or a free model call. "
                 "After this window, return to team-local and liaison communication; preserve useful teams. "
                 "Every worker can append" + common)
    if config.adaptive_communication:
        rules += (ADAPTIVE_RULES + f" After the opening window, alternate {config.communication_local_rounds} "
                  f"local-work rounds with {config.communication_exchange_rounds} exchange round(s). "
                  f"Current mode: {window['mode']}. Bridge lifetime: {config.communication_bridge_rounds} rounds.")
    return rules


class TeamSharing(AdaptiveCommunication):
    def open_contacts(self):
        return self.communication_state()["open"]

    def sharing_schema(self, phase):
        if phase not in {"work", "formation", "discovery"}:
            return {}
        result = {
            "shared_post": {"topic": "stable topic (max 120 bytes)",
                            "status": "finding|blocker|resolved|interface|coverage",
                            "text": "concise evidence and actionable conclusion",
                            "evidence": "public workspace path, command or probe ID"},
            "shared_search": "topic query for the next observation (max 240 bytes)",
        }
        if self.config.adaptive_communication and phase in {"work", "formation"}:
            result.update(bridge_request={"to": "known funded external worker ID", "reason": "concrete dependency or reproduction"},
                          bridge_accept="incoming requester ID", bridge_close=True)
        if phase == "formation":
            result["liaison"] = "team root only: teammate ID or null; temporary extra liaison"
        return result

    def team_liaisons(self, team_id):
        team = self.teams.get(team_id)
        if not team or not team.funded:
            return []
        names = [team.manager]
        if team.liaison and team.liaison_expires >= self.round:
            names.append(team.liaison)
        return [n for n in dict.fromkeys(names) if n in self.agents
                and not self.agents[n].retired and self.agents[n].team == team_id]

    def shared_view(self, actor, query):
        # Host storage can scale with total work. Each inference receives a
        # constant number of byte-bounded entries, never the complete log.
        latest = {}
        for entry in self.shared_entries:
            latest[entry["author"], entry["topic"]] = entry
        terms = set(keywords(query))
        entries = sorted(latest.values(), key=lambda e: (
            -len(terms & set(keywords(e["topic"] + " " + e["text"]))), -e["id"]))
        blockers = [e for e in latest.values() if e["status"] == "blocker"]
        priority = sorted(blockers, key=lambda e: -e["id"])[:1]
        chosen = (priority + [e for e in entries if e not in priority])[:self.config.scratch_reads]
        self.emit("shared_read", actor=actor, entries=[e["id"] for e in chosen])
        return chosen

    def sharing_context(self, agent, phase, required):
        required["schema"].update(self.sharing_schema(phase))
        if "messages" in required["schema"]:
            required["schema"]["messages"][0]["to"] = ("any other known live worker ID; bank publishes an update" if self.open_contacts() else "teammate ID; external liaison only if you are a liaison; bank publishes an update")
        required["communication"] = {
            "team_liaisons": self.team_liaisons(agent.team),
            "you_are_liaison": agent.name in self.team_liaisons(agent.team),
            "direct_messages": ("any other known live worker" if self.open_contacts() else "within your funded team, or liaison to liaison"),
            "open_contact_window": self.open_contacts(),
            "open_contact_through_round": self.communication_state()["through_round"] if self.open_contacts() else None,
            "cycle": self.communication_state(),
            "max_messages": self.config.message_contacts,
            "shared_reads": self.config.scratch_reads,
            "shared_entry_bytes": self.config.shared_entry_bytes,
        }
        if self.config.adaptive_communication:
            required["communication"]["bridge"] = self.bridge_context(agent)
            if not self.open_contacts():
                required["communication"]["direct_messages"] += ", or your accepted temporary bridge peer"
                if "messages" in required["schema"]:
                    required["schema"]["messages"][0]["to"] += "; an accepted temporary bridge peer is also permitted"
        for key in ("peers", "work_peers"):
            if key in required and not self.open_contacts():
                required[key] = [card for card in required[key]
                                 if self.bridge_allows(agent, card["id"]) or self.agents[card["id"]].team == agent.team
                                 or (agent.name in self.team_liaisons(agent.team)
                                     and card["id"] in self.team_liaisons(self.agents[card["id"]].team))]
        required["shared_scratchpad"] = self.shared_view(
            agent.name, agent.shared_query or agent.assignment)
        if getattr(self, "stall_review_round", None) is not None:
            required["recovery_deadline"] = self.stall_review_round + self.config.bank_review_interval

    def append_shared(self, agent, data):
        if not isinstance(data, dict) or set(data) != {"topic", "status", "text", "evidence"}:
            raise ValueError("shared_post requires topic, status, text and evidence")
        if data["status"] not in {"finding", "blocker", "resolved", "interface", "coverage"}:
            raise ValueError("Invalid shared status")
        topic = clip(data["topic"], 120).strip()
        text = clip(data["text"], self.config.shared_entry_bytes).strip()
        evidence = clip(data["evidence"], 240)
        if not topic or not text:
            raise ValueError("Shared topic and text must be nonempty")
        entry = {"id": len(self.shared_entries) + 1, "author": agent.name,
                 "team": agent.team, "round": self.round, "topic": topic,
                 "status": data["status"], "text": text, "evidence": evidence}
        self.shared_entries.append(entry)
        self.emit("shared_post", **entry)

    def sharing_actions(self, agent, reply):
        if self.config.adaptive_communication:
            self.bridge_actions(agent, reply)
        if "shared_search" in reply:
            self.attempt(agent, "shared_search", lambda: setattr(
                agent, "shared_query", clip(reply["shared_search"], 240)))
        if "shared_post" in reply:
            self.attempt(agent, "shared_post", lambda: self.append_shared(agent, reply["shared_post"]))
        if "liaison" in reply:
            def appoint():
                team = self.teams.get(agent.team)
                target = reply["liaison"]
                if self.phase != "formation" or not team or team.manager != agent.name:
                    raise ValueError("Only the team root appoints a liaison at formation")
                if target is not None and (not isinstance(target, str) or target not in team.members
                                           or self.agents[target].retired):
                    raise ValueError("Liaison must be a live teammate or null")
                team.liaison = target
                team.liaison_expires = self.round + self.config.liaison_rounds - 1
                self.emit("liaison_appointed", team=team.id, agent=target, expires=team.liaison_expires)
            self.attempt(agent, "liaison", appoint)

    def team_outbound(self, agent, reply, scope):
        data = reply.get("messages", [])
        if not isinstance(data, list) or len(data) > self.config.message_contacts:
            raise ValueError("Too many messages")
        result, seen = [], set()
        # Validate each recipient separately: a bad bank/retired address must
        # never discard valid messages to collaborators in the same reply.
        for item in data:
            def send():
                if not isinstance(item, dict) or not isinstance(item.get("to"), str):
                    raise ValueError("Message requires a string recipient")
                target = item["to"]
                if target in seen:
                    raise ValueError("Duplicate message recipient: " + target)
                seen.add(target)
                text = clip(item["text"], self.config.text_bytes)
                if target == "bank":
                    self.append_shared(agent, {"topic": "bank-update", "status": "finding",
                                               "text": text, "evidence": "Agent message; not independently verified"})
                    self.emit("bank_update_published", agent=agent.name)
                    return
                receiver = self.agents.get(target)
                if not receiver or receiver.retired:
                    raise ValueError("Unknown or retired recipient: " + target)
                if target == agent.name:
                    raise ValueError("Use memory for self notes")
                funded = agent.team and self.teams[agent.team].funded
                local = funded and receiver.team == agent.team
                bridge = (agent.name in self.team_liaisons(agent.team)
                          and target in self.team_liaisons(receiver.team))
                if not (self.open_contacts() or local or bridge or self.bridge_allows(agent, target)):
                    raise ValueError("Use your team liaison or shared_post for this recipient: " + target)
                result.append((agent.name, target, text, scope))
            self.attempt(agent, "message_delivery", send)
        return result
