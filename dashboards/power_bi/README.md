# Power BI report: build guide

**Purpose:** a four-page Power BI report on the project's results, built by hand by Tanmay so that Power BI, Power Query and DAX can be listed truthfully on the CV. The guide gives the design; the clicking, measures and layout are Tanmay's own work.

**Honesty rule:** list Power BI on the CV only once this report is built and its screenshots are in the repository.

## Setup (once)
1. Install **Power BI Desktop** (free) from the Microsoft Store, which keeps it updated.
2. Enable the project format: File → Options and settings → Options → Preview features → **Power BI Project (.pbip) save option** (if it is listed as a preview feature).
3. Run the export: `.venv\Scripts\python -m valuation_monitor.exports`. Parquet files appear in `dashboards/power_bi/data/`. The Week 1 export already supports pages 1 and 2.

## Build order: one page per project stage
| When | Page | Needs |
|---|---|---|
| End of Week 1 | 1 Market overview, 2 Data quality | `fact_sales` (market and match columns), dimensions |
| End of Week 2 | 3 Model performance | Model columns in `fact_sales` |
| End of Week 3 | 4 Reliability monitor | `fact_monitoring`, the what-if parameter |

## Step by step
1. **Get data:** Get data → Parquet, one query per file. In Power Query, check the column types against `data_model.md`, rename queries to the table names, and disable load for any helper queries.
2. **Model:** create the relationships in `data_model.md` (Model view). Build `dim_date` in DAX and mark it as the date table. Hide the key columns on the fact tables.
3. **Measures:** create a `_Measures` table (Enter data → one dummy column, then hide it). Add the measures from `data_model.md` in display folders. Format percentages and £ values.
4. **Theme:** View → Themes → Browse for themes → `theme/valuation_monitor_theme.json`. Its colours are checked to remain distinguishable for colour-blind viewers.
5. **Pages:** build them as specified below.
6. **Save:** File → Save as → **Power BI project (.pbip)** in this folder, named `UK_Valuation_Reliability_Monitor.pbip`. Do not save `.pbix` files here: they embed the data, and `.gitignore` excludes them.
7. **Evidence for the repository:** export each page as PNG to `reports/figures/` (e.g. `pbi_01_market_overview.png`) and the whole report to PDF (File → Export → PDF).

## Page design
**Common to all pages:** a single row of slicers at the top (date range, local authority, property type), a title stating the question the page answers, and at most six visuals.

1. **Market overview**: *What is happening in the local market?*
   - KPI cards: Sales, Median Price, Median Price YoY %.
   - Line chart: Median Price by month, by property type.
   - Bar chart: Sales by local authority.
2. **Data quality**: *Which sales could be linked to EPC data, and does that bias the sample?*
   - Card: Match Rate.
   - Bar chart: Match Rate by local authority and by property type.
   - Clustered bar: Median Price Matched vs Unmatched by property type.
   - A text box explaining the finding in one sentence.
3. **Model performance**: *Does the model beat the simple baseline, and are its ranges honest?*
   - Clustered bar: Model vs Baseline MdAPE by local authority.
   - Bar chart: Coverage by local authority, with a constant line at Target Coverage (90%).
   - Card: Improvement vs Baseline.
4. **Reliability monitor**: *Where and when can the valuations be trusted?*
   - Matrix: local authority × month, showing Coverage with conditional formatting. Use the status colours with icons, never colour alone.
   - Table: alerts with their reasons.
   - What-if sliders: **LTV** and **Stress Cap**, with cards for Automation Rate, Accepted Coverage and Accepted MdAPE.
   - Line chart: Automation Rate and Accepted Coverage across LTV values (LTV on the x-axis).
   - Map: alerts by local authority, using the **Shape map** visual with a custom TopoJSON of ONS local-authority boundaries (prepared in Week 4). Shape map avoids the Bing and Azure Maps sign-in settings.

**Extras that show depth (optional):**
- A drill-through page from a local authority to its postcode districts.
- A report-page tooltip on the matrix.
- A bookmark-driven "About this report" panel.

## Skills this demonstrates
Power Query typing and shaping, star-schema modelling with a snowflaked dimension, a DAX date table, time intelligence (`DATEADD`), `CALCULATE` with filter modification, two what-if parameters driving an LTV-aware decision rule with variables, conditional formatting, drill-through and a custom theme.

Microsoft's free PL-300 learning path on Microsoft Learn covers each of these if more practice is needed.
