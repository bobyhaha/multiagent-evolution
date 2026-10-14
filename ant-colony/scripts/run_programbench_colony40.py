"""A bounded colony sharing the original authorized campaign ledger (40 agents by default)."""

import argparse
from collections import Counter
from decimal import Decimal
import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from ant_colony.campaign_budget import Ledger
from ant_colony.config import ColonyConfig
from ant_colony.storage import audit
from run_programbench_repaired import financial_failure, write


def experiment_config(base, *, bank_contacts=2, manager_contacts=2, max_children=2, model_mix="mixed", hierarchy_bias=False, quality_first=False, team_sharing=False, open_contact_rounds=0, adaptive_communication=False, strict_outputs=True, work_contracts=False, runtime_control=False, total_agents=40, max_total_agents=64):
    if (type(total_agents) is not int or type(max_total_agents) is not int
            or not 2 <= total_agents <= max_total_agents <= 64):
        raise ValueError("Total agents must satisfy 2 <= initial <= maximum <= 64, including the bank")
    if model_mix == "mixed" and total_agents != 40:
        raise ValueError("Custom population requires all-astra model mix")
    if model_mix not in {"mixed", "all-astra"}:
        raise ValueError("Unknown model mix")
    cfg = {**base, "initial_agents": total_agents - 1, "max_agents": max_total_agents - 1, "max_rounds": 60,
           "initial_models": ["astra"] * 3 + ["sol"] * 16 + ["luna"] * 20,
           "bank_model": "astra", "funding_recovery": True, "persistent_teams": True,
           "bank_finalization": True, "request_pricing": True, "event_driven_bank": True,
           "standing_grants": True, "progress_control": True,
           "coordination_max_output_tokens": 4096, "coordination_context_bytes": 32000,
           "bank_review_interval": 4, "standing_grant_rounds": 6, "stagnation_rounds": 6,
           "bank_contacts": bank_contacts, "manager_contacts": manager_contacts,
           "max_children": max_children, "max_depth": 6, "hierarchy_bias": hierarchy_bias}
    cfg["worker_models"] = list(cfg["worker_models"])
    if model_mix == "all-astra":
        cfg["initial_models"] = ["astra"] * cfg["initial_agents"]
        cfg["worker_models"] = ["astra"]
    if quality_first:
        cfg.update(quality_first=True, cost_mode="api_usd", rent_per_round=0,
                   discovery_budget=200_000_000, discovery_contacts=8, discovery_turns=3,
                   message_contacts=4, trial_max_output_tokens=16_384, text_bytes=1800,
                   max_grant=60_000_000, grant_rounds=16)
    cfg["team_sharing"] = team_sharing
    cfg["open_contact_rounds"] = open_contact_rounds
    cfg["adaptive_communication"] = adaptive_communication
    cfg["strict_outputs"] = strict_outputs
    cfg["work_contracts"] = work_contracts
    cfg["runtime_control"] = runtime_control
    if work_contracts:
        cfg["coordination_context_bytes"] = cfg["context_bytes"]
    ColonyConfig.from_dict(cfg)
    return cfg


def check_admission(accounting, cap, episode_ceiling=Decimal(15)):
    if accounting["blocked"]:
        raise ValueError("Unresolved prior billing; no experiment may start")
    if not Decimal(0) < cap <= episode_ceiling <= Decimal(200):
        raise ValueError("This experiment is capped at $" + str(episode_ceiling))
    # Live reservations are included. Existing future episode caps are ceilings,
    # not guarantees; every controller uses the durable authorized ceiling.
    if Decimal(str(accounting["accounted_usd"])) + cap > Decimal(str(accounting.get("ceiling_usd", 100))):
        raise ValueError("Insufficient shared campaign headroom for the new run")


def check_attempt_budget(ledger, previous_attempts, total, new_cap):
    """All prior attempt ceilings and this cap fit one experiment total."""
    if isinstance(previous_attempts, str):
        previous_attempts = [previous_attempts]
    previous_attempts = list(previous_attempts or [])
    if not previous_attempts and total is None:
        return None
    if not previous_attempts or total is None or not Decimal(0) < total <= Decimal(str(ledger.limit)):
        raise ValueError("Supply prior attempts and a positive experiment total within the campaign ceiling")
    attempts, previous_ceiling = [], Decimal(0)
    for previous_attempt in previous_attempts:
        account = ledger.summary(previous_attempt)
        if account['pending'] or account['blocked']:
            raise ValueError("Previous attempt still has pending or unresolved requests")
        with ledger.connect() as db:
            old = db.execute('SELECT cap FROM runs WHERE id=?', (previous_attempt,)).fetchone()
        if old is None:
            raise ValueError("Unknown previous attempt " + previous_attempt)
        sealed_cap = Decimal(str(old['cap']))
        previous_ceiling += sealed_cap
        attempts.append({'id': previous_attempt, 'sealed_cap_usd': str(sealed_cap),
                         'accounting': account})
    if previous_ceiling + new_cap > total:
        raise ValueError("Combined attempt ceilings exceed the total experiment budget")
    return {'ids': previous_attempts, 'sealed_cap_usd': str(previous_ceiling),
            'attempts': attempts}


def campaign_failure(accounting, global_accounting, check, events):
    # A conservatively held timeout stops only its own episode. Missing audits,
    # unknown failures, pending calls, and actual contract violations remain global.
    if global_accounting["blocked"]:
        return True
    isolated = accounting.get("quarantined_timeouts", 0) > 0
    adjusted = {**accounting, "blocked": accounting["blocked"] and not isolated}
    return financial_failure(adjusted, check, events)


def check_episode(ledger, ident):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,95}", ident):
        raise ValueError("Episode ID must be a short lowercase name without path separators")
    with ledger.connect() as db:
        if db.execute("SELECT 1 FROM runs WHERE id=?", (ident,)).fetchone():
            raise ValueError("Episode ID already exists in the shared ledger; use a fresh ID")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--prior-study", type=Path, required=True)
    parser.add_argument("--max-usd", type=Decimal, default=Decimal(15))
    parser.add_argument("--episode-id", default="v3-colony40-xsv")
    parser.add_argument("--bank-contacts", type=int, default=2)
    parser.add_argument("--manager-contacts", type=int, default=2)
    parser.add_argument("--max-children", type=int, default=2)
    parser.add_argument("--total-agents", type=int, default=40, help="Initial population INCLUDING the bank")
    parser.add_argument("--max-total-agents", type=int, default=64, help="Maximum population INCLUDING the bank")
    parser.add_argument("--model-mix", choices=("mixed", "all-astra"), default="mixed")
    parser.add_argument("--hierarchy-bias", action="store_true")
    parser.add_argument("--quality-first", action="store_true")
    parser.add_argument("--team-sharing", action="store_true")
    parser.add_argument("--open-contact-rounds", type=int, default=0)
    parser.add_argument("--adaptive-communication", action="store_true")
    parser.add_argument("--continue-artifact", type=Path, help="Continue the ungraded code of this prior episode with fresh agents")
    parser.add_argument("--inference-deadline", type=float)
    parser.add_argument("--tolerate-transient-errors", action="store_true")
    parser.add_argument("--max-rounds", type=int, default=60)
    parser.add_argument("--runtime-control", action="store_true",
                        help="Bounded recovery calls, explicit cancellation and incomplete checkpoint selection")
    parser.add_argument("--work-contracts", action="store_true",
                        help="Frozen artifact contracts, runtime check receipts and recipient acceptance")
    parser.add_argument("--strict-outputs", action=argparse.BooleanOptionalAction, default=True,
                        help="Phase-specific output contracts (default: on; --no-strict-outputs for legacy runs)")
    parser.add_argument("--previous-attempt", action="append", dest="previous_attempts",
                        help="Prior attempt in this experiment; may be repeated")
    parser.add_argument("--experiment-total-usd", type=Decimal)
    parser.add_argument("--prompt-key", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.max_rounds <= 60:
        raise ValueError("Round cap must be between 1 and 60")
    code, study, prior = Path(__file__).resolve().parents[1], args.out.resolve(), args.prior_study.resolve()
    previous = json.loads((prior / "study.json").read_text())
    ledger_path = Path(previous["ledger"])
    if not ledger_path.is_file() or (ledger_path.parent / "STOP").exists():
        raise RuntimeError("Original ledger must exist and no global STOP may be present")
    ledger = Ledger(ledger_path, parallel=True)
    check_episode(ledger, args.episode_id)
    lock = (ledger_path.parent / (args.episode_id + "-controller.lock")).open("a+b")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    check_episode(ledger, args.episode_id)
    before = ledger.summary()
    episode_ceiling = (Decimal(200) if args.quality_first else Decimal(100)) if args.model_mix == "all-astra" else Decimal(15)
    check_admission(before, args.max_usd, episode_ceiling)
    prior_attempt = check_attempt_budget(ledger, args.previous_attempts, args.experiment_total_usd, args.max_usd)
    if args.prompt_key and not os.environ.get("OPENROUTER_API_KEY"):
        os.environ["OPENROUTER_API_KEY"] = getpass.getpass("OpenRouter API key (not saved): ")
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY is required")
    before = ledger.summary()
    check_admission(before, args.max_usd, episode_ceiling)
    prior_attempt = check_attempt_budget(ledger, args.previous_attempts, args.experiment_total_usd, args.max_usd)
    study.mkdir(parents=True, exist_ok=False)
    runtime = study / "runtime"
    for name in ("ant_colony", "hayekmas"):
        shutil.copytree(code / name, runtime / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (runtime / "scripts").mkdir()
    for name in ("run_programbench_campaign.py", Path(__file__).name, "run_programbench_repaired.py"):
        shutil.copyfile(code / "scripts" / name, runtime / "scripts" / name)
    cfg = experiment_config(json.loads((code / "configs/programbench-mixed-high.json").read_text()),
                            bank_contacts=args.bank_contacts, manager_contacts=args.manager_contacts,
                            max_children=args.max_children, model_mix=args.model_mix,
                            hierarchy_bias=args.hierarchy_bias, quality_first=args.quality_first, team_sharing=args.team_sharing, open_contact_rounds=args.open_contact_rounds, adaptive_communication=args.adaptive_communication, strict_outputs=args.strict_outputs, work_contracts=args.work_contracts, runtime_control=args.runtime_control, total_agents=args.total_agents, max_total_agents=args.max_total_agents)
    cfg["max_rounds"] = args.max_rounds
    write(study / "main-config.json", cfg)
    model_settings = json.loads((code / "configs/programbench-high-models.json").read_text())
    allowed_models = set(cfg["worker_models"]) | {cfg["bank_model"]}
    write(study / "models.json", {name: settings for name, settings in model_settings.items()
                                  if name in allowed_models})
    hashes = {str(p.relative_to(runtime)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in runtime.rglob("*") if p.is_file()}
    write(study / "source-hashes.json", hashes)
    row = {"id": args.episode_id, "task": "xsv", "cap": float(args.max_usd),
           "solo": False, "solo_model": None, "pilot": False}
    society = Counter(cfg["initial_models"])
    society[cfg["bank_model"]] += 1
    plan = {"status": "running", "benchmark": "ProgramBench", "ledger": str(ledger_path),
            "prior_study": str(prior), "reasoning_effort": "high", "max_rounds": args.max_rounds,
            "initial_society": {**society, "bank_included": True}, "model_mix": args.model_mix,
            "max_population_including_bank": cfg["max_agents"] + 1, "max_direct_children": cfg["max_children"], "max_depth": 6,
            "bank_contacts": cfg["bank_contacts"], "manager_contacts": cfg["manager_contacts"],
            "allocated_maximum_usd": float(args.max_usd), "global_ceiling_usd": before["ceiling_usd"],
            "accounting_at_start": before, "max_concurrent_api_requests_shared": 2,
            "episodes": [row], "fresh_seed": True,
            "selection": "One final integrated artifact; native hidden tests supply no feedback to agents.",
            "budget_amendment": f"User authorized a fresh {args.total_agents}-agent run including the bank, capped at ${args.max_usd}. The existing ${before['ceiling_usd']} cumulative campaign ceiling, prior charges and reservations remain in force.",
            "hypothesis": "Outcome ownership prompts and explicit, reviewed recruitment shortfalls let funded workers initiate useful recursive delegation. Renewals preserve the existing outcome, and a rejected top-up defers rather than permanently bars a funded worker from requesting support.",
            "emergence_metrics": ["working agents by model", "introductions routed and forwarded", "recruitment funding requests and review outcomes", "recruitment after funding", "trial hires", "hires and spawns", "peak depth", "productive workers at depth >=2", "standing grants used", "coordination cost share", "context bound", "final score and actual cost"],
            "limitations": "Prompt changes, recruitment funding, and renewal fixes change together; one fresh run cannot isolate their individual effects. Population, horizon and episode ceiling are explicit in this plan and may differ from earlier conditions. Compare explicit configured contact and child caps. A deeper tree alone is not evidence of useful emergence."}
    if args.model_mix == "all-astra":
        plan["hypothesis"] = "With the latest delegation mechanism unchanged, an all-Astra society may improve verified quality and autonomous collaboration relative to the mixed-model v6 run. Initial workers and any new spawns must use Astra."
        plan["limitations"] = "Model-specific reserves, example budgets and affordable participation depend on the configured population and model set. Initial population does not imply funded participation; additional protocol flags are recorded separately. This is one fresh run with no controlled provider seed; equal dollar ceilings do not imply equal actual cost or calls. Compare the recorded caps and observed stopping rounds."
        plan["budget_amendment"] = f"User authorized this all-Astra version with a ${args.max_usd} attempt ceiling within the existing ${before['ceiling_usd']} cumulative campaign cap; no prior charges or holds are reset."
    plan['hierarchy_bias'] = cfg['hierarchy_bias']
    plan['quality_first'] = cfg['quality_first']
    if cfg['hierarchy_bias']:
        plan['hypothesis'] = "An explicitly stated preference for useful hierarchical delegation, inherited by the bank and every worker, may encourage recursive teams under the authorized all-Astra budget."
        plan['limitations'] = "This invocation enables hierarchy bias. Compare recorded model composition, budgets and prompting; this is not automatically a model-only or equal-budget comparison. A deeper tree alone is not useful emergence. Initial population is not active population; native results are unavailable to the agents."
    if args.quality_first:
        plan['hypothesis'] = "Quality-first objectives, sponsored discovery, direct offers, addressable bounded messages and recursive ownership may improve useful participation and task correctness."
        plan['limitations'] = "A new compound mechanism treatment: objective, prompts, admission, communication, hierarchy preference and budget differ. One run with no controlled provider seed; compare outcomes without causal attribution to a single change."
        plan['budget_amendment'] = f"User authorized a fresh quality-first {args.total_agents}-Astra experiment capped at ${args.max_usd}, within the existing ${before['ceiling_usd']} campaign including all historical spending and unresolved reservations. This is a new attempt, not restored agent state."
        plan['discovery'] = {k:cfg[k] for k in ('discovery_budget','discovery_contacts','discovery_turns')}
    if args.team_sharing:
        plan['team_sharing'] = True
        plan['hypothesis'] = "Shared evidence retrieval, team-local messages, temporary cross-team liaisons, per-recipient delivery and bounded stagnation recovery improve integration and completeness."
        plan['limitations'] = "A compound protocol treatment compared with v10; one fresh run, no controlled provider seed. Population and horizon are recorded explicitly; earlier runs may use different values. Existing campaign commitments still constrain admission. Compare actual cost, stopping reason and native counts; do not infer causality from tree depth."
        plan['emergence_metrics'] += ['shared posts and retrieved entries', 'liaison appointments', 'message delivery failures by reason', 'introduction queue', 'stagnation recovery']
    if args.open_contact_rounds:
        plan['open_contact_rounds'] = args.open_contact_rounds
        plan['hypothesis'] = f"Allowing bounded direct messages and collaborator lookup across all live workers in the first {args.open_contact_rounds} rounds may improve initial team formation; subsequent rounds use team-local and liaison communication."
        plan['limitations'] = "Opening contact is enabled for the configured initial window. Treat this run as an uncontrolled experiment; use its recorded population, structural limits, seed status and budgets when comparing. Historical campaign spending and reservations remain accounted."
    plan["strict_outputs"] = args.strict_outputs
    plan["work_contracts"] = args.work_contracts
    plan["runtime_control"] = args.runtime_control
    if args.runtime_control:
        plan["hypothesis"] += " Bounded control calls may unblock stranded allowance and sleeping executors; host evidence may reduce repeated checks."
        plan["limitations"] += " Runtime controls and durable evidence are a compound treatment. Prompts are frozen; this is not a controlled causal comparison."
    plan["inference_deadline_epoch"] = args.inference_deadline
    plan["tolerate_transient_errors"] = args.tolerate_transient_errors
    if args.adaptive_communication:
        plan['adaptive_communication'] = True
        plan['communication_cycle'] = {k: cfg[k] for k in ('open_contact_rounds', 'communication_local_rounds', 'communication_exchange_rounds', 'communication_bridge_rounds')}
        plan['hypothesis'] = "Stable teams with recurring bounded exchange windows and consensual expiring peer bridges may improve integration and adaptation without unbounded agent contexts."
        plan['limitations'] = "Communication schedule and bridge permissions change together. One fresh run cannot isolate either effect; communication does not alter admission/funding or prove useful specialization."
        plan['emergence_metrics'] += ['communication phases', 'bridge requests/acceptance/expiry', 'bridge-assisted verified work']
    if args.strict_outputs:
        plan['hypothesis'] += " Strict phase-specific output contracts may reduce wasted malformed replies."
        plan['limitations'] += " Replies are validated locally, with no fallback or automatic paid retry. The output-contract treatment must be included when comparing protocols."
    if args.work_contracts:
        plan['hypothesis'] += " Frozen work contracts and recipient-reviewed verification receipts may improve handoff reliability."
        plan['limitations'] += " Work contracts add calls and context and use the existing full context ceiling for coordination; acceptance is not benchmark correctness. Compare against strict-output-only runs with matched tasks, models, budgets and horizons."
    if args.work_contracts:
        plan['emergence_metrics'] += ['work contracts created', 'verification receipts', 'accepted and revised handoffs', 'stale evidence invalidations']
    if args.continue_artifact:
        plan['fresh_seed'] = False
        plan['artifact_continuation'] = str(args.continue_artifact.resolve())
        plan['agent_state_restored'] = False
        plan['budget_amendment'] += ' This attempt continues an explicitly authorized ungraded code artifact; only agent state is fresh.'
        plan['limitations'] += " Continues the last integrated ungraded artifact, retaining public probe usage; agents reform teams and reopen the two-round contact window. This is not a fresh-seed benchmark or full-state resume."
    if prior_attempt:
        plan['previous_attempt'] = prior_attempt
        plan['experiment_total_cap_usd'] = str(args.experiment_total_usd)
        plan['budget_amendment'] += (f" Prior attempts {args.previous_attempts} are retained and charged against the same "
                                     f"${args.experiment_total_usd} experiment total. Their combined sealed ledger "
                                     "ceilings plus this attempt ceiling cannot exceed that total. This is a fresh "
                                     "attempt, not restoration of live agent state.")
    write(study / "study.json", plan)
    write(study / "budget-amendment.json", {
        "prior_study": str(prior), "global_ceiling_usd": before["ceiling_usd"],
        "accounting_before": before, "new_episode_cap_usd": str(args.max_usd),
        "prior_attempts": prior_attempt["attempts"] if prior_attempt else [],
        "experiment_total_cap_usd": str(args.experiment_total_usd) if prior_attempt else None,
        "prior_attempt_sealed_caps_usd": prior_attempt["sealed_cap_usd"] if prior_attempt else None,
        "scope": plan["budget_amendment"],
    })
    env = dict(os.environ, PYTHONPATH=str(runtime),
               ANT_COLONY_NATIVE_LOCK=str(ledger_path.parent / "native-evaluation.lock"))
    command = [sys.executable, str(runtime / "scripts/run_programbench_campaign.py"),
               "--task", str(code.parent / "code-testing-v1/datasets/programbench-xsv/task.json"),
               "--config", str(study / "main-config.json"), "--models", str(study / "models.json"),
               "--out", str(study / row["id"]), "--ledger", str(ledger_path),
               "--evaluator-python", str(code.parent / "code-testing-v1/.venv/bin/python"),
               "--max-usd", str(args.max_usd)]
    if args.inference_deadline is not None:
        command += ["--inference-deadline", str(args.inference_deadline)]
    if args.tolerate_transient_errors:
        command.append("--tolerate-transient-errors")
    if args.continue_artifact:
        command += ["--continue-artifact", str(args.continue_artifact.resolve())]
    print("Starting " + row["id"] + f": {args.total_agents} initial agents, up to {args.max_rounds} rounds, ceiling $" + str(args.max_usd), flush=True)
    try:
        with (study / (row["id"] + ".log")).open("x") as log:
            result = subprocess.run(command, cwd=runtime, env=env, stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
        directory = study / row["id"]
        event_file, report_file = directory / "events.jsonl", directory / "report.json"
        events = [json.loads(line) for line in event_file.read_text().splitlines()] if event_file.exists() else []
        report = json.loads(report_file.read_text()) if report_file.exists() else {}
        check = audit(event_file) if report_file.exists() else {}
        account = ledger.summary(row["id"])
        unsafe = campaign_failure(account, ledger.summary(), check, events)
        if unsafe:
            (ledger_path.parent / "STOP").write_text("Financial/inference-contract failure in " + row["id"] + ".\n")
        healthy = result.returncode == 0 and report.get("status") == "completed" and check.get("complete_evaluation") and not unsafe
        plan["status"] = "completed" if healthy else "stopped_transport" if account.get("quarantined_timeouts") and not unsafe else "failed_episode"
        write(study / "outcomes.json", [{"id": row["id"], "status": plan["status"], "report": report,
                                          "audit": check, "accounting": account, "returncode": result.returncode}])
    except BaseException as exc:
        plan["status"], plan["error_type"] = "controller_failed", type(exc).__name__
        raise
    finally:
        write(study / "study.json", plan)
        write(study / "budget.json", ledger.summary())
        ledger.close()
        lock.close()


if __name__ == "__main__":
    main()
