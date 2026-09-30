# Data

`hiddenbench.json` was downloaded from the authors' public
[HiddenBench dataset](https://huggingface.co/datasets/YuxuanLi1225/HiddenBench).
The dataset card declares an MIT license. `hiddenbench.provenance.json` records
the source, retrieval time, SHA-256 and record count (65).

The local loader groups identical descriptions/options (or explicit `group_id`s)
before partitioning. Private-fact variants of the same public scenario do not
cross the boundary. With the downloaded version, there are 39 train, 12 validation
and 14 test items. Grouping is a minimum contamination precaution, not a claim
that all semantically similar scenarios have been discovered or that model
pretraining contamination is excluded.

These splits and the sequential auction protocol are **custom experimental
adaptations**. Do not compare their scores directly with an official leaderboard.
The scripted backend always selects the first textual answer option when it
submits on this dataset. It is a plumbing check, not a natural-language solver.

Generated `sum`, `max` and `path` tasks are recreated from deterministic seed,
split and episode identifiers. They are original diagnostic tasks. No Silo-Bench,
Social Gym, MATH, CloudCast or ProgramBench dataset is included here.
