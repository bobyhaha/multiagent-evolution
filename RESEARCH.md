# Research design — reviewed September 25, 2026 (Pacific)

The shared conversation frames the problem as **institutional rules → organization
→ collective performance**, with individual, team, and society adaptation. The
implementation makes these three scales separate experiments with a common
environment and measurement interface. This is a research harness and an initial
mechanism model, not a claim that the proposed society already works.

## What was read and inspected

- [Economy of Minds](https://arxiv.org/abs/2606.02859): full HTML paper, including
  its economic rules, evaluation protocol, theoretical discussion, and topology
  appendices. Its fixed bids, predecessor payments, wealth selection, and frozen
  testing are the starting point. Prompt evolution uses a frozen model backbone.
- [Shared conversation](https://chatgpt.com/s/t_6ab6bcc55fa481919c2511bb318a2004):
  read through the browser. Its priorities include temporary contracts, voluntary
  exit, partial memories, costly communication, cognitive investment, multiple
  reward scales, and parameter sweeps rather than imposed organization charts.
- [EoM source](https://github.com/zhentingqi/EoM), inspected at
  `d608a2874340d08b5564cb16d558ffcefa5996a3`: `hayekmas/base/agent.py`,
  `population.py`, `mas.py`, adapter descriptions and configuration. The current
  engine includes multiple bid modes, protected roles, terminal gating and
  optional path rewards. Those additions are not silently treated as the minimal
  paper mechanism.
- [CORAL source](https://github.com/Human-Agent-Society/CORAL), inspected at
  `0123dfb939b35228cf2c1fde224cd0561e727408`: grader contracts, island visibility,
  shared-state checkpoints and worktree isolation. Its useful contribution here
  is a clean separation of agents, evaluation, persistent artifacts and visibility.
  CORAL's coding runtime is not embedded in this simulator. See also the
  [CORAL paper](https://arxiv.org/abs/2604.01658).

The implementation is independent code. Reference repositories are read-only
checkouts under `research/references/` and are ignored by the parent Git repository.

Two limits in EoM matter here: its continuation-value interpretation requires
additional assumptions, and Appendix C.5 explicitly allows externally profitable
cartels to survive. Bankruptcy is not a general anti-collusion theorem. Its
appendix topology analysis primarily studies sequences of auction winners; our
message graph, payment graph, membership structure and lineage are different
objects and are logged separately. [Paper and appendices](https://arxiv.org/html/2606.02859v1).

## Current literature that changes the design

I checked the [September 25 cs.MA listing](https://arxiv.org/list/cs.MA/recent) and
recent primary papers, rather than interpreting “today's literature” as a claim
that every relevant paper appeared today. Some recent papers are preprints.

| Source | Consequence for these experiments |
|---|---|
| [Silo-Bench](https://arxiv.org/abs/2603.01045), March 2026 | Information exchange and successful integration are distinct. Record submitter evidence coverage separately from accuracy. A well-formed network is not a successful collective reasoner. |
| [Proxifield](https://arxiv.org/abs/2609.20889), September 16 | Sparse, adaptive communication is a relevant comparator. Include fixed star/ring controls and agent failure tests. This implementation does not claim to reproduce Proxifield's semantic router. |
| [Rethinking Multi-Agent Collaboration](https://arxiv.org/abs/2609.19759), September 17/18 | Dependency structure matters. Compare distributed aggregation with sequential graph reasoning and a full-information single agent; report cost and task quality together. |
| [Behavior is Not Enough](https://arxiv.org/abs/2609.26481), submitted September 22 | The same behavior can arise through different social mechanisms. Graph patterns and cooperative outcomes alone do not establish norms. Our reports avoid that inference. |
| [Agensh](https://arxiv.org/abs/2609.26781), submitted September 22 | Organization can be studied at large scales with shared work and asynchronous claims. Treat such a harness as a later systems comparator; do not extrapolate an eight-agent sequential auction to 1,024-agent throughput. |
| [What Confidence Routing Is Actually Doing](https://arxiv.org/abs/2609.27822), September 2026 | Routing, probability calibration and commitment are different. Keep fixed bids distinct from model confidence, and record the executed action rather than scoring a preliminary intention. |
| [Social Gym / SPaRTan](https://arxiv.org/abs/2608.09128), August 2026 | Rule-based social-game scores are preferable to a society judging itself. Reflection gains can depend on the backbone; paid reflection needs an ablation rather than an assumed benefit. |
| [AgentSociety](https://arxiv.org/abs/2605.26203), May 2026 | Institutional incentives and decentralized social choice are existing research directions. The prospective contribution here is controlled interaction between labor, communication and multilevel investment, not the first “agent society.” |
| [Emergent social conventions](https://arxiv.org/abs/2410.08948), Science Advances 2025 | Population-level convergence and collective bias warrant measurement independent of individual behavior. Behavioral diversity is a diagnostic, not an added reward term. |
| [SRPO](https://arxiv.org/abs/2609.08452), September 8 | Joint credit assignment matters if this work later trains model weights. This version evolves prompts and policy parameters; it implements no RL weight update or SRPO objective. |
| [PAWS](https://arxiv.org/abs/2609.28547), submitted September 24 | Historical policy-response evaluation offers a future external-validity test. Financial replay is too confounded for the first mechanism-identification experiment. |
| [Codetta](https://arxiv.org/abs/2609.28900), submitted September 24 | Observed communication concentration cannot establish whether coordination is benign or collusive. Our “hub” and “concentration” flags are descriptive and are not collusion detectors. |

Recent-paper abstracts were read for breadth; full HTML was additionally inspected
for Silo-Bench and the September 22–24 papers saved in `research/papers/`. These
papers motivate controls, not a synthesized claim that all their results agree.

## Project 1: cognitive capital under economic selection

**Question:** Does allowing agents to purchase private strategy improvement yield
better held-out task performance per dollar than economic selection alone?

The learned state is an agent's prompt, bounded local memory, behavioral parameters,
fixed bid, and observed relationship history. An auction selects an eligible actor.
The winner pays its bid to the previous actor, or to the house on the first step.
Real API dollars and simulated wealth are separate accounts. Wealth can pay for
reflection, but paying never mechanically raises an answer's probability of being
correct. In live mode, the model must actually produce a more useful strategy.

Reflection sees only the agent's local actions, received messages and outcome
feedback. It does not receive the evaluator's answer. Wealth selection replaces
unsuccessful agents; successful and failed agents can seed variants. No behavior
gets an explicit diversity bonus.

**Primary outcome:** held-out accuracy, accompanied by total inference tokens,
reserved/reported USD and economic resource consumption. Secondary outcomes:
investment frequency, survival, wealth inequality and concentration of acting
turns. The clean factorial comparison toggles investment, payments and evolution.

**Falsification:** reject a cognitive-capital advantage if it vanishes against
an equal-budget non-investing population, or if local reflection merely increases
prompt length without improving held-out accuracy. Compare training expense plus
test expense, not test expense alone.

## Project 2: labor markets and organizational boundaries

**Question:** When do persistent teams provide enough informational benefit to
justify membership and coordination costs?

Teams start absent in the main treatment. Agents can fund a team, accept an offer,
or leave. Contracts have a fixed duration; wages are escrowed upfront, released
per episode, and unused escrow is refunded on exit. An agent cannot belong to two
teams. A solvent team cannot arbitrarily kick out one member. Insolvency dissolves
the organization, while ordinary expiry allows re-hiring or nonrenewal. Founders
hold no permanent ownership of other agents.

The organization cost is

\[
C_T(n)=c_1n+c_2 n(n-1)/2.
\]

Internal publication delivers bounded evidence to current members. External agents
can buy a bounded current team summary; ordinary cross-team messages are more
expensive. Summaries have an actual UTF-8 byte bound, including evidence payload
and framing. This avoids assuming that compressed summaries are free information.
Bandwidth is measured in bytes to remain tokenizer-independent.

The single external reward supply is divided as

\[
R\,[\alpha\text{ to submitter}+\beta\text{ to its treasury}
+\gamma/N\text{ to every agent}],\qquad\alpha+\beta+\gamma=1.
\]

An unaffiliated submitter receives its team share itself. This normalization keeps
the total reward supply fixed when team sizes or reward mixtures change. Team
treasuries may fund a member's private reflection. A team's own reflection sees
team outcomes and public member profiles, never everyone's private histories.

**Primary experiment:** communication ratio × coordination cost, with matched
workload, population size, reward supply, and seed. Follow with reward-mixture,
contract-duration and summary-bandwidth sweeps. Compare evolved membership to
fixed teams; compare communication to star/ring and round-robin controls.

**Falsification:** teams are unhelpful if any accuracy gain costs more than a
full-information agent or if their advantage disappears with equal communication
bandwidth. A larger team is not a success metric.

## Project 3: adaptive institutions and organizational regimes

**Question:** Can limited society-level feedback change economic rules to recover
from a workload shift without concentrating information or control?

At a slower timescale, an institution sees rolling aggregate accuracy, inequality,
team concentration, isolation and communication volume, plus short team summaries.
It may adjust external communication cost and pairwise organizational cost by at
most 20% per review. It cannot select the next actor, edit a private memory, or
assign a role. This is an explicit controller of institutional rules; calling the
whole system fully decentralized would therefore be inaccurate.

Compare fixed/adaptive rules crossed with static/shifting workload. The supplied
shift increases procedural data volume midway through training. The final test
distribution is fixed, so “online recovery from shock” and “final generalization”
are separate questions. Broader task-family shifts can be provided as JSONL data.

The scripted controller is a declared feedback heuristic, not a discovered optimal
institution. In live mode an LLM proposes rule changes through the same bounded
interface. Future outer-loop optimization should select rules on validation only.

## Which structures could form, and how to distinguish them

These are hypotheses about mechanisms, not promised simulator outcomes.

| Candidate organization | Plausible pressure | Evidence needed |
|---|---|---|
| Atomized population | Communication too costly; insufficient joint surplus | Few messages and stable isolation, compared to shuffled/no-communication controls |
| Small specialist teams | Internal communication savings exceed moderate coordination cost | Persistent memberships, varied action profiles, useful within-team exchange, held-out task gains |
| Modular federation | Teams can exchange useful compressed evidence | Communities aligned imperfectly with contracts, useful cross-team exchanges, resilience to member removal |
| Brokerage network | Some agents repeatedly connect otherwise separated information | Betweenness plus novel-evidence delivery; remove broker versus matched random removal |
| Hub-dominated organization | Turn allocation or information favors a few incumbents | Centralization and actor concentration across windows; intervention to distinguish efficiency from a bottleneck |
| Membership monopoly | Increasing returns overwhelm coordination costs | Persistent dominant team share, not just one short-lived large team |
| Cartel or exclusionary coalition | Private group benefit conflicts with global output | Controlled incentive manipulation, price/output evidence and counterfactual deviation tests; graph modularity alone is insufficient |
| Hierarchy | Repeated delegation becomes a stable dependency relation | Directed task/delegation traces and persistence across tasks; message hubs are insufficient |

Implemented measurements include message-network modularity, contractual
modularity, degree centralization, betweenness, cross-team fraction, isolates,
membership distributions, wealth Gini, action-distribution divergence, effective
actor count, turnover and exact task scores. The graph is an undirected projection
of **observed messages** among living agents at episode end. Payments and parentage
remain distinct event types. Greedy modularity search is a deterministic local
heuristic, not a guarantee of optimal community detection.

Use multiple windows and population sizes (e.g. 4, 8, 16, 32), bootstrap independent
population seeds, and test degree-preserving/null-network alternatives before
making a topology claim. A finite-size phase transition needs sustained evidence,
hysteresis or scaling analysis; crossing an arbitrary threshold in one run does not
qualify. Formal coalitions, delegation contracts and normative-expectation probes
are not implemented in this first version.

## Benchmark priorities

1. **Procedural distributed sum, maximum and shortest path:** already implemented,
   inexpensive, unlimited disjoint seed streams and exact scoring. These diagnose
   communication and integration failures; their scripted solver is intentionally
   strong. They are not official Silo-Bench tasks or broad intelligence measures.
2. **[HiddenBench](https://huggingface.co/datasets/YuxuanLi1225/HiddenBench):** real
   natural-language hidden-profile tasks; already downloaded and adapted. Four
   agents are the sensible first setup for its small information partitions.
   Group related scenario variants, inspect all split sizes, and do not repeatedly
   select mechanisms against its small test set. The adapter's custom episode and
   partition protocol differs from the upstream benchmark.
3. **[Silo-Bench](https://arxiv.org/abs/2603.01045):** strongest next benchmark for
   distributed algorithmic coordination. Add its official loader and evaluator
   without claiming the current procedural tasks reproduce it.
4. **[Reasoning Gym](https://github.com/open-thought/reasoning-gym)** and selected
   MATH tasks: useful transfer tests. Procedural generators reduce fixed-benchmark
   reuse. Mathematical equivalence needs an appropriate verifier; our exact
   string grader is insufficient for general MATH answers.
5. **[Social Gym](https://arxiv.org/abs/2608.09128):** next test for bargaining,
   public-goods behavior and conflicting incentives. Requires a simultaneous-action
   game adapter; the current single-submission evaluator is not that adapter.
6. **CORAL/CloudCast or ProgramBench:** later external-validity test of useful
   collective research/code work. Add isolated executable workspaces and trusted
   graders first; do not grant generated code unrestricted access to this laptop.

Finance-Agent-Bench and FrontierScience are useful comparators to EoM, but initial
experiments should avoid confounding market design with search-tool access or
same-model subjective grading. No scores for those benchmarks are fabricated.

## Important implementation boundaries

- All main agents share a frozen backbone. Prompts, local strategies and membership
  evolve; model weights do not. This isolates institutions from training changes.
- The default eligibility rule is a local cadence scaffold. `--llm-triggers` adds
  local model decisions. Cadence, replacement, random exploration and the scripted
  labor heuristic are imposed mechanisms; their effects cannot be advertised as
  wholly spontaneous organization.
- At fixed population size, periodic replacement of a poor incumbent is a declared
  adaptation to equalize compute. Birth endowments are logged external issuance,
  never counted as earned wealth. Multiple simultaneous novices cannot all win
  the same first auction; randomized sequential bid initialization resolves that
  competition explicitly.
- Reputation is a smoothed **group-outcome exposure proxy**, not Shapley value or
  verified individual competence. Behavioral divergence does not prove skill.
- Team decisions use a rotating representative. Persistent self-elected leadership
  is not implemented; we therefore do not claim to have demonstrated hierarchy.
- Authenticated evidence IDs can only be forwarded by an agent that observed them.
  Natural-language assertions are unverified. This constrains deception relative
  to an unconstrained conversational society and must be disclosed in results.
- Main trials are serial and bounded. LLM-trigger screening can be O(N) per step.
  Sequential auction timing is not a throughput benchmark of asynchronous MAS.
- Same budgets mean equal ceilings, not equal realized consumption. Report the
  accuracy/cost frontier and fund equal-budget controls before claiming efficiency.
- No claim about LLM emergence is supported until live-model experiments succeed
  and replicate across independent seeds and at least two backbone conditions.
