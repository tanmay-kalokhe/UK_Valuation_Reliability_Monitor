# Week 2 plan: matching accuracy, baseline and models

_Prepared 16 October 2026, updated 17 October 2026. Decisions move to `decision_log.md` when they are made._

## Goal
By the end of the week, answer two questions with measured figures:
1. **How accurate is the address matching?** Report the precision and recall of the SQL rules and of Splink, judged on 300 hand-checked sales.
2. **Does machine learning beat a simple industry method?** Compare LightGBM and CatBoost with an HPI-indexed district median, on a time-based holdout and on local-authority holdouts.

## Tasks
| # | Task | Owner | Output | Status |
|---|---|---|---|---|
| 1 | Draw the stratified hand-check sample and write the blind labelling sheet | Claude | `match_review.py sample`, D-019 | Done |
| 2 | **Label the 300 sales**, following `docs/hand_check_protocol.md` | **Tanmay** | `answer` column filled in | **To do** |
| 3 | Probabilistic matching with Splink 5, blocked on postcode like the SQL rules | Claude | `match_splink.py`, `splink_link`, D-023 | Done (threshold provisional) |
| 4 | Score both methods against the labels; choose the Splink threshold; re-tune the SQL thresholds if justified | Claude | `match_accuracy.py` → `reports/match_accuracy.md` | Code ready and tested; waits for task 2 |
| 5 | Feature SQL (`sql/03_features/`) with an information cut-off | Claude | `model_input`, D-022, `tests/test_features.py` | Done |
| 6 | HPI-indexed district-median baseline | Claude | `03_feat_baseline.sql`, `baseline.py` | Done |
| 7 | Time split and leave-one-local-authority-out; MdAPE, PPE10, PPE20 and bias with bootstrap intervals | Claude | `validation.py`, D-020, D-021 | Done |
| 8 | LightGBM and CatBoost, tracked in MLflow, compared with the baseline on both holdouts | Claude | `modelling.py`, `reports/model_performance.md` | Done |
| 9 | Model columns in the Power BI export; then page 3 (accuracy visuals) | Claude, then **Tanmay** | `exports.py`; guide Phase 8 | Export done; page 3 is Tanmay's |

## Results so far
**Models (time split, 27,639 test sales, Sep 2025 to Aug 2026).** Full tables with 95% intervals are in `reports/model_performance.md`.

| Estimator | MdAPE | PPE10 | PPE20 |
|---|---:|---:|---:|
| Baseline | 19.0% | 28.7% | 52.0% |
| LightGBM | 10.0% | 50.0% | 77.9% |
| CatBoost | 10.2% | 49.4% | 77.6% |

- LightGBM was selected on the calibration period (9.83% against 9.92%), not on the test period. It goes forward to Week 3.
- On an unseen local authority, pooled MdAPE rises to 11.6%. Camden suffers most: 13.6% with its own sales in training, 19.6% without. Its high-value flat market is unlike the other six areas.

**Splink against the SQL rules (no labels yet).** At the provisional 0.9 threshold, Splink links 90.0% of sales. At property level the two methods:

| Outcome | Sales |
|---|---:|
| Agree on the same property | 223,184 |
| Pick different properties | 3,869 |
| Linked only by Splink | 4,037 |
| Linked only by the SQL rules | 16,685 |

Which method is right on the disagreements is what the labels will show.

## Next
- Tanmay labels the sheet (task 2). Claude then runs `py -3.12 -m valuation_monitor.match_accuracy` and reports precision and recall.
- Week 3: conformal price ranges on the calibration period, coverage by area, type and month, and the monthly replay.
