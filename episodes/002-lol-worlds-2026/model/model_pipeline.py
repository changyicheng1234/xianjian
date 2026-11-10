"""Chronological, market-free opponent-strength models for one Worlds forecast.

This is a project-local research extension. It does not modify the shared engine.
Configuration selection precedes the target calculation. Inputs are completed
series; a series is never entered again as separate map observations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize, minimize_scalar
from scipy.special import expit, logit
from scipy.sparse import coo_matrix


HERE = Path(__file__).resolve().parent
ALIASES = {
    "geng": "GEN", "gengesports": "GEN", "gen": "GEN",
    "bilibiligaming": "BLG", "bilibiligamingdreamsmart": "BLG",
    "bilibiligamingpingan": "BLG", "bilibiligamingpinganbank": "BLG", "blg": "BLG",
    "dpluskia": "DK", "damwonkia": "DK", "dk": "DK",
    "hanwhalifeesports": "HLE", "hle": "HLE",
    "invictusgaming": "IG", "shanghaiinvictusgamingmeituan": "IG", "ig": "IG",
    "topesports": "TES", "tes": "TES", "g2esports": "G2", "g2": "G2",
    "teamliquid": "TL", "teamliquidalienware": "TL", "tlaw": "TL", "tl": "TL",
    "ktrolster": "KT", "kt": "KT", "t1": "T1", "sktelecomt1": "T1",
    "karminecorp": "KC", "kc": "KC", "anyoneslegend": "AL", "al": "AL",
    "tt": "TT", "thundertalkgaming": "TT", "omg": "OMG", "ohmygod": "OMG",
    "fearx": "FOX", "bnkfearx": "FOX",
    "drx": "DRX", "kiwoomdrx": "DRX",
    "okbrion": "BRION", "oksavingsbankbrion": "BRION", "hanjinbrion": "BRION",
    "kwangdongfreecs": "DNF", "dnfreecs": "DNF", "dnsoopers": "DNF",
}
REVIEWED_SAME_DAY_PAIRS = {
    frozenset(["gol:57277", "gol:57447"]),
    frozenset(["gol:59828", "gol:60157"]),
    frozenset(["gol:65096", "gol:65359"]),
    frozenset(["gol:65108", "gol:65360"]),
}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def team_key(name, year=None, league=None):
    key = re.sub(r"[^a-z0-9]", "", str(name).lower())
    if not key:
        raise ValueError(f"Empty canonical team: {name!r}")
    if key == "madlionskoi" and year == 2024 and league in {"LEC", "Worlds", "MSI", "EWC"}:
        return "MKOI"
    if key == "movistarkoi" and year is not None and year >= 2025 and league in {"LEC", "Worlds", "MSI", "FST", "EWC"}:
        return "MKOI"
    return ALIASES.get(key, key)


def bo5_link(p):
    p = np.asarray(p)
    return p ** 3 * (10 - 15 * p + 6 * p ** 2)


def calibrate(p, slope):
    return expit(float(slope) * logit(np.clip(p, 1e-9, 1 - 1e-9)))


def scores(p, y):
    p = np.clip(np.asarray(p, dtype=float), 1e-9, 1 - 1e-9)
    y = np.asarray(y, dtype=float)
    if not len(y):
        return {"n": 0, "brier": None, "logLoss": None, "accuracy": None}
    return {"n": len(y), "brier": float(np.mean((p - y) ** 2)),
            "logLoss": float(np.mean(-y * np.log(p) - (1 - y) * np.log1p(-p))),
            "accuracy": float(np.mean(np.where(np.isclose(p, .5, rtol=0, atol=1e-12), .5, (p > .5) == y)))}


def calibration_slope(p, y):
    z = logit(np.clip(np.asarray(p), 1e-9, 1 - 1e-9))
    y = np.asarray(y)
    # A fixed, weak anchor limits extreme slopes when validation has few BO5s.
    result = minimize_scalar(lambda a: np.sum(np.logaddexp(0, a * z) - y * a * z)
                             + .5 * (a - 1) ** 2, bounds=(0, 3), method="bounded")
    if not result.success:
        raise RuntimeError("Symmetric calibration did not converge")
    return float(result.x)


def load_series(path, cutoff, out):
    raw = pd.read_csv(path, keep_default_na=False)
    required = ["series_id", "date_utc", "event", "team_a", "team_b", "wins_a", "wins_b", "bo", "source_url"]
    if any(c not in raw for c in required):
        raise ValueError("Dataset missing columns: " + str([c for c in required if c not in raw]))
    repeated = raw[raw.series_id.duplicated(keep=False)]
    for sid, group in repeated.groupby("series_id"):
        signature = group[["date_utc", "event", "team_a", "team_b", "wins_a", "wins_b", "bo"]].drop_duplicates()
        if len(signature) != 1:
            group.to_csv(out / "conflicting-original-series-id.csv", index=False)
            raise ValueError(f"Conflicting duplicate original series ID: {sid}; no row chosen by order")
    # Select by competition identity/year before inspecting any model scores.
    core = {"LCK", "LPL", "LEC", "LCS", "LTA", "LCP", "CBLOL", "Worlds", "MSI", "FST", "EWC"}
    legacy = {"PCS", "VCS", "LJL", "LLA"}
    excluded_domain = []
    def primary_domain(row):
        league, event, year = str(row.get("league", "")), str(row["event"]), str(row["date_utc"])[:4]
        reason = ""
        if league == "EWC" and "qualifier" in event.lower():
            reason = "EWC regional online qualifier, outside primary top-tier event domain"
        elif league not in core and not (year == "2024" and league in legacy):
            reason = "Lower-tier or out-of-scope competition/year"
        elif year == "2024" and league in {"LJL", "LLA"} and str(row.get("event_contains_tied_results", "")).lower() == "true":
            reason = "Historical regional event with unresolved BO2/draw format; exclude whole event"
        if reason:
            excluded_domain.append({**row, "domain_exclusion_reason": reason})
        return not reason
    raw = raw.loc[raw.apply(primary_domain, axis=1)].copy()
    pd.DataFrame(excluded_domain).to_csv(out / "excluded-event-domain.csv", index=False)
    write_json(out / "domain-selection.json", {"originalRows": len(raw) + len(excluded_domain), "primaryRowsBeforeValidation": len(raw),
               "excludedRows": len(excluded_domain), "excludedEvents": sorted({r["event"] for r in excluded_domain}),
               "rule": "Protocol clarification 04; event/year domain fixed before model scores. Legitimate invited teams in top-tier events remain included."})
    good, rejected, seen = [], [], set()
    for row in raw.to_dict("records"):
        try:
            date = pd.Timestamp(str(row["date_utc"])[:10])
            if not pd.Timestamp("2024-01-01") <= date < pd.Timestamp(cutoff[:10]):
                raise ValueError("outside training window or not safely before cutoff date")
            a, b = [team_key(row[c], date.year, str(row.get("league", ""))) for c in ["team_a", "team_b"]]
            values = [float(row[c]) for c in ["wins_a", "wins_b", "bo"]]
            if not all(math.isfinite(v) and v.is_integer() for v in values):
                raise ValueError("Scores and planned/inferred format must be finite integers")
            wa, wb, bo = map(int, values)
            if a == b or bo not in [1, 3, 5] or min(wa, wb) < 0 or max(wa, wb) != bo // 2 + 1 or wa == wb:
                raise ValueError("unknown/nonstandard/incomplete series format or score")
            if not str(row["series_id"]).strip() or not str(row["source_url"]).startswith("https://"):
                raise ValueError("missing original series ID or public source URL")
            if str(row["series_id"]) in seen:
                raise ValueError("duplicate original series ID")
            seen.add(str(row["series_id"]))
            if a > b:
                a, b, wa, wb = b, a, wb, wa
            good.append({**row, "date": date, "team_a": a, "team_b": b,
                         "wins_a": wa, "wins_b": wb, "bo": bo, "maps": wa + wb,
                         "y": int(wa > wb), "year": date.year,
                         "international": str(row.get("league", "")) in {"Worlds", "MSI", "FST", "EWC"}})
        except (ValueError, TypeError) as exc:
            rejected.append({**row, "reason": str(exc)})
    data = pd.DataFrame(good).sort_values(["date", "series_id"]).reset_index(drop=True)
    if not len(data) or set(data["year"]) != {2024, 2025, 2026}:
        raise ValueError("The registered chronological design requires usable 2024, 2025 and 2026 data")
    reviewed = []
    for key, group in data.groupby(["date", "team_a", "team_b"]):
        if len(group) <= 1:
            continue
        if frozenset(group.series_id) not in REVIEWED_SAME_DAY_PAIRS or not any("TIEBREAKER" in str(s).upper() for s in group.stage):
            group.to_csv(out / "same-day-pair-conflicts.csv", index=False)
            raise ValueError("Multiple series for the same teams/day require source review before fitting")
        reviewed.append({"date": str(key[0]), "teams": list(key[1:]), "seriesIds": list(group.series_id), "reason": "Independently checked ordinary match and separate tiebreaker; both retained, day-batched prediction."})
    write_json(out / "reviewed-same-day-series.json", reviewed)
    data.to_csv(out / "model-input-series.csv", index=False)
    write_json(out / "quarantined-input-rows.json", rejected)
    audit = {"sourceFile": str(path.resolve()), "sourceSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
             "acceptedSeries": len(data), "quarantinedRows": len(rejected), "dateMin": str(data.date.min()), "dateMax": str(data.date.max()),
             "dateBoundary": "Source dates; source timezone may be unspecified. All same-day forecasts precede all that day's updates. Entire cutoff date excluded.",
             "byYear": {str(k): int(v) for k, v in data.groupby("year").size().items()},
             "bo5ByYear": {str(k): int(v) for k, v in data[data.bo == 5].groupby("year").size().items()},
             "eventCounts": {str(k): int(v) for k, v in data.groupby("event").size().items()}, "aliases": ALIASES,
             "noTargetResult": bool(not ((data.team_a == "BLG") & (data.team_b == "GEN") & (data.date >= pd.Timestamp("2026-11-01"))).any())}
    write_json(out / "dataset-audit.json", audit)
    if not audit["noTargetResult"]:
        raise ValueError("Potential target-final result in training data; explicit review required")
    return data


def elo_replay(data, k, half_life):
    ratings, last, preds = {}, {}, {}
    for day, group in data.groupby("date", sort=True):
        teams = set(group.team_a) | set(group.team_b)
        for team in teams:
            old = ratings.get(team, 1500.)
            if half_life is not None and team in last:
                old = 1500 + (old - 1500) * 2 ** (-(day - last[team]).days / half_life)
            ratings[team], last[team] = old, day
        changes = defaultdict(float)
        for row in group.itertuples():
            p = float(expit((ratings[row.team_a] - ratings[row.team_b]) * math.log(10) / 400))
            preds[row.Index] = float(bo5_link(p))
            delta = k * (row.wins_a - row.maps * p) / math.sqrt(row.bo)
            changes[row.team_a] += delta
            changes[row.team_b] -= delta
        for team, delta in changes.items():
            ratings[team] += delta
    return np.array([preds[i] for i in range(len(data))]), ratings, last


def elo_target(ratings, last, cutoff, half_life):
    day = pd.Timestamp(cutoff[:10])
    def strength(team):
        r = ratings.get(team, 1500.)
        return 1500 + (r - 1500) * 2 ** (-(day - last[team]).days / half_life) if half_life is not None and team in last else r
    a, b = strength("BLG"), strength("GEN")
    return {"rawBO5": float(bo5_link(expit((a - b) * math.log(10) / 400))), "BLGrating": a, "GENrating": b}


def bt_fit(train, cutoff, half_life, ridge):
    teams = sorted(set(train.team_a) | set(train.team_b))
    lookup = {team: i for i, team in enumerate(teams)}
    n = len(train)
    rr = np.repeat(np.arange(n), 2)
    cc = np.array([[lookup[a], lookup[b]] for a, b in zip(train.team_a, train.team_b)]).ravel()
    xx = np.tile([1., -1.], n)
    x = coo_matrix((xx, (rr, cc)), shape=(n, len(teams))).tocsr()
    reference = pd.Timestamp(cutoff)
    if reference.tzinfo is not None:
        reference = reference.tz_convert("UTC").tz_localize(None)
    age = (reference - train.date).dt.total_seconds().to_numpy() / 86400
    weights = train.maps.to_numpy() * 2 ** (-age / half_life)
    y = train.wins_a.to_numpy() / train.maps.to_numpy()
    def objective(theta):
        z = x @ theta
        value = np.sum(weights * (np.logaddexp(0, z) - y * z)) + .5 * ridge * np.dot(theta, theta)
        grad = x.T @ (weights * (expit(z) - y)) + ridge * theta
        return value, np.asarray(grad)
    fit = minimize(objective, np.zeros(len(teams)), method="L-BFGS-B", jac=True,
                   options={"maxiter": 500, "ftol": 1e-10, "gtol": 1e-7})
    if not fit.success:
        raise RuntimeError(f"BT optimization failed: {fit.message}")
    return dict(zip(teams, map(float, fit.x))), {"nSeries": n, "nTeams": len(teams), "success": bool(fit.success), "iterations": int(fit.nit), "objective": float(fit.fun)}


def bt_predict(strength, a, b):
    return float(bo5_link(expit(strength.get(a, 0.) - strength.get(b, 0.))))


def bt_replay(data, half_life, ridge):
    pred = np.full(len(data), np.nan)
    logs = []
    dates = sorted(data.loc[(data.year >= 2025) & (data.bo == 5), "date"].unique())
    for day in dates:
        cutoff = pd.Timestamp(day)
        test = data[(data.date == cutoff) & (data.bo == 5)]
        train = data[data.date < cutoff]
        if train.empty:
            raise ValueError("Empty historical training window")
        strength, info = bt_fit(train, cutoff, half_life, ridge)
        for row in test.itertuples():
            pred[row.Index] = bt_predict(strength, row.team_a, row.team_b)
        logs.append({"forecastSourceDate": str(cutoff.date()), "trainingMaxDate": str(train.date.max()), "strictlyEarlier": bool(train.date.max() < cutoff), **info})
    return pred, logs


def metric_report(data, pred):
    report = {}
    for label, mask in [("allBO5", data.bo == 5), ("internationalBO5", (data.bo == 5) & data.international)]:
        indices = np.flatnonzero(mask.to_numpy())
        report[label] = scores(pred[indices], data.y.to_numpy()[indices])
    return report


def block_bootstrap(data, p, draws=2000):
    y = data.y.to_numpy()
    q = np.clip(p, 1e-9, 1 - 1e-9)
    losses = pd.DataFrame({"brier": (q - y) ** 2, "logLoss": -y * np.log(q) - (1 - y) * np.log1p(-q),
                           "block": data.event.astype(str).to_numpy()})
    blocks = [g[["brier", "logLoss"]].to_numpy() for _, g in losses.groupby("block")]
    rng = np.random.default_rng(20261109)
    values = np.empty((draws, 2))
    for j in range(draws):
        sample = np.concatenate([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))])
        values[j] = sample.mean(axis=0)
    return {"unit": "whole competition event", "nBlocks": len(blocks), "draws": draws,
            "warning": "Descriptive block-bootstrap metric intervals; tournaments and teams can remain dependent. These are not target-probability confidence intervals.",
            "brierPercentile95": list(map(float, np.quantile(values[:, 0], [.025, .975]))),
            "logLossPercentile95": list(map(float, np.quantile(values[:, 1], [.025, .975])))}


def reliability(data, p):
    # Symmetrize team orientation, so alphabetic names cannot define the bins.
    p = np.r_[p, 1 - p]
    y = np.r_[data.y.to_numpy(), 1 - data.y.to_numpy()]
    bins = []
    for lo, hi in zip(np.arange(0, 1, .1), np.arange(.1, 1.01, .1)):
        mask = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        n = int(mask.sum())
        bins.append({"lower": float(lo), "upper": float(hi), "orientedRows": n,
                     "meanPredicted": float(p[mask].mean()) if n else None,
                     "observedFraction": float(y[mask].mean()) if n else None,
                     "warning": "Two complementary rows per original series; not independent observations."})
    return bins


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cutoff", required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    out = args.out
    write_json(out / "run-start.json", {"startedAtUtc": stamp(), "argv": vars(args) | {"dataset": str(args.dataset), "out": str(out)},
                                     "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "marketInputs": False})
    data = load_series(args.dataset, args.cutoff, out)
    tune = (data.year == 2025) & (data.bo == 5)
    test = (data.year == 2026) & (data.bo == 5)
    if tune.sum() < 30 or test.sum() < 30:
        raise ValueError("Insufficient BO5 validation/holdout samples for the registered design")
    all_preds, candidates, fitted, replay_logs = {}, [], {}, {}
    for k, half in product([16, 32, 64], [90, 180, 365, None]):
        name = f"elo-k{k}-h{half}"
        pred, ratings, last = elo_replay(data, k, half)
        all_preds[name] = pred
        fitted[name] = (ratings, last)
        candidates.append({"name": name, "family": "elo", "k": k, "halfLife": half, "raw2025": scores(pred[tune], data.y[tune])})
        print(f"[INFO] {stamp()} validation replay complete: {name}", flush=True)
    for half, ridge in product([90, 180, 365], [1, 4, 16]):
        name = f"bt-h{half}-r{ridge}"
        pred, logs = bt_replay(data, half, ridge)
        all_preds[name], replay_logs[name] = pred, logs
        candidates.append({"name": name, "family": "bt", "halfLife": half, "ridge": ridge, "raw2025": scores(pred[tune], data.y[tune])})
        print(f"[INFO] {stamp()} daily replay complete: {name}", flush=True)
    chosen = {}
    for family in ["elo", "bt"]:
        best = min([c for c in candidates if c["family"] == family], key=lambda c: (c["raw2025"]["logLoss"], c["name"]))
        slope = calibration_slope(all_preds[best["name"]][tune], data.y[tune])
        chosen[family] = {**best, "calibrationSlope": slope, "blendWeight": .5}
    selection = {"lockedAtUtc": stamp(), "selectionUsed": "Raw chronological 2025 BO5 log loss only",
                 "calibrationUsed": "Selected model's 2025 out-of-time BO5 predictions; .5*(slope-1)^2 fixed regularization, slope in [0,3], no intercept",
                 "calibrationTrainingIsNotValidation": True, "holdoutUsedForSelection": False,
                 "targetProbabilityExaminedBeforeSelection": False, "chosen": chosen, "candidates": candidates}
    write_json(out / "model-selection.json", selection)
    write_json(out / "daily-fit-audit.json", replay_logs)
    columns = ["series_id", "date_utc", "event", "team_a", "team_b", "wins_a", "wins_b", "bo", "y", "international", "source_url"]
    rows = data.loc[tune | test, columns].copy()
    for name, pred in all_preds.items():
        rows[name] = pred[tune | test]
    rows.to_csv(out / "all-candidate-out-of-time-predictions.csv", index=False)
    holdout = data.loc[test].reset_index(drop=True)
    pcal, metrics = {}, {}
    for family, config in chosen.items():
        raw = all_preds[config["name"]][test]
        pcal[family] = calibrate(raw, config["calibrationSlope"])
        metrics[family + "Raw"] = metric_report(holdout, raw)
        metrics[family + "Calibrated"] = metric_report(holdout, pcal[family])
    blend = .5 * (pcal["elo"] + pcal["bt"])
    metrics["primaryEqualBlend"] = metric_report(holdout, blend)
    metrics["coinFlip"] = metric_report(holdout, np.full(len(holdout), .5))
    metrics["blockBootstrapPrimary"] = block_bootstrap(holdout, blend)
    metrics["warning"] = "Sequential 2026 holdout with frozen selection/calibration; one data provider, incomplete coverage, roster/meta drift and remaining event dependence limit generalization."
    write_json(out / "holdout-metrics.json", metrics)
    write_json(out / "holdout-calibration-bins.json", reliability(holdout, blend))
    holdout["p_elo"], holdout["p_bt"], holdout["p_primary"] = pcal["elo"], pcal["bt"], blend
    holdout[columns + ["p_elo", "p_bt", "p_primary"]].to_csv(out / "holdout-predictions.csv", index=False)
    # Only now, after selection has been persisted, compute this final's result.
    components = {}
    ec, bc = chosen["elo"], chosen["bt"]
    r, last = fitted[ec["name"]]
    components["elo"] = elo_target(r, last, args.cutoff, ec["halfLife"])
    components["elo"]["calibratedBLG"] = float(calibrate(components["elo"]["rawBO5"], ec["calibrationSlope"]))
    strength, fit_info = bt_fit(data, pd.Timestamp(args.cutoff[:10]), bc["halfLife"], bc["ridge"])
    raw = bt_predict(strength, "BLG", "GEN")
    components["bt"] = {"rawBO5": raw, "calibratedBLG": float(calibrate(raw, bc["calibrationSlope"])),
                        "BLGstrength": strength.get("BLG", 0.), "GENstrength": strength.get("GEN", 0.), "fit": fit_info}
    month_start = pd.Timestamp(args.cutoff[:10]).to_period("M").start_time
    older = data[data.date < month_start]
    month_strength, _ = bt_fit(older, month_start, bc["halfLife"], bc["ridge"])
    stale_bt = float(calibrate(bt_predict(month_strength, "BLG", "GEN"), bc["calibrationSlope"]))
    probability = .5 * (components["elo"]["calibratedBLG"] + components["bt"]["calibratedBLG"])
    result = {"computedAtUtc": stamp(), "informationCutoffUtc": args.cutoff, "isFrozen": False,
              "BLG": probability, "GenG": 1 - probability, "components": components,
              "samePolicyStartOfMonthBT": stale_bt,
              "samePolicyBlend": .5 * (components["elo"]["calibratedBLG"] + stale_bt),
              "selectionSha256": hashlib.sha256((out / "model-selection.json").read_bytes()).hexdigest(),
              "interpretation": "A reproducible model estimate, not a guaranteed result or calibrated target confidence interval. Final review of dataset coverage, aliases and methodology remains required.",
              "rosterPatchDraftAdjustment": 0,
              "selectionAndCalibrationMarketInput": False}
    write_json(out / "target-calculation.json", result)
    write_json(out / "selected-strengths.json", {"bt": strength, "elo": r, "eloLastObservedDate": {k: str(v) for k, v in last.items()}})
    write_json(out / "run-complete.json", {"completedAtUtc": stamp(), "outputDirectory": str(out.resolve()), "probabilityComputedButNotFrozen": True})
    print(json.dumps({"output": str(out.resolve()), "target": result, "holdout": metrics["primaryEqualBlend"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
