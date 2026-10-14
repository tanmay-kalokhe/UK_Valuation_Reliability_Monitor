# Power BI data model

A star schema (snowflaked for the area hierarchy) fed by Parquet files that `src/valuation_monitor/exports.py` writes to `dashboards/power_bi/data/`. **No table contains address fields.** The data folder is git-ignored; the model definition is committed through the `.pbip` project format.

## Tables

### Facts

**`fact_sales`**: one row per Category A sale in the study area.

| Column | Type | Notes |
|---|---|---|
| `sale_key` | Whole number | Surrogate key, not the Land Registry transaction ID (which could be re-linked to an address) |
| `sale_date` | Date | |
| `postcode_district` | Text | e.g. `LS6`; the finest location level exported |
| `property_type_code` | Text | D, S, T, F, O |
| `new_build` | True/False | |
| `tenure` | Text | F (freehold) or L (leasehold) |
| `price` | Whole number | £ |
| `epc_matched` | True/False | Whether the sale was linked to an EPC certificate |
| `in_test_set` | True/False | Sales scored by the model in the time-based test period |
| `estimate_model`, `estimate_baseline` | Whole number | £; blank outside the test set |
| `range_lower`, `range_upper` | Whole number | £; the 90% price range |
| `covered` | True/False | Price fell inside the range |
| `ape_model`, `ape_baseline` | Decimal | Absolute percentage error |
| `interval_width_pct` | Decimal | (upper − lower) ÷ estimate |
| `decision` | Text | `Accept` or `Refer` at the default threshold |

**`fact_monitoring`**: one row per local authority and month, produced by the Python monitor (the alert rule uses confidence intervals, which are computed in Python, not DAX).

| Column | Type |
|---|---|
| `month_start` | Date |
| `local_authority_code` | Text |
| `test_sales` | Whole number |
| `coverage`, `coverage_ci_lower`, `coverage_ci_upper` | Decimal |
| `mdape` | Decimal |
| `alert` | True/False |
| `alert_reason` | Text |

### Dimensions
| Table | Key | Other columns | Source |
|---|---|---|---|
| `dim_date` | `date` | year, month number, month name, year-month, month start | **Built in DAX** (see below) |
| `dim_area` | `postcode_district` | `local_authority_code` | Export |
| `dim_local_authority` | `local_authority_code` | `local_authority_name`, `region` | Export |
| `dim_property_type` | `property_type_code` | `property_type_name` (Detached, Semi-detached, Terraced, Flat/Maisonette, Other), `sort_order` | Export |

## Relationships (all many-to-one, single direction)
| From | To |
|---|---|
| `fact_sales[sale_date]` | `dim_date[date]` |
| `fact_sales[postcode_district]` | `dim_area[postcode_district]` |
| `dim_area[local_authority_code]` | `dim_local_authority[local_authority_code]` |
| `fact_sales[property_type_code]` | `dim_property_type[property_type_code]` |
| `fact_monitoring[month_start]` | `dim_date[date]` |
| `fact_monitoring[local_authority_code]` | `dim_local_authority[local_authority_code]` |

Mark `dim_date` as the date table (Table tools → Mark as date table).

## Date table (DAX calculated table)
```dax
dim_date =
VAR FirstDate = DATE ( YEAR ( MIN ( fact_sales[sale_date] ) ), 1, 1 )
VAR LastDate  = DATE ( YEAR ( MAX ( fact_sales[sale_date] ) ), 12, 31 )
RETURN
ADDCOLUMNS (
    CALENDAR ( FirstDate, LastDate ),
    "Year", YEAR ( [Date] ),
    "Month Number", MONTH ( [Date] ),
    "Month Name", FORMAT ( [Date], "mmm" ),
    "Year Month", FORMAT ( [Date], "yyyy-mm" ),
    "Month Start", DATE ( YEAR ( [Date] ), MONTH ( [Date] ), 1 )
)
```
Rename the `Date` column to `date`, or keep `Date` and use that name in the relationships. Sort `Month Name` by `Month Number`.

## Measures
Keep the measures in a dedicated `_Measures` table, in display folders: Market, Data quality, Model, Reliability.

```dax
// Market
Sales = COUNTROWS ( fact_sales )
Median Price = MEDIAN ( fact_sales[price] )
Median Price YoY % =
VAR PriorYear = CALCULATE ( [Median Price], DATEADD ( dim_date[date], -12, MONTH ) )
RETURN DIVIDE ( [Median Price] - PriorYear, PriorYear )

// Data quality
Matched Sales = CALCULATE ( [Sales], fact_sales[epc_matched] = TRUE () )
Match Rate = DIVIDE ( [Matched Sales], [Sales] )
Median Price Matched = CALCULATE ( [Median Price], fact_sales[epc_matched] = TRUE () )
Median Price Unmatched = CALCULATE ( [Median Price], fact_sales[epc_matched] = FALSE () )

// Model
Test Sales = CALCULATE ( [Sales], fact_sales[in_test_set] = TRUE () )
Model MdAPE = CALCULATE ( MEDIAN ( fact_sales[ape_model] ), fact_sales[in_test_set] = TRUE () )
Baseline MdAPE = CALCULATE ( MEDIAN ( fact_sales[ape_baseline] ), fact_sales[in_test_set] = TRUE () )
Improvement vs Baseline = DIVIDE ( [Baseline MdAPE] - [Model MdAPE], [Baseline MdAPE] )

// Reliability
Target Coverage = 0.90
Coverage =
DIVIDE (
    CALCULATE ( [Sales], fact_sales[in_test_set] = TRUE (), fact_sales[covered] = TRUE () ),
    [Test Sales]
)
Coverage Gap = [Coverage] - [Target Coverage]
Coverage Previous Month = CALCULATE ( [Coverage], DATEADD ( dim_date[date], -1, MONTH ) )
Median Interval Width % =
CALCULATE ( MEDIAN ( fact_sales[interval_width_pct] ), fact_sales[in_test_set] = TRUE () )
Areas on Alert =
CALCULATE ( DISTINCTCOUNT ( fact_monitoring[local_authority_code] ), fact_monitoring[alert] = TRUE () )
```

### What-if parameter: accept-or-refer threshold
Create it with Modeling → New parameter → Numeric range: name **Max Interval Width**, 0.05 to 0.50, increment 0.01, default 0.20. Power BI creates the table, the slicer and the measure `Max Interval Width Value`.

```dax
Automation Rate =
VAR MaxWidth = [Max Interval Width Value]
RETURN
DIVIDE (
    CALCULATE ( [Test Sales], fact_sales[interval_width_pct] <= MaxWidth ),
    [Test Sales]
)

Accepted Coverage =
VAR MaxWidth = [Max Interval Width Value]
RETURN CALCULATE ( [Coverage], fact_sales[interval_width_pct] <= MaxWidth )

Accepted MdAPE =
VAR MaxWidth = [Max Interval Width Value]
RETURN CALCULATE ( [Model MdAPE], fact_sales[interval_width_pct] <= MaxWidth )
```
The variable captures the slicer value before `CALCULATE` changes the filter context. That is a standard interview question on context transition.
