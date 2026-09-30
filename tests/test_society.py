"""Behavioral and accounting contracts; all provider tests use a local fake server."""

import copy
import json
import math
import random
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import test as lab


def society(**kw):
    cfg = lab.Config(**kw).validate()
    events = lab.Events()
    model = lab.Model(cfg, events, None)
    return lab.Society(cfg, events, model)


class AccountingTests(unittest.TestCase):
    def test_transfer_and_self_payment_conserve(self):
        ledger = lab.Ledger(lab.Events())
        ledger.mint("a", 10, "test")
        self.assertTrue(ledger.transfer("a", "b", 3, "test"))
        self.assertTrue(ledger.transfer("a", "a", 5, "self"))
        self.assertEqual(ledger.balance("a"), 7)
        self.assertFalse(ledger.transfer("b", "a", 4, "too_large"))
        self.assertEqual(ledger.balance("b"), 3)
        self.assertAlmostEqual(ledger.audit(), 0)

    def test_debt_retirement_is_not_money_creation(self):
        ledger = lab.Ledger(lab.Events())
        ledger.mint("a", 1, "test")
        ledger.transfer("a", "house", 3, "rent", debt=True)
        ledger.retire("a")
        self.assertEqual(ledger.balance("house"), 1)
        self.assertEqual(ledger.audit(), 0)

    def test_nan_and_negative_transfers_rejected(self):
        ledger = lab.Ledger(lab.Events())
        for bad in (-1, math.nan, math.inf):
            with self.assertRaises(ValueError):
                ledger.transfer("a", "b", bad, "test")

    def test_reward_supply_does_not_depend_on_population(self):
        s = society(project="teams", agents=7)
        ids = list(s.agents)
        tid = s.found(ids[0])
        s.hire(tid, ids[1], 0)
        before = s.ledger.minted
        s.reward(ids[1], 1)
        self.assertAlmostEqual(s.ledger.minted - before, s.cfg.reward)
        self.assertAlmostEqual(s.ledger.balance(tid), 2 + s.cfg.beta * s.cfg.reward)
        s.ledger.audit()

    def test_wages_funded_and_refunded_on_exit(self):
        s = society(project="teams", contract_length=4)
        a, b = list(s.agents)[:2]
        tid = s.found(a)
        self.assertTrue(s.hire(tid, b, 0.2))
        c = s.contracts[b]
        self.assertAlmostEqual(s.ledger.balance(c.escrow), 0.8)
        s.end_episode()
        self.assertAlmostEqual(s.ledger.balance(c.escrow), 0.6)
        s.leave(b, "voluntary")
        self.assertNotIn(b, s.contracts)
        self.assertIsNone(s.agents[b].team)
        self.assertNotIn(c.escrow, s.ledger.balances)
        s.ledger.audit()

    def test_contract_expires_without_selective_kicking(self):
        s = society(project="teams", contract_length=1, evolution=False)
        a, b = list(s.agents)[:2]
        tid = s.found(a)
        s.hire(tid, b, 0.1)
        s.end_episode()
        s.episode = 1
        s.settle_contracts()
        self.assertIsNone(s.agents[b].team)
        self.assertNotIn(b, s.contracts)

    def test_two_teams_cannot_hire_same_agent(self):
        s = society(project="teams")
        a, b, c = list(s.agents)[:3]
        t1, t2 = s.found(a), s.found(b)
        self.assertTrue(s.hire(t1, c, 0.1))
        self.assertFalse(s.hire(t2, c, 0.1))
        s.assert_memberships()

    def test_novice_bid_is_frozen_after_first_assignment(self):
        s = society()
        ids = list(s.agents)
        s.assign_novice_bids(ids)
        before = {a: s.agents[a].bid for a in ids}
        s.assign_novice_bids(ids)
        self.assertEqual(before, {a: s.agents[a].bid for a in ids})
        child = s.birth(s.agents[ids[0]])
        s.assign_novice_bids(list(s.agents))
        self.assertGreater(child.bid, max(before.values()))


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.s = society(agents=4, steps=12)
        self.task = lab.Tasks(self.s.cfg).make("train", 0, list(self.s.agents))
        self.ep = lab.Episode(self.s, self.task, False)
        self.ep.virtual = {}
        self.ep.summaries = {}

    def test_private_observation_has_no_label_or_peers_records(self):
        aid = list(self.s.agents)[0]
        obs = self.ep.observation(aid)
        self.assertNotIn("answer", obs)
        self.assertNotIn("answer", obs["task"])
        self.assertEqual({r["id"] for r in obs["records"]}, set(self.task.holders[aid]))
        for peer in obs["peers"]:
            self.assertNotIn("records", peer)

    def test_cannot_send_unobserved_records(self):
        a, b = list(self.s.agents)[:2]
        outsider = next(
            x for x in self.task.records if x["id"] not in self.ep.known[a] and x["id"] not in self.ep.known[b]
        )
        self.ep.deliver(a, b, [outsider["id"]], "invented request")
        self.assertNotIn(outsider["id"], self.ep.known[b])

    def test_delivery_has_real_information_effect(self):
        a, b = list(self.s.agents)[:2]
        rid = self.task.holders[a][0]
        self.assertNotIn(rid, self.ep.known[b])
        self.ep.deliver(a, b, [rid], "valid evidence")
        self.assertIn(rid, self.ep.known[b])

    def test_utf8_bandwidth_bound_includes_record_payload(self):
        records = [{"id": str(i), "text": "证据" * 20} for i in range(10)]
        packed, text, size = lab.pack_records(records, "你好" * 100, 300)
        self.assertLessEqual(size, 300)
        self.assertLess(len(packed), len(records))
        self.assertEqual(size, len(lab.dumps({"records": packed, "text": text}).encode()))

    def test_score_rejects_nan_bool_and_wrong_number(self):
        self.assertEqual(self.task.score(self.task.answer), 1)
        for bad in (True, None, float("nan"), float("inf"), self.task.answer + 1):
            self.assertEqual(self.task.score(bad), 0)

    def test_split_task_streams_are_disjoint(self):
        tasks = lab.Tasks(self.s.cfg)
        tr = tasks.make("train", 1, list(self.s.agents))
        te = tasks.make("test", 1, list(self.s.agents))
        self.assertNotEqual(tr.id, te.id)
        self.assertNotEqual(tr.records, te.records)

    def test_no_communication_ablation_blocks_transfer(self):
        self.s.cfg.communication = False
        a, b = list(self.s.agents)[:2]
        self.assertFalse(self.ep.deliver(a, b, self.task.holders[a], "test"))


class EvolutionTests(unittest.TestCase):
    def test_interrupted_episode_resumes_from_last_completed_checkpoint(self):
        cfg = lab.Config(project="teams", agents=4, episodes=5, eval_episodes=0, steps=8, reflection_every=2)
        original = lab.Model.ask

        def interrupt(model, kind, system, observation, fallback, rng):
            if model.events.episode == 2 and kind == "action":
                raise lab.BudgetExceeded("synthetic interruption")
            return original(model, kind, system, observation, fallback, rng)

        with tempfile.TemporaryDirectory() as tmp, patch.object(lab, "write_report"):
            root = Path(tmp)
            lab.run_experiment(cfg, root / "whole")
            with patch.object(lab.Model, "ask", interrupt):
                result = lab.run_experiment(cfg, root / "interrupted")
            self.assertEqual(result["status"], "budget_exhausted")
            lab.run_experiment(cfg, root / "resumed", root / "interrupted" / "checkpoint.json")

            def stable(x):
                if isinstance(x, dict):
                    return {k: stable(v) for k, v in x.items() if k != "latency_seconds"}
                if isinstance(x, list):
                    return [stable(v) for v in x]
                return x

            whole = json.loads((root / "whole" / "frozen_population.json").read_text())
            resumed = json.loads((root / "resumed" / "frozen_population.json").read_text())
            self.assertEqual(stable(whole), stable(resumed))

    def test_evaluation_never_updates_population(self):
        s = society(project="teams", agents=4, steps=16)
        s.labor_market()
        s.assign_novice_bids(list(s.agents))
        before = copy.deepcopy(s.snapshot())
        before.pop("random_state")
        task = lab.Tasks(s.cfg).make("test", 0, list(s.agents))
        lab.Episode(s, task, True).run()
        after = s.snapshot()
        after.pop("random_state")
        self.assertEqual(before, after)

    def test_snapshot_roundtrip_preserves_rng_and_membership(self):
        s = society(project="teams")
        a, b = list(s.agents)[:2]
        t = s.found(a)
        s.hire(t, b, 0.1)
        raw = json.loads(lab.dumps(s.snapshot()))
        other = lab.Society.from_snapshot(raw, lab.Events(), s.model)
        self.assertEqual(lab.dumps(s.snapshot()), lab.dumps(other.snapshot()))
        self.assertEqual(s.rng.random(), other.rng.random())

    def test_bankruptcy_births_have_unique_ids_and_conserve_ledger(self):
        s = society(agents=4, mutation_rate=0)
        ids = set(s.agents)
        for aid in ids:
            s.ledger.transfer(aid, "house", 100, "test", debt=True)
        s.end_episode()
        self.assertEqual(len(s.agents), 4)
        self.assertFalse(ids & set(s.agents))
        self.assertEqual(s.deaths, 4)
        s.ledger.audit()

    def test_adaptive_rule_uses_aggregates_and_obeys_step_bound(self):
        s = society(project="institutions")
        s.last_metrics = [
            dict(score=0, gini=0.2, largest_team_share=0.9, isolate_fraction=0.1, communication_bytes=200)
        ]
        old = s.cfg.coordination_cost
        s.institution()
        self.assertAlmostEqual(s.cfg.coordination_cost, old * 1.2)
        e = s.events.rows[-1]
        self.assertNotIn("private_memory", e["observation"])

    def test_scripted_stream_reproducible(self):
        answers = []
        for _ in range(2):
            s = society(seed=21, agents=4, steps=20)
            task = lab.Tasks(s.cfg).make("train", 0, list(s.agents))
            r = lab.Episode(s, task, False).run()
            r.pop("latency_seconds")
            answers.append((r, copy.deepcopy(s.ledger.balances)))
        self.assertEqual(answers[0], answers[1])


class MetricsTests(unittest.TestCase):
    def test_star_center_betweenness_and_centralization(self):
        ids = list("abcd")
        m = lab.network_metrics(ids, {("a", x): 1 for x in "bcd"}, {a: None for a in ids})
        self.assertAlmostEqual(m["degree_centralization"], 1)
        self.assertAlmostEqual(m["betweenness"]["a"], 1)
        self.assertEqual(m["isolate_fraction"], 0)

    def test_disjoint_cliques_are_modular(self):
        ids = list("abcdef")
        edges = {(a, b): 1 for group in ("abc", "def") for a in group for b in group if a < b}
        m = lab.network_metrics(ids, edges, {a: None for a in ids})
        self.assertAlmostEqual(m["modularity"], 0.5)

    def test_no_edges_is_not_evidence_of_a_hierarchy(self):
        m = lab.network_metrics(list("abc"), {}, dict.fromkeys("abc"))
        self.assertEqual(m["modularity"], 0)
        self.assertEqual(m["degree_centralization"], 0)
        self.assertEqual(m["isolate_fraction"], 1)

    def test_gini_zero_and_concentrated(self):
        self.assertEqual(lab.gini([2, 2, 2]), 0)
        self.assertAlmostEqual(lab.gini([0, 0, 3]), 2 / 3)
        self.assertEqual(lab.gini([0, 0, 0]), 0)


class ProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                cls.requests += 1
                cls.payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                self.send_response(cls.status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {
                            "choices": [{"message": {"content": cls.content}}],
                            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "cost": 0.00001},
                            "model": "fake",
                        }
                    ).encode()
                )

            def log_message(self, *args):
                pass

        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        type(self).requests = 0
        type(self).status = 200
        type(self).content = '{"kind":"think","text":"ok"}'
        cfg = lab.Config(
            provider="compatible",
            base_url=f"http://127.0.0.1:{self.server.server_port}/v1",
            api_key_env="SOCIETIES_TEST_ABSENT_KEY",
            max_usd=1,
            max_calls=1,
        )
        self.model = lab.Model(cfg, lab.Events(), None)

    def test_actual_http_payload_and_usage(self):
        answer = self.model.ask("action", "system", {"public": "question"}, {}, random.Random(1))
        self.assertEqual(answer["kind"], "think")
        self.assertEqual(self.model.calls, 1)
        self.assertEqual(self.model.tokens, {"input": 5, "output": 3})
        self.assertEqual(type(self).payload["max_tokens"], 700)
        self.assertGreater(self.model.reserved_usd, self.model.reported_usd)

    def test_budget_stops_before_second_request(self):
        self.model.ask("action", "system", {}, {}, random.Random(1))
        with self.assertRaises(lab.BudgetExceeded):
            self.model.ask("action", "system", {}, {}, random.Random(1))
        self.assertEqual(type(self).requests, 1)

    def test_dollar_cap_stops_before_any_request(self):
        self.model.cfg.max_usd = 0.00000001
        with self.assertRaises(lab.BudgetExceeded):
            self.model.ask("action", "system", {}, {}, random.Random(1))
        self.assertEqual(type(self).requests, 0)

    def test_invalid_json_does_not_fall_back_to_script(self):
        type(self).content = "not json"
        answer = self.model.ask("action", "system", {}, {"kind": "submit", "answer": 123}, random.Random(1))
        self.assertEqual(answer, {})

    def test_nonfinite_json_is_invalid(self):
        type(self).content = '{"answer":NaN}'
        self.assertEqual(self.model.ask("action", "system", {}, {}, random.Random(1)), {})

    def test_http_failure_keeps_reservation_no_retry(self):
        type(self).status = 500
        with self.assertRaises(lab.ProviderError):
            self.model.ask("action", "system", {}, {}, random.Random(1))
        self.assertEqual(type(self).requests, 1)
        self.assertGreater(self.model.reserved_usd, 0)


class DataTests(unittest.TestCase):
    def test_hiddenbench_split_excludes_scenario_duplicates(self):
        path = lab.ROOT / "data" / "hiddenbench.json"
        if not path.exists():
            self.skipTest("HiddenBench not downloaded")
        t = lab.Tasks(lab.Config(benchmark="hiddenbench", dataset=str(path)))
        sets = [{t.scenario_key(r) for r in t.dataset_rows(split)} for split in ("train", "validation", "test")]
        self.assertTrue(all(sets))
        self.assertFalse(sets[0] & sets[1] or sets[1] & sets[2] or sets[0] & sets[2])

    def test_jsonl_cross_split_duplicates_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tasks.jsonl"
            rows = [
                {"id": i, "public": {"question": "same"}, "answer": 0, "split": split}
                for i, split in enumerate(("train", "validation", "test"))
            ]
            path.write_text("\n".join(map(json.dumps, rows)))
            with self.assertRaises(ValueError):
                lab.Tasks(lab.Config(benchmark="jsonl", dataset=str(path)))

    def test_invalid_config_fails_early(self):
        for cfg in (
            lab.Config(alpha=0.8),
            lab.Config(agents=0),
            lab.Config(provider="openrouter"),
            lab.Config(comm_out=math.nan),
        ):
            with self.assertRaises(ValueError):
                cfg.validate()

    def test_compatible_endpoint_cannot_inherit_openrouter_key(self):
        with self.assertRaises(ValueError):
            lab.Config(provider="compatible", base_url="https://example.org/v1", max_usd=1).validate()


if __name__ == "__main__":
    unittest.main()
