"""Generate portable tables and scientific figures from the verified local runs."""

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research" / "verified-results"
OUT.mkdir(exist_ok=True)
engine_hash = hashlib.sha256((ROOT / "test.py").read_bytes()).hexdigest()
names = ["phase-study", "project-study", "institution-study", "capital-ablation"]
summary = {}
for name in names:
    folder = ROOT / "runs" / ("verified-" + name)
    summary[name] = json.loads((folder / "sweep_summary.json").read_text())
    assert summary[name]["status"] == "complete"
    for manifest in folder.glob("cell-*/manifest.json"):
        assert json.loads(manifest.read_text())["code_sha256"] == engine_hash, manifest
(OUT / "summary.json").write_text(json.dumps({"code_sha256": engine_hash, "studies": summary}, indent=2) + "\n")

cells = summary["project-study"]["cells"]
fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
projects = ["capital", "teams", "institutions"]
for b, baseline in enumerate(["market", "round_robin", "single"]):
    selected = [next(c for c in cells if c["parameters"] == {"project": p, "baseline": baseline}) for p in projects]
    means = np.array([c["test_accuracy_mean"] for c in selected])
    low = np.array([c["seed_bootstrap_95_ci"][0] for c in selected])
    high = np.array([c["seed_bootstrap_95_ci"][1] for c in selected])
    ax.bar(
        np.arange(3) + (b - 1) * 0.24,
        means,
        width=0.24,
        label=baseline,
        yerr=np.maximum(0, np.array([means - low, high - means])),
        capsize=3,
    )
ax.set_xticks(range(3), projects)
ax.set_ylim(0, 1.15)
ax.set_ylabel("Held-out procedural accuracy")
ax.set_title(
    "Scripted agents: routing dominates these small tasks\n3 population seeds; seed-bootstrap intervals are exploratory"
)
ax.legend(ncols=3, loc="upper center")
ax.spines[["top", "right"]].set_visible(False)
fig.savefig(OUT / "project-comparison.png", dpi=170)
plt.close(fig)

cells = summary["phase-study"]["cells"]
fig, axes = plt.subplots(1, 2, figsize=(10, 5), layout="constrained")
comm = [0.03, 0.18, 0.9]
coord = [0, 0.025, 0.15]
for ax, key, title in zip(
    axes, ["test_accuracy_mean", "tail_team_share_mean"], ["Held-out accuracy", "Largest-team fraction (late training)"]
):
    values = np.array(
        [
            [next(c[key] for c in cells if c["parameters"] == {"comm_out": r, "coordination_cost": q}) for q in coord]
            for r in comm
        ]
    )
    plot = ax.imshow(values, vmin=0, vmax=1, cmap="viridis")
    for i in range(3):
        for j in range(3):
            ax.text(
                j, i, f"{values[i, j]:.2f}", ha="center", va="center", color="white" if values[i, j] < 0.5 else "black"
            )
    ax.set_xticks(range(3), coord)
    ax.set_yticks(range(3), [1, 6, 30])
    ax.set_xlabel("Coordination cost per pair")
    ax.set_ylabel("Outside / inside communication price")
    ax.set_title(title)
fig.colorbar(plot, ax=axes, shrink=0.65)
fig.suptitle("Conditional simulator screening — not an established phase diagram")
fig.savefig(OUT / "mechanism-screen.png", dpi=170)
plt.close(fig)
print(
    json.dumps(
        {
            "output": str(OUT),
            "code_sha256": engine_hash,
            "runs": sum(v["replicates_completed"] for v in summary.values()),
        },
        indent=2,
    )
)
