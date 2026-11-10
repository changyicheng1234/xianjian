# V3 independent method challenge: retain the point estimate, qualify its precision

Review the [machine decision](method-review.json), [precomputation plan](diagnostic-plan.json), and [new diagnostics](calibration-diagnostics.json). This is a targeted independent review, not another native full-review run. No markets, odds, or other forecasters' probabilities were read; frozen artifacts and weights were not changed.

**Decision: no confirmed data/implementation error currently requires a different number. Retain Gen.G 66.5024%, BLG 33.4976%, displayed as 66.5/33.5 or approximately 67/33 in narration.** This remains the previous-cutoff conditional model estimate, not a probability proved accurate by these diagnostics. A new verified factual error requires separate treatment; this review does not replace the factual refresh.

Fixed forecasts on 239 BO5s and 46 international main-event BO5s were examined under the recorded plan, using 2000 whole-event bootstrap draws. No diagnostic slope is applied to the target.

| Diagnostic | All 239, 25 blocks | International 46, only 5 blocks |
| --- | ---: | ---: |
| Blend's diagnostic 2026 slope | 0.769 | 1.189 |
| Descriptive block 95% percentiles | 0.537–1.163 | 0.752–1.919 |
| Family error correlation | 0.982 | 0.969 |
| Mean blend-minus-BT log loss | +0.00232 | −0.01124 |
| Descriptive paired block range | −0.00892–+0.01479 | −0.02893–+0.00851 |

A slope below one signals possible overconfidence in this diagnostic. The full sample shows it, particularly Elo: slope 0.648, descriptive range 0.452–0.973. This must be disclosed. International results do not show the same direction, with only five blocks. The evidence does not identify a defensible uniform target shrinkage. Bootstrap percentiles/fractions are descriptive, not target confidence intervals or posterior probabilities.

Within the prespecified 0.6–0.7 favorite bin, all 69 forecasts average 64.6% versus 62.3% favorite wins. Internationally, only 13 forecasts average 65.6%, with 7/13 favorite wins. This is thin local calibration evidence, not a replacement probability for this match. Paired blend-versus-BT ranges cross zero; neither switching to BT nor claiming stable blending gains is supported. Shared data produce highly correlated errors. Fixed losses beat 50/50 in this retrospective sample without proving single-match accuracy.

Removing 2024 changes BLG from 33.50% to 34.48%; 2026-only history gives 37.93%. The latter simultaneously changes Elo initialization, opponent histories, and regional anchors while retaining old calibration slopes. It is a stress scenario, not an equivalently selected/calibrated/validated replacement. No inactivity decay is also not equal weighting of every old Elo game. BT already discounts history over 90 days. Roster drift remains real without a validated arbitrary player adjustment.

Only eight 2026 LCK–LPL BO5s exist, with BLG appearing six times and GEN twice. They are not independent target-match calibration trials; 3432 training series are not 3432 comparable finals. The raw BO5 link is a working constant-map-strength assumption; historical symmetric calibration does not prove independent maps or correct adaptation/Fearless modeling.

The missing-record portion of the native calibration/blending diagnostics question now has paired losses, correlation, slopes, and one-row-per-series reliability tables. Stable benefit and target calibration remain unproved; no native gap status is altered. Daily BT and target policies align, with month-start values representing stale-information sensitivity. Existing direct-file selection/calibration checks remain valid without establishing historical as-available data versions or season-start preregistration.

Complete current Fearless applicability, comprehensive notice coverage, exact UTC chronology, registration/health, and some entity continuity remain bounded uncertainties. This review obtains no new rule text and does not remove native `insufficient_evidence`. Other V3 factual work may update particular claims from new original evidence.

Suggested video framing: a new targeted review retains approximately Gen.G 67%, BLG 33%, based on opponent-adjusted historical results, with shared-data models and unresolved applicability/availability limits. Keep the original match-data cutoff, 2026-11-09T13:00:34Z, distinct from today's review date. Do not claim precise true probability, guaranteed success, two independent AIs, stable blending gains, season-long prospective performance, pristine blindness, or a calibrated target confidence interval. The improvement is a stronger diagnostic record and more accurate interpretation, not an arbitrary number change.
