# Episode002: Worlds2026 AI forecast

**GEN66.5%, BLG33.5%.** Conditional on normal completion with one official champion. Cancellation/unresolved/no champion is not automatically either team's defeat.

[Report](report.en.md) · [PDF](report.en.pdf) · [Frozen JSON](frozen-probabilities.json) · [Sources](sources.csv) · [Download](https://github.com/changyicheng1234/ai-prediction-evidence/releases/tag/episode-002-20261110-v3) · [中文](README.md)

Match-data cutoff2026-11-09T13:00:34Z; latest included source date November8. Official review cutoff2026-11-10T06:04:34Z. Local freeze06:09:44Z; market snapshot06:11:55Z, midpoints GEN62.5/BLG37.5. Actual publication must be checked against GitHub release published_at.

Opponent-adjusted results and GEN consistency support the estimate. BLG's DK/T1 path, international ceiling and near-level official GPR are counterevidence. Components share data and are not independent evidence.

Native full review remains insufficient_evidence. Rules, health, historical availability and target calibration remain limited; diagnostics suggest possible global overconfidence. Brier0.2223 versus0.2500 in239 historical BO5s is retrospective, not a prospectively published record or guarantee.

See reviews/, market/, version-history.json and public-export.json. Quick standard-library verification:

```bash
python verify_results.py
```

Full replay with Python3.11, from this episode directory:

```bash
python -m pip install -r requirements.txt
python model/model_pipeline.py --dataset data/series-source-snapshot.csv --out replay-output-new --cutoff 2026-11-09T13:00:34Z
```

The full replay can take several minutes. Compare numbers/configurations/metrics, not whole output hashes because paths/timestamps change. target-calculation.json is a pre-freeze intermediate; frozen-probabilities.json is authoritative. A rerun never automatically replaces the archive.
