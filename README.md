# UK Valuation Reliability Monitor

**When can an automated property valuation be trusted?**

This project estimates the value of homes in England and Wales, attaches a calibrated price range to each estimate, and monitors month by month whether the model remains reliable in each area. It recommends accepting the automated valuation or referring the property to a surveyor.

> Status: setup complete; build not started. See `PROJECT_BRIEF.md` for the full rationale.

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
```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pip install -e .
.venv\Scripts\pre-commit install
.venv\Scripts\python -m pytest
```
Exact package versions are in `requirements-lock.txt`. Pre-commit checks block data and `.pbix` files, lint Python (ruff) and SQL (sqlfluff), and strip notebook outputs before each commit.

## Tools
| Tool | Used for |
|---|---|
| DuckDB (Python and CLI) | All SQL: staging, matching, features, monitoring summaries |
| Splink | Probabilistic record linkage, compared with SQL rules |
| LightGBM, CatBoost, scikit-learn, MAPIE | Models and conformal price ranges |
| SHAP | Per-valuation explanations |
| MLflow | Experiment tracking (`mlflow ui`) |
| Power BI Desktop | Four-page report (`dashboards/power_bi/`) |
| Streamlit, Plotly | Public interactive demo and maps |
| pytest, ruff, sqlfluff, pre-commit, nbstripout | Tests and code quality |

## Results
_To be added once the build is complete._
