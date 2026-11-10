# 第002期：2026全球总决赛AI预测

**Gen.G66.5%，BLG33.5%。** 以指定BO5正常完成并产生唯一官方冠军为条件，取消、未决或无冠军不自动算任何一方输。

[中文报告](report.zh.md) · [PDF](report.zh.pdf) · [冻结JSON](frozen-probabilities.json) · [来源清单](sources.csv) · [下载](https://github.com/changyicheng1234/ai-prediction-evidence/releases/tag/episode-002-20261110-v3) · [English](README.en.md)

比赛数据截止：北京时间2026年11月9日21:00:34，最后纳入日期11月8日。官方复核截止：11月10日14:04:34。本地冻结：11月10日14:09:44。市场快照：11月10日14:11:55，买卖中间价GEN62.5%/BLG37.5%。**GitHub实际公开时间以Release published_at为准。**

主要依据为对手调整后的赛果及GEN稳定性。最强反证包括BLG淘汰DK/T1、国际上限和官方实力榜几乎持平。两个模型共享数据，不能当独立证据。

完整原生审核仍为insufficient_evidence。规则细则、健康、资料时点与本场校准仍有限制，整体诊断提示可能偏自信。239场BO5的Brier0.2223低于五五开0.2500，是历史回放而非前瞻战绩，不保证本场命中。

## 核查与复算

reviews/为审阅与诊断，market/为冻结后的市场对照和结算差异，version-history.json保留早期版本，public-export.json记录净化副本与原件哈希。

快速核查只需Python标准库：

```bash
python verify_results.py
```

完整重跑用Python3.11，在本期目录执行：

```bash
python -m pip install -r requirements.txt
python model/model_pipeline.py --dataset data/series-source-snapshot.csv --out replay-output-new --cutoff 2026-11-09T13:00:34Z
```

重跑会重新拟合候选，可能需数分钟。比较数值、配置和指标；时间戳/路径会变化，输出SHA不要求完全相同。model/target-calculation.json是冻结前中间计算，isFrozen=false；本期冻结状态以frozen-probabilities.json为准。重跑不自动替换原预测。
