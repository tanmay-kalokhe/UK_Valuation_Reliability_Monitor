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
| 1 | Load the data into DuckDB; SQL matching with match-rate and bias reporting; data dictionary; Power BI pages 1–2 |
| 2 | Baseline vs LightGBM/CatBoost; time and local-authority holdouts; conformal intervals; coverage by area; Power BI page 3 |
| 3 | Monthly replay with monitoring and alerts; Power BI page 4; Streamlit demo; results write-up |

## Setup
```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m pytest
```

## Results
_To be added once the build is complete._
