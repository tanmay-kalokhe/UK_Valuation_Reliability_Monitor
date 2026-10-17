# UK Valuation Reliability Monitor

**When can an automated property valuation be trusted?**

This project estimates the value of homes in England and Wales, attaches a calibrated price range to each estimate, and monitors month by month whether the model remains reliable in each area. It recommends accepting the automated valuation or referring the property to a surveyor.

> Status: Week 1 of 4 complete (data loaded and linked); Week 2 (matching comparison and models) next. See `PROJECT_BRIEF.md` for the full rationale.

## Data (public, not committed)
- HM Land Registry Price Paid Data
- Energy Performance Certificates (England and Wales)
- UK House Price Index
- Postcode-to-geography lookup

Download instructions and licence notes are in `data/README.md`.

## Project layout
```
UK_Valuation_Reliability_Monitor/
├── PROJECT_BRIEF.md          what, why, market relevance
├── config/                   project_config.yaml: scope, thresholds, paths
├── data/                     raw / interim / processed (git-ignored)
├── sql/                      01_staging → 02_matching → 03_features → 04_monitoring
├── src/valuation_monitor/    Python package, one module per stage
├── dashboards/               power_bi/ (4-page report, .pbip) and streamlit/ (interactive demo)
├── notebooks/                exploration only
├── tests/                    pytest checks
├── reports/figures/          charts for the write-up
└── docs/                     decision log and data dictionary
```

## Build plan
| Week | Deliverable |
|---|---|
| 1 | Load the data into DuckDB; SQL address matching with match-rate and bias reporting; data dictionary; Power BI pages 1–2 |
| 2 | Splink vs SQL matching on 300 hand-checked pairs; baseline vs LightGBM/CatBoost on time and local-authority holdouts, tracked in MLflow |
| 3 | Conformal price ranges and coverage by area; monthly replay with monitoring and alerts; Power BI page 3 |
| 4 | Maps (local authority and MSOA); Power BI page 4; hosted Streamlit demo; results write-up |

**Study area:** Manchester, Trafford, Leeds, Milton Keynes, Camden, Cornwall and Cardiff. **Intended user:** a mortgage lender's valuation team.

## Setup
Packages are installed into the main Python 3.12 interpreter (no virtual environment). One command does the whole setup and leaves any package the interpreter already has at its current version:
```powershell
powershell -ExecutionPolicy Bypass -File .\setup_local_env.ps1
```
The equivalent manual steps:
```powershell
py -3.12 -m pip install -r requirements-dev.txt -c requirements-lock.txt
py -3.12 -m pip install -e .
py -3.12 -m pre_commit install
py -3.12 -m pytest
```
Run project tools through the launcher, for example `py -3.12 -m streamlit run dashboards/streamlit/app.py`, `py -3.12 -m mlflow ui` and `py -3.12 -m jupyterlab`.
Exact package versions are in `requirements-lock.txt`. Pre-commit checks block data and `.pbix` files, lint Python (ruff) and SQL (sqlfluff), and strip notebook outputs before each commit.

## Tools
| Tool | Used for |
|---|---|
| DuckDB (Python and CLI) | All SQL: staging, matching, features, monitoring summaries |
| Splink | Probabilistic record linkage, compared with SQL rules |
| LightGBM, CatBoost, scikit-learn, MAPIE | Models and conformal price ranges |
| SHAP | Per-valuation explanations |
| MLflow | Experiment tracking (`py -3.12 -m mlflow ui`) |
| Power BI Desktop | Four-page report (`dashboards/power_bi/`) |
| Streamlit, Plotly | Public interactive demo and maps |
| pytest, ruff, sqlfluff, pre-commit, nbstripout | Tests and code quality |

## Progress
- **Week 1 (done):** staging tables in DuckDB and SQL address matching. **94.8%** of 256,677 standard sales (2020 to Aug 2026) were linked to an energy certificate lodged before the sale. The full report, including where matching falls short (Camden 80%, flats 87%), is in [`reports/match_quality.md`](reports/match_quality.md).
- **Week 2 (mostly done):** features with a three-month information cut-off, the baseline, LightGBM and CatBoost on both holdouts, and Splink matching. The hand-checked matching accuracy waits for labelling (protocol in [`docs/hand_check_protocol.md`](docs/hand_check_protocol.md)). Status in [`docs/week_2_plan.md`](docs/week_2_plan.md).
- **Power BI:** a click-by-click build guide with checkpoint figures is in [`dashboards/power_bi/step_by_step_guide.md`](dashboards/power_bi/step_by_step_guide.md).

## Results
**Valuation accuracy**, 27,639 matched sales in the 12 test months (Sep 2025 to Aug 2026), never used in training. Full results with 95% confidence intervals are in [`reports/model_performance.md`](reports/model_performance.md).

| | Median absolute error | Within 10% of price | Within 20% of price |
|---|---:|---:|---:|
| Baseline (HPI-indexed district median) | 19.0% | 28.7% | 52.0% |
| LightGBM (selected on the calibration period) | **10.0%** | **50.0%** | **77.9%** |

- **Unseen areas:** trained on six local authorities and tested on the seventh, LightGBM's median error is 11.6% overall. Camden is the weak point: 19.6%, against 13.6% when its own sales are in training.
- **Limitations:** only sales linked to an energy certificate are modelled; flats and Camden link least often (see the match report). Hyperparameters are not tuned. The sale price is treated as the true value.
