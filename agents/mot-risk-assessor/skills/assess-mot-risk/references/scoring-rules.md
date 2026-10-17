# Evidence-based MOT condition scoring

Use these **specific deductions as the default, cross-vehicle-comparable method**. This is the owner's judgement-based screening heuristic, **not** a DVSA or calibrated failure-probability score. Keep the optional 100-point category rubric independent: do not add its category deductions to this method. Default to conservative explicit evidence and avoid double counting.

## A. Latest *unresolved* MOT defects

The “latest” is the most recent test evidence **after accounting for any subsequent pass/retest**. Never penalise a historical failed item as currently unresolved if a later pass superseded that fail, absent new evidence of persistence.

| Latest unresolved evidence | Deduction | Safety cap |
| --- | ---: | ---: |
| Dangerous defect affecting structure, brakes or steering | −4.0 | Score at most **2.0** |
| Other dangerous defect | −2.0 | Score at most **5.0** |
| Major defect affecting structure, brakes or steering | −2.0 | Score at most **5.0** |
| Isolated inexpensive major issue, e.g. defective bulb | −0.75 | None |
| Other major defect | −1.0 to −2.0, based on safety/repair complexity | None |
| Minor defects | −0.25 each | Combined with advisories below |
| Advisories | −0.15 each | Combined with minors: max **1.5** |

If one issue is described redundantly in the same test, penalise it once at the most serious applicable severity, not simultaneously as a dangerous and major issue. Multiple truly separate issues within a category can each count. Apply safety caps to the final result, not just their own subtotal. A pass may still carry minor defects or advisories; they are not failed legal requirements. A latest failed MOT with no recorded later pass can be described as **unresolved in the available evidence**, not proof that repairs never happened after the test. The same rule applies to latest passed evidence that visibly contains a structural corrosion advisory: use the special historical corrosion rule below as appropriate.

## B. Historical patterns (previous three distinct annual MOT testing cycles)

| Evidence | Deduction / cap |
| --- | --- |
| Same system appears across at least two distinct annual cycles | −0.6 **per system**, maximum **−1.8** across systems |
| An advisory/minor issue progresses into a major/dangerous failure | −0.75 **per system**, maximum **−1.5** |
| Structural corrosion in recent history without verified repairs | −0.75 |
| **Structural corrosion still on latest passed MOT** | **−1.25 instead of −0.75**; cap score **6.0** if across multiple annual cycles |
| Repeated emissions-related failure cycles | −0.75 |
| Three or more different **costly systems** developing defects within two annual cycles | −0.6 |
| Multiple **separate annual** failure cycles over last three years | −0.5 |

Interpret “previous three annual cycles” as the latest three **annual test periods including their grouped passes/retests**, with enough previous cycles for a recurrence judgment. A fail and its pass in one cycle is one failure cycle. A system recurring within only one test/retest cycle is **not** two annual cycles. An advisory progressing to failure **within the same cycle** isn't automatic longitudinal deterioration; prefer progression between distinct cycles. Count multiple cycles of emissions failures for the emissions penalty, but a single failed test + successful retest isn't repeated annual failure.

Structural corrosion −0.75 and −1.25 are **alternatives**, never cumulative. A persistent corrosion system can also qualify for a *distinct system-recurrence penalty*, but do not subtract multiple historical rows for duplicate wording that evidences only the same one-off defect. Use all independently evidenced pattern penalties while describing any overlap. Repairs supported by dated, specific invoices may reduce pattern concerns; do not automatically infer repairs from a pass. Three successive annual cycles repeating an advisory, dangerous tyre failures and multiple unrelated safety problems should inform the qualitative maintenance/neglect assessment even where no extra fixed numeric penalty is defined. No arbitrary extra deductions.

## C. Arithmetic and bands

1. Start **10.0**.
2. Sum legitimate A deductions, with the aggregate minor+advisory deduction capped at 1.5.
3. Sum independent B deductions with their category maximums.
4. Calculate `raw = 10 − latest − historical` and clamp to `[0,10]`.
5. Apply **all** safety caps: minimum of the raw score and applicable cap values.
6. Round to nearest 0.5 (exact midpoints round upward).

| Final score | Band |
| --- | --- |
| 9.0–10.0 | Excellent |
| 7.5–8.5 | Good |
| 5.5–7.0 | Moderate |
| 3.0–5.0 | High risk |
| 0.0–2.5 | Very high risk |

These **labels are descriptive only**; never mistake for accident risk, residual life, or repair probability. Because scores are rounded in half-point increments, these ranges cover every possible output. A strong-looking score does not cancel an inspection warning about a separately identified serious risk.

## D. Confidence

- **High**: Clear source, latest reasonably recent, multiple annual cycles (preferably 5 years), readable classifications and mileages, no major gaps or contradictions. Not a physical inspection.
- **Medium**: Two or more cycles but meaningful gaps, old data, unclear repairs or moderate source limitations.
- **Low**: Fewer than two annual cycles (**mandatory**); no recent test, substantial missing/contradictory records, unreliable transcription, unknown outcome of safety-critical repairs. Use judgment if a single limitation is less important, but never call sparse evidence High.

When no actual tests exist, do not issue a numerical rating; explain what records are needed. Mileage reductions and missing service records are **verification/confidence issues**, not extra fixed-score deductions, since the user has not provided a fixed mileage or service-history penalty. Note these prominently when relevant; do not dilute critical safety concerns merely because the arithmetic is high.

## E. Sanity checks (hypothetical, not vehicle data)

- Latest *unresolved* dangerous steering defect: 10−4=6, then safety cap **2.0**; any other supported penalty cannot increase it. No recommendation that it is safe to drive.
- Latest passed MOT with two advisories, and one system also recorded in a distinct recent annual cycle: 10−0.30−0.60=**9.0** after half-point rounding, absent other concerns.
- Latest passed MOT has structural corrosion advisory recurring from a prior annual cycle: latest advisory −0.15, recurrence −0.60, current structural −1.25, raw 8.0; special recurring-corrosion cap makes score **6.0**. Do not separately deduct the alternative −0.75 corrosion row.
- Prior failed MOT with a defective bulb, subsequently passed on retest and with no supporting persistence evidence: **do not** deduct an unresolved-major penalty for that old bulb.

## F. Required calculation trace (retain internally; show if asked)

For every assessed car, identify the testing cycles used, distinguish current defects from historic failed tests later superseded by a pass, and retain a concise trace:

`10.0 − eligible current major/dangerous − min(1.5, current minor+advisory) − distinct recurrence/progression/other historical deductions = raw; clamp; apply lowest safety cap; round 0.5; classify.`

Every line of the trace needs a recorded defect/system and annual cycle. Never presume repeat defects across retests are multiple annual cycles. If user requests the optional 100-point view, present its seven scored categories **separately**; no adjustment to the primary fixed score.
