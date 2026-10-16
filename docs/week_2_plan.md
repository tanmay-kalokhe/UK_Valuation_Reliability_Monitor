# Week 2 plan: matching accuracy, baseline and models

_Prepared 16 October 2026. The plan is updated as tasks finish, and decisions move to `decision_log.md` when they are made._

## Goal
By the end of the week, answer two questions with measured figures:
1. **How accurate is the address matching?** Report the precision and recall of the SQL rules and of Splink, judged on 300 hand-checked sales.
2. **Does machine learning beat a simple industry method?** Compare LightGBM and CatBoost with an HPI-indexed district median, on a time-based holdout and on local-authority holdouts.

## Tasks
| # | Task | Owner | Output | Status |
|---|---|---|---|---|
| 1 | Draw the stratified hand-check sample and write the blind labelling sheet | Claude | `match_review.py sample`, D-019 | Done |
| 2 | **Label the 300 sales**, following `docs/hand_check_protocol.md` | **Tanmay** | `answer` column filled in | To do |
| 3 | Probabilistic matching with Splink 5 on DuckDB: block on postcode; compare house/flat identifiers, address words (Jaro-Winkler) and street; train by expectation-maximisation; choose the threshold from the match-weight distribution | Claude | `splink_link` table and its module | To do |
| 4 | Score both methods against the labels: weighted precision and recall with bootstrap confidence intervals, then re-tune the SQL thresholds if the labels justify it | Claude | `match_review.py score`, new section and figure in `reports/match_quality.md` | Waits for 2 and 3 |
| 5 | Feature SQL (`sql/03_features/`): EPC attributes of the linked certificate, certificate age, local price trends using only earlier sales (window functions), previous sale of the same property, HPI for the sale month | Claude | `model_input` table, data dictionary | To do |
| 6 | Baseline: median price for the postcode district and property type over the training window, indexed to the sale month with the local-authority HPI for that type | Claude | `baseline.py` | To do |
| 7 | Validation design: time-based split and leave-one-local-authority-out; metrics MdAPE, PPE10 and PPE20 (share within 10% and 20% of the price), with bootstrap confidence intervals | Claude | `validation.py`, tests | To do |
| 8 | LightGBM and CatBoost on log price, tracked in MLflow, compared with the baseline on both holdouts | Claude | `modelling.py`, `reports/model_performance.md` | To do |
| 9 | Add the model columns to the Power BI export, then build page 3 | Claude, then **Tanmay** | `exports.py`, `dashboards/power_bi/step_by_step_guide.md` Phase 8 | Waits for 8 |

Tasks 3, 5, 6 and 7 do not depend on the labels. They proceed while the labelling (task 2) is under way.

## Proposed time split (to confirm before task 7)
| Period | Months | Use |
|---|---|---|
| 2020 | Jan–Dec 2020 | Only as history for lagged features and the baseline. Never scored. |
| Training | Jan 2021 – Feb 2025 | Fit the models and the baseline medians. |
| Calibration | Mar 2025 – Aug 2025 | Held back for the conformal price ranges in Week 3. Also used for early stopping. |
| Test | Sep 2025 – Aug 2026 | 12 unseen months. Also the period replayed month by month in Week 3. |

Features use only information available before each sale (sale date and earlier), and the baseline medians use only training sales. The local-authority holdout trains on six areas and tests on the seventh, in turn, over the same months.

## Decisions for Tanmay
- **Time split:** accept the split above, or move it. A longer test period gives a better replay, but less recent training data.
- **Metrics:** PPE10 and PPE20 are added beside MdAPE because UK AVM providers quote "share within 10%" figures. Keep them, or drop them.
