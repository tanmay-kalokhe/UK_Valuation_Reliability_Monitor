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
| `lower_ratio` | Decimal | range_lower ÷ estimate_model; drives the LTV-aware decision |
| `decision` | Text | `Accept` or `Refer` at the default LTV (75%) and stress cap (100%) |

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

### What-if parameters: the LTV-aware accept-or-refer rule
**The rule (decision D-013).**
- **Loan:** loan = LTV × estimate.
- **Stressed LTV:** stressed LTV = loan ÷ the lower end of the price range. This is the LTV if the property turns out to be worth only the pessimistic value.
- **Decision:** the valuation is **accepted** when the stressed LTV is at or below the **stress cap**, and **referred** to a surveyor otherwise.
- **Single-column test:** algebraically, accept when `lower_ratio ≥ LTV ÷ stress cap`. This means the measures compare one column with a scalar.
- **Effect:** a 60% LTV mortgage tolerates a wide price range, while a 95% LTV mortgage needs a very tight one.

Create two parameters with Modeling → New parameter → Numeric range:
- **LTV**: 0.50 to 0.95, increment 0.05, default 0.75.
- **Stress Cap**: 0.90 to 1.00, increment 0.01, default 1.00 (no negative equity at the pessimistic value).

Power BI creates the tables, slicers and the measures `LTV Value` and `Stress Cap Value`.

```dax
Min Lower Ratio = DIVIDE ( [LTV Value], [Stress Cap Value] )

Automation Rate =
VAR MinRatio = [Min Lower Ratio]
RETURN
DIVIDE (
    CALCULATE ( [Test Sales], fact_sales[lower_ratio] >= MinRatio ),
    [Test Sales]
)

Accepted Coverage =
VAR MinRatio = [Min Lower Ratio]
RETURN CALCULATE ( [Coverage], fact_sales[lower_ratio] >= MinRatio )

Accepted MdAPE =
VAR MinRatio = [Min Lower Ratio]
RETURN CALCULATE ( [Model MdAPE], fact_sales[lower_ratio] >= MinRatio )
```
The variable captures the slicer value before `CALCULATE` changes the filter context. That is a standard interview question on context transition.

**Chart idea:** put the LTV parameter column on the x-axis of a line chart with `Automation Rate` and `Accepted Coverage`. Each point evaluates the measures at that LTV, which shows how automation falls as LTV rises.

**Caveat to state on the report:** the stress cap and the defaults are illustrative design choices, not any lender's policy.
