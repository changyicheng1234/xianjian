"""Verify published probabilities and retrospective metrics without network access."""
from pathlib import Path
import csv
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parent


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8-sig"))


def rows(name):
    with (ROOT / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def close(a, b):
    assert abs(float(a) - float(b)) < 1e-11, (a, b)


def loss(data, column):
    return sum(-float(r["y"]) * math.log(float(r[column])) - (1 - float(r["y"])) * math.log1p(-float(r[column])) for r in data) / len(data)


def metrics(data):
    return {"n": len(data), "brier": sum((float(r["p_primary"]) - float(r["y"])) ** 2 for r in data) / len(data), "logLoss": loss(data, "p_primary")}


def main():
    f = read("frozen-probabilities.json")
    freeze_sha = hashlib.sha256((ROOT / "frozen-probabilities.json").read_bytes()).hexdigest()
    assert freeze_sha == "006e9ed53f80dedc9db28e8e889701db1a66ca5d30e842a06b843991e233d404"
    assert f["frozen"] and f["episodeProbabilityFinalized"] and not f["fullResearchChecksPassed"]
    close(sum(f["probabilities"].values()), 1)
    selection = read("model/model-selection.json")
    target = read("model/target-calculation.json")
    probabilities = []
    for family in ["elo", "bt"]:
        component = target["components"][family]
        raw = component["rawBO5"]
        slope = selection["chosen"][family]["calibrationSlope"]
        calibrated = 1 / (1 + math.exp(-slope * math.log(raw / (1 - raw))))
        close(calibrated, component["calibratedBLG"])
        probabilities.append(calibrated)
    close(sum(probabilities) / 2, f["probabilities"]["BLG"])
    close(1 - sum(probabilities) / 2, f["probabilities"]["GEN"])
    holdout = rows("model/holdout-predictions.csv")
    assert len(holdout) == 239
    for row in holdout:
        close(float(row["p_primary"]), (float(row["p_elo"]) + float(row["p_bt"])) / 2)
    international = [r for r in holdout if r["international"].lower() == "true"]
    assert len(international) == 46
    expected = read("model/holdout-metrics.json")["primaryEqualBlend"]
    for name, data in [("allBO5", holdout), ("internationalBO5", international)]:
        actual = metrics(data)
        for key in actual:
            close(actual[key], expected[name][key])
    candidates = rows("model/all-candidate-out-of-time-predictions.csv")
    tune = [r for r in candidates if r["date_utc"].startswith("2025")]
    assert len(tune) == 211
    for family in ["elo", "bt"]:
        columns = [c for c in tune[0] if c.startswith(family + "-")]
        selected = min(columns, key=lambda c: (loss(tune, c), c))
        assert selected == selection["chosen"][family]["name"]
        close(loss(tune, selected), selection["chosen"][family]["raw2025"]["logLoss"])
    raw = ROOT / "data/series-source-snapshot.csv"
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == "23f706bb7cf488371fa9adb682386ecd8d816e4490c2c20037fc97183850b9cd"
    assert len(rows("data/series-source-snapshot.csv")) == 4007
    assert len(rows("data/model-input-series.csv")) == 3432
    market = read("market/market-comparison.json")
    assert market["predictionFreezeSha256"] == freeze_sha
    assert market["observedAtUtc"] > f["frozenAtUtc"] and not market["sameOutcomeCondition"]
    print(json.dumps({"status": "pass", "checks": "Frozen bytes, calibration, equal blend, 2025 selection, 239/46 metrics, input counts and post-freeze comparison", "probabilities": f["probabilities"], "retrospective": True, "fullResearchChecksPassed": False}, indent=2))


if __name__ == "__main__":
    main()
