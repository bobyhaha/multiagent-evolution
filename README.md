# Multiagent Evolution

This repository contains the full multiagent research workspace:

- **[EoM and voluntary teams](eom-teams/TEAMS.md):** the complete EoM codebase,
  team auctions, independent draft/check/revise experiments, evaluation tools,
  tests, and interactive interaction replays. Start in `eom-teams/`.
- **Artificial Societies Lab:** the capital, teams, and institutions experiments
  below, implemented at the repository root.
- **[Research results](RESULTS.md):** saved analysis and figures under `research/`.

The EoM source is included as ordinary files, not a submodule. It retains its
upstream license and attribution; this import includes team-extension commit
`c3b99190b20a73b350d91104db7d65a87d02b8c6`. Local credentials, environments,
download caches, and generated run logs are excluded from version control.

## Artificial Societies Lab

Three runnable research projects share one inspectable implementation in `test.py`.
The research question is whether incentives and limited information can produce
useful organizations, and under which conditions they fail.

| Project | Mechanism being tested | Main comparison |
|---|---|---|
| `capital` | Wealth buys private reflection; strategies mutate and agents are replaced | Paid investment versus no investment, with economic selection ablated separately |
| `teams` | Voluntary teams, escrowed temporary labor contracts, team budgets, shared memory, bounded summaries | Communication-price ratio, organizational cost, and individual/team/social reward mixture |
| `institutions` | A bounded rule controller sees aggregate outcomes and team summaries | Fixed versus adaptive institutions, with and without a workload shock |

The default backend is a **scripted simulator**, clearly labeled in every report.
It validates mechanisms and supplies a transparent control; its results are not
evidence that an LLM spontaneously discovers organizations. OpenRouter and
OpenAI-compatible local model servers use the same observation/action interface.

## Run locally

Python 3.11+ is sufficient; no packages are needed for the engine.

```bash
git clone https://github.com/bobyhaha/multiagent-evolution.git
cd multiagent-evolution
python3 test.py run --config configs/capital.json --out runs/my-capital
python3 test.py run --config configs/teams.json --out runs/my-teams
python3 test.py run --config configs/institutions.json --out runs/my-institutions
python3 -m unittest discover -s tests -v
```

Each output path must be new, so a run never silently overwrites another.
To generate network and trajectory figures, install the optional plotting packages:

```bash
uv sync --extra plots --extra dev
uv run test.py run --config configs/teams.json --out runs/teams-with-plots
```

`report.html` links to the event log, measurements, and manifest. Outputs include:

- `events.jsonl`: economic transactions, actions, observed communication, births,
  deaths, contracts, reflection, rule changes, and provider usage.
- `metrics.csv` / `metrics.json`: performance, information coverage, network
  measures, wealth, memberships, graph snapshots, and descriptive regime flags.
- `checkpoint.json`: last completed training episode, including RNG state.
- `frozen_population.json`: final population used for independent test episodes.
- `usage.json`: API call count, conservative reservation, reported spend, tokens.
- `manifest.json`: full configuration, code hash, dataset hash, runtime version.

## Compare mechanisms

```bash
python3 test.py sweep --config configs/teams.json \
  --grid configs/phase_grid.json --seeds 7,17,29,43,59 --out runs/phase-study

python3 test.py sweep --config configs/capital.json \
  --grid configs/capital_ablations.json --seeds 7,17,29 --out runs/capital-ablation

python3 test.py sweep --config configs/teams.json \
  --grid configs/reward_grid.json --seeds 7,17,29 --out runs/reward-mixtures

python3 test.py sweep --config configs/institutions.json \
  --grid configs/institution_ablations.json --seeds 7,17,29 --out runs/institution-study
```

Confidence intervals resample **independent population seeds**, not correlated
turns. Paired comparisons use the same task seeds. A small parameter grid is a
screening experiment, not proof of a phase transition. The sweep budget is shared
across its child runs; it is not multiplied by the number of cells.

Available routing controls: `market`, `eom`, `random`, `round_robin`, `star`, `ring`,
`fixed_teams`, and `single`. `eom` is an economic-mechanism baseline adapted to these
environments, **not a reproduction of the paper's benchmark scores**. `single`
receives all evidence and is an information-access ceiling. Star/ring constrain
message recipients and use round-robin scheduling. Other ablations can retain
economic selection; inspect each manifest rather than assuming an entire
algorithm was replaced.

## Real benchmark and frozen evaluation

The downloaded `data/hiddenbench.json` contains the 65 public HiddenBench items.
The adapter performs exact option scoring. It uses a custom grouped 60/20/20
train/validation/test partition, so its scores must not be presented as official
HiddenBench leaderboard results. Public problem variants stay in the same split.

```bash
python3 test.py run --project teams --benchmark hiddenbench \
  --dataset data/hiddenbench.json --agents 4 --episodes 12 --eval-episodes 8 \
  --out runs/hiddenbench-smoke

python3 test.py evaluate --checkpoint runs/my-teams/frozen_population.json \
  --split validation --eval-episodes 10 --out runs/validation

python3 test.py evaluate --checkpoint runs/my-teams/frozen_population.json \
  --intervention remove_richest --eval-episodes 10 --out runs/remove-richest
```

Compare `remove_richest` with `remove_random` and no removal, using matched seeds.
Removal loses that agent's private shard; it is a combined capability/information
failure intervention, not a clean causal estimate of brokerage value.

Evaluation freezes prompts, wealth, teams, contracts, reputation, and rules. Each
task runs on an independent copy. It still enforces a fresh virtual resource
envelope derived from frozen wealth, without updating the ledger. Test labels are
never included in agent/reflection observations. Use validation to choose
settings before reading test results.

External exact-answer tasks can use `--benchmark jsonl --dataset FILE`:

```json
{"id":"task-1","split":"train","public":{"description":"Question","possible_answers":["A","B"]},"records":[{"id":"f0","text":"Private evidence"}],"answer":"B"}
```

Supply distinct items for all three splits. Answers are numeric (absolute
tolerance 1e-8) or exact strings after trimming/case normalization. Symbolic MATH
equivalence and code-execution benchmarks need separate graders; they are not
silently approximated here. `sum`, `max`, and `path` are original procedural
diagnostics, not an implementation of Silo-Bench.

## Use Qwen through OpenRouter

Set `OPENROUTER_API_KEY` outside the code. See [PROVIDERS.md](PROVIDERS.md) for the
current pricing snapshot and SF Compute deployment path.

```bash
python3 test.py models --out research/qwen-model-snapshot.json
python3 test.py run --project capital --provider openrouter \
  --model qwen/qwen3-32b --agents 4 --episodes 4 --eval-episodes 2 --steps 16 \
  --max-tokens 700 --max-calls 150 --max-usd 10 \
  --input-usd-per-million 1 --output-usd-per-million 5 \
  --out runs/qwen-pilot
```

`--llm-triggers` replaces the local cadence trigger with an LLM eligibility check
on the agent's local observation. It adds up to N calls per decision step and is a
separate experimental condition. Live JSON failures become invalid actions; the
runner never substitutes a scripted answer. Transport failures stop the run and
preserve the spend reservation. Provider seeds are best-effort, not a guarantee
of deterministic hosted inference.

Resume only from a **completed episode checkpoint** into a new output directory:

```bash
python3 test.py run --checkpoint runs/interrupted/checkpoint.json --out runs/resumed
```

For paid work, keep the prior `usage.json` beside the checkpoint; its counters are
carried forward. `interrupted_state.json` is an audit snapshot of a partial episode,
not an exact mid-episode resume point.

## Where to read next

[RESEARCH.md](RESEARCH.md) records the literature review, project hypotheses,
implementation choices, caveats, and benchmark priorities. [RESULTS.md](RESULTS.md)
records the local checks and simulator findings. [PROVIDERS.md](PROVIDERS.md)
explains live providers and costs. All implementation is local; no paid calls or
GPU provisioning were performed during development.
