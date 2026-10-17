# Power BI report: step-by-step guide

This guide takes you from installing Power BI Desktop to a finished, committed four-page report, assuming you know basic Excel but have not used Power BI before. It complements [README.md](README.md), which gives the short build order and page design, and [data_model.md](data_model.md), which is the reference for tables, relationships and DAX. Each measure is copied into the step where you create it, so you do not need to switch files mid-step; if the guide and `data_model.md` ever disagree, `data_model.md` is correct and the guide should be fixed.

You build the report yourself. Nothing in this repository generates the `.pbip` report for you, which is what makes the skill genuinely yours.

Menu paths are written in bold with arrows, for example **Home → Get data**. Power BI Desktop is updated monthly, so a label may differ slightly between versions; labels that vary are marked as such.

---

## 1. Before you start

### What you will build
A four-page report, one page per project stage, for the intended user: a mortgage lender's valuation team.

| Page | Question it answers | Project stage |
|---|---|---|
| 1 Market overview | What is happening in the local market? | Data linkage |
| 2 Data quality | Which sales could be linked to EPC data, and does that bias the sample? | Data linkage |
| 3 Model performance | Does the model beat the simple baseline, and are its ranges honest? | Modelling and uncertainty |
| 4 Reliability monitor | Where and when can the valuations be trusted? | Monitoring |

### What is ready now and what is not
- **Ready now (Week 1 data):** pages 1 and 2. `fact_sales` already has the market columns and the match columns (`epc_matched`, `match_status`, `match_tier`).
- **After Week 2 (ready once the export is re-run):** the accuracy part of page 3. `fact_sales` gains `in_test_set`, `estimate_model`, `estimate_baseline`, `ape_model` and `ape_baseline`.
- **After Week 3:** the price-range columns (`range_lower`, `range_upper`, `covered`, `interval_width_pct`, `lower_ratio`, `decision`) for the coverage visual on page 3 and for page 4.
- **Later, after Week 3:** page 4 needs the `fact_monitoring` table plus the model columns above.

Do not try to build pages 3 and 4 yet: the columns do not exist, so the measures would fail. Phases 8 and 9 are marked accordingly.

### Time estimates
| Phase | Estimate |
|---|---|
| 0 Install and configure | 20 minutes |
| 1 Refresh the data | 10 minutes |
| 2 Power Query | 45 minutes |
| 3 Model view | 60 minutes |
| 4 Theme and page template | 30 minutes |
| 5 Page 1 | 60 minutes |
| 6 Page 2 | 60 minutes |
| Checkpoints | 20 minutes |
| 7 Save and commit | 30 minutes |
| 8 Page 3 (after Week 2) | 60 minutes |
| 9 Page 4 (after Week 3) | 120 minutes |
| Optional extras | 60 to 90 minutes |

These are estimates for a first-time user, not measured figures. Expect Phase 3 and the checkpoints to take longest the first time.

### The honesty rule
List Power BI on the CV and LinkedIn **only once the report is built and its screenshots are in the repository**. Use only figures that are true (for example, the real number of measures you wrote).

---

## 2. Phase 0 – Install and configure

1. Open the **Microsoft Store**, search for **Power BI Desktop** and choose **Install**. The Store version updates itself.
2. Open Power BI Desktop. Close the sign-in prompt; you do not need an account for a local report.
3. Go to **File → Options and settings → Options → Preview features**.
4. Tick **Power BI Project (.pbip) save option**. If **Store semantic model using TMDL format** is listed, tick that too. (Preview feature names change between versions; if neither appears, update Power BI Desktop through the Store and look again.)
5. Go to **Options → Current File → Data Load** and untick **Auto date/time**.
   - **Why:** by default Power BI silently creates a hidden date table for every date column. We build our own `dim_date` in Phase 3 so that time intelligence (`DATEADD`) works from one visible, marked date table and the checkpoints match. Leaving Auto date/time on is the most common cause of confusing date behaviour.
   - This is a **Current File** setting. Re-check it after you save the project in Phase 7. You can also set **Options → Global → Data Load → Time intelligence** so that new files start with it off (the label may differ slightly between versions).
6. Go to **Options → Current File → Regional Settings** and set **Locale for import** to **English (United Kingdom)**. Under **Options → Global → Regional Settings**, set the application language to match if offered.
   - **Why:** this makes £ and dd/mm/yyyy display correctly. You also set formats on each column and measure later, so the display does not depend on your computer's settings.
7. Click **OK**. Restart Power BI Desktop if it asks you to, because preview features only apply after a restart.

---

## 3. Phase 1 – Refresh the data

The Parquet files are git-ignored and contain no address fields. You regenerate them whenever the pipeline changes.

1. Open **PowerShell** and move to the project folder:
   ```powershell
   cd D:\UK_Valuation_Reliability_Monitor
   ```
2. Run the export. Always use `py -3.12`, because Python 3.14 may be the default `python`:
   ```powershell
   py -3.12 -m valuation_monitor.exports
   ```
3. The export prints one line per file, for example `wrote fact_sales.parquet: 256,638 rows`. Check that these four files now exist in `dashboards/power_bi/data/`:

| File | Content |
|---|---|
| `dim_local_authority.parquet` | One row per local authority: code, name, market, nation |
| `dim_area.parquet` | One row per local authority and postcode district |
| `dim_property_type.parquet` | Detached, Semi-detached, Terraced, Flat/Maisonette, with sort order |
| `fact_sales.parquet` | One row per Category A sale, no address fields |

4. `fact_monitoring.parquet` is **not** written yet. It arrives in Week 3, and you will repeat this phase then.
5. Never copy these files elsewhere, publish them or commit them.

---

## 4. Phase 2 – Power Query (Get data)

Power Query is the data-loading layer. Every step you take is recorded and replayed on each refresh, which is the point: the report stays reproducible.

### 4.1 Create a folder parameter
Using a parameter means you change one value if the project moves folders.

1. Click **Home → Transform data** to open the Power Query Editor.
2. In the editor, click **Home → Manage Parameters → New Parameter**.
3. Set:
   - **Name:** `DataFolder`
   - **Type:** Text
   - **Suggested Values:** Any value
   - **Current Value:** the absolute path to the folder, **ending with a backslash**:
     ```
     D:\UK_Valuation_Reliability_Monitor\dashboards\power_bi\data\
     ```
4. Click **OK**.

### 4.2 Load each Parquet file
1. In the editor, click **Home → New Source → More… → Parquet**. (Or close the editor and use **Home → Get data → More… → Parquet** in the main window.)
2. Browse to `fact_sales.parquet` once, just to create the query. Click **OK**.
3. With the new query selected, open **Home → Advanced Editor** and replace the source line so that it uses the parameter. The exact M for `fact_sales` is:
   ```powerquery
   let
       Source = Parquet.Document(File.Contents(DataFolder & "fact_sales.parquet"))
   in
       Source
   ```
   Power BI may generate extra steps (such as `Navigation` or `Changed Type`) automatically. Keep any it makes only if they are correct; you will set the types explicitly below.
4. Click **Done**.
5. Repeat steps 1 to 4 for `dim_local_authority.parquet`, `dim_area.parquet` and `dim_property_type.parquet`, changing only the file name in the M.
6. Rename each query to its table name by right-clicking it in the **Queries** pane and choosing **Rename**, or by editing **Name** in **Query Settings**: `fact_sales`, `dim_local_authority`, `dim_area`, `dim_property_type`. Remove any `fact_sales (2)` style suffixes.
7. Leave `DataFolder` as a parameter. It does not load into the model.

### 4.3 Set the column types
For each table, click a column header, then **Transform → Data Type** (or click the type icon in the header). Use this checklist. Anything not listed should be Text.

**`fact_sales`**

| Column | Type to set |
|---|---|
| `sale_key` | Whole Number |
| `sale_date` | Date |
| `area_key` | Text |
| `postcode_district` | Text |
| `property_type_code` | Text |
| `new_build` | True/False |
| `tenure` | Text |
| `price` | Whole Number |
| `epc_matched` | True/False |
| `match_status` | Text |
| `match_tier` | Whole Number (blank when no candidate passed a rule; ambiguous sales and sales with only post-sale certificates still carry a tier) |

**`dim_local_authority`**

| Column | Type to set |
|---|---|
| `local_authority_code` | Text |
| `local_authority_name` | Text |
| `market` | Text |
| `nation` | Text |

**`dim_area`**

| Column | Type to set |
|---|---|
| `area_key` | Text |
| `postcode_district` | Text |
| `local_authority_code` | Text |

**`dim_property_type`**

| Column | Type to set |
|---|---|
| `property_type_code` | Text |
| `property_type_name` | Text |
| `sort_order` | Whole Number |

Keep `sale_date` as **Date**, not Date/Time: a relationship to `dim_date[date]` requires matching types.

Check that no column shows an error. If `new_build` or `epc_matched` arrive as text, that is a typing problem to fix here, not later in DAX.

### 4.4 Close and apply
1. Click **Home → Close & Apply**.
2. Wait for the load. `fact_sales` has about a quarter of a million rows, which Power BI handles easily.
3. Save a working copy as a `.pbix` in a folder **outside** the repository for now (for example your Documents folder) if you want a safety net. You convert to `.pbip` inside the repository in Phase 7. Never save a `.pbix` in the repository: it embeds the data.

---

## 5. Phase 3 – Model view (star schema)

### 5.1 Build `dim_date`
1. Click **Modeling → New table** (the label may be under **Table tools** in some versions).
2. Paste this DAX and press Enter:
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
   The calendar runs from 1 January of the first sale year to 31 December of the last, so it is **contiguous** with no gaps. That matters for time intelligence.
3. In the **Data** pane, select the `Date` column, then **Column tools → Name** and rename it to `date`.
4. Set formats: `date` and `Month Start` as **Date** with format `dd/mm/yyyy`; `Year` and `Month Number` as **Whole number** with the thousands separator **off** (otherwise 2024 appears as 2,024).
5. Select `Month Name`, then **Column tools → Sort by column → Month Number**. Without this, months sort alphabetically (Apr, Aug, Dec...).
6. Select `Year Month` text: it sorts correctly as it is, because the format is `yyyy-mm`.
7. Select the `dim_date` table, then **Table tools → Mark as date table**, choose `date` as the date column and click **OK**. (If you cannot find it, right-click the table in the **Data** pane.)
8. Optionally set **Column tools → Summarization → Don't summarise** on `Year` and `Month Number`, so they are not added up in visuals.

### 5.2 Create the relationships
1. Open **Model view** (the third icon on the left rail).
2. Create each relationship by dragging the column from the **many** side (the fact or child table) onto the matching column of the **one** side (the dimension). Power BI opens **Create relationship**. Check **Cardinality: Many to one (*:1)**, **Cross-filter direction: Single**, **Make this relationship active** ticked, then click **Save**.
3. Create these four relationships now:

| From (many) | To (one) |
|---|---|
| `fact_sales[sale_date]` | `dim_date[date]` |
| `fact_sales[area_key]` | `dim_area[area_key]` |
| `dim_area[local_authority_code]` | `dim_local_authority[local_authority_code]` |
| `fact_sales[property_type_code]` | `dim_property_type[property_type_code]` |

4. The two `fact_monitoring` relationships (`fact_monitoring[month_start]` to `dim_date[date]`, and `fact_monitoring[local_authority_code]` to `dim_local_authority[local_authority_code]`) are created in Phase 9, when that table exists.
5. Check each line: the arrow points from the dimension towards the fact (filtering flows one way, from dimension to fact), the end at the dimension shows **1** and the end at the fact or child table shows **\***. A dotted line means the relationship is **inactive**; see the troubleshooting list in the checkpoints section.
6. Power BI may offer to auto-detect relationships. If it created any extra ones, delete them so that only the four above exist.

### 5.3 Why the area dimension is a snowflake
A pure star schema has every dimension attached directly to the fact table. Here, `fact_sales` joins to `dim_area` (the finest location level, a postcode district such as `LS6`), and `dim_area` joins to `dim_local_authority`. That is a **snowflake**: the local-authority attributes (name, market, nation) are stored once, not repeated on every district row. Filters still flow in one direction, from `dim_local_authority` to `dim_area` to `fact_sales`, so a local-authority slicer filters sales correctly. The reason for `area_key` being `local_authority_code|postcode_district` is that a district can cross a local-authority boundary, so the district alone is not a unique key.

### 5.4 Hide key columns
Hiding keys keeps the **Data** pane clean so that report authors use the dimension attributes, not raw keys.
1. In **Model view**, select `fact_sales[sale_key]`, `fact_sales[area_key]`, `fact_sales[property_type_code]` and `fact_sales[sale_date]`.
2. In the **Properties** pane, set **Is hidden** to **Yes**. (Hide `sale_date` only after you have confirmed the relationship; use `dim_date[date]` in visuals from now on.)
3. Also hide `dim_area[area_key]`, `dim_area[local_authority_code]`, `dim_local_authority[local_authority_code]` and `dim_property_type[property_type_code]`.
4. On the `dim_property_type` table, select `property_type_name` and set **Sort by column → sort_order**, so property types appear as Detached, Semi-detached, Terraced, Flat/Maisonette rather than alphabetically.
5. Set data categories only if you need them; you do not for the Week 1 pages.

### 5.5 Create the `_Measures` table
All measures live in one table, which keeps them easy to find.
1. Click **Home → Enter data**.
2. Rename the single column from `Column1` to `Dummy`. Leave it empty.
3. Name the table `_Measures` and click **Load**.
4. In **Model view**, select the `Dummy` column and set **Is hidden** to **Yes**. Power BI then shows the table with a calculator icon once it holds measures. (If it does not, create your first measure first and it updates.)
5. To put a new measure in this table: select `_Measures` in the **Data** pane, then **Modeling → New measure** (the label may be under **Measure tools**), type the DAX, and press Enter.
6. To set a display folder: select the measure, then in the **Properties** pane enter the name under **Display folder** (for example `Market`).

---

## 6. Phase 4 – Theme and page template

### 6.1 Import the theme
1. Click **View → Themes**, open the drop-down arrow, then **Browse for themes**.
2. Select `dashboards/power_bi/theme/valuation_monitor_theme.json`. Click **Open**, then **OK**.
3. Confirm the palette changed. The colours (blue `#2A78D6`, orange `#EB6834`, green `#1BAF7A`, amber `#EDA100` and others) were chosen to remain distinguishable for colour-blind viewers. The theme also sets the status colours: good `#0CA30C`, neutral `#FAB219`, bad `#D03B3B`. You use these in page 4.
4. The theme sets the **Segoe UI** font family. If it does not display, you can still continue.

### 6.2 Build the page template once
1. Rename **Page 1** by double-clicking its tab: `1 Market overview`.
2. Insert a **Text box** (**Insert → Text box**) at the top. Type the page question: `What is happening in the local market?` Make it **Segoe UI Semibold**, size 14 or larger.
3. Insert three **Slicer** visuals in one row beneath the title:
   - **Date range:** add `dim_date[date]` to the slicer's **Field**. Set the slicer style to **Between** (**Format → Slicer settings → Options → Style → Between**). The label may differ slightly between versions.
   - **Local authority:** add `dim_local_authority[local_authority_name]`. Style: **Dropdown**.
   - **Property type:** add `dim_property_type[property_type_name]`. Style: **Dropdown**.
4. Align the three slicers in a single row. Select them, then **Format → Align → Align top** and **Distribute horizontally**.
5. Duplicate the page: right-click the tab and choose **Duplicate page**. Do this for the number of pages you need now (one duplicate for page 2). Later, duplicate again for pages 3 and 4. Duplicating keeps the slicers identical and in the same place.
6. Open **View → Sync slicers**. For each slicer, tick **Sync** (and **Visible**) for all pages so that choosing "Leeds" on page 1 still applies on page 2. Verify by setting a filter on one page and checking another.
7. Rename the second page `2 Data quality` and change its title text to its own question (see Phase 6).

---

## 7. Phase 5 – Page 1 Market overview

Page question: *What is happening in the local market?* Use at most six visuals, as the page design requires.

### 7.1 Measures for page 1
Create these in `_Measures` and set **Display folder** to `Market`.

1. **Sales**: format as **Whole number** with the thousands separator.
   ```dax
   Sales = COUNTROWS ( fact_sales )
   ```
2. **Median Price**: format as **Currency**, £ English (United Kingdom), **0 decimal places**.
   ```dax
   Median Price = MEDIAN ( fact_sales[price] )
   ```
3. **Median Price YoY %**: format as **Percentage**, **1 decimal place**.
   ```dax
   Median Price YoY % =
   VAR PriorYear = CALCULATE ( [Median Price], DATEADD ( dim_date[date], -12, MONTH ) )
   RETURN DIVIDE ( [Median Price] - PriorYear, PriorYear )
   ```

**Important note on `Median Price YoY %`.** `DATEADD` shifts whatever dates are currently selected in `dim_date` back by 12 months, which is why `dim_date` must be marked as a date table. The measure is therefore only meaningful when the visual has a clear period: a single year or a single month.
- **No date filter** (for example a plain card, or a bar chart by local authority only): it compares the median of *all* sales with the median of the dates shifted back a year (2020 to 2025). It returns a number, but that number is misleading.
- **A single year or month** (a card filtered to one year, or a line chart by month): it gives the true year-on-year change.
- **2020:** there is no earlier data, so the measure is blank for 2020 by design.

Always show it with a single-year filter or by month.

### 7.2 Visuals for page 1
**Visual A: card, Sales**
1. Click a blank part of the canvas, then **Visualizations → Card**. (The newer **Card (new)** is also fine; field wells differ slightly.)
2. Drag `Sales` into **Fields**.
3. Format: **Callout value** size 28 (the theme provides this), a clear label such as `Sales`.

**Visual B: card, Median Price**
1. Insert a **Card** and add `Median Price`.

**Visual C: card, Median Price YoY %**
1. Insert a **Card** and add `Median Price YoY %`.
2. Add a visual-level filter: **Filters → Filters on this visual → dim_date[Year]**, then choose the latest full year (for example 2025), so the card has a date context. Say so in the card title: `Median Price YoY % (2025)`.

**Visual D: line chart, Median Price by month by property type**
1. Insert a **Line chart**.
2. **X-axis:** `dim_date[Year Month]`. (If it shows as a hierarchy, remove the hierarchy levels so a single flat axis remains.) Set the axis type to **Categorical** (**Format → X-axis → Type**).
3. **Y-axis:** `Median Price`.
4. **Legend:** `dim_property_type[property_type_name]`.
5. Format: Y-axis start at 0 if you want honest scale, or leave automatic and label it clearly; add axis titles; turn on **Data labels** only for the last point if the chart is crowded.
6. Title: `Median price by month and property type`.

**Visual E: bar chart, Sales by local authority**
1. Insert a **Clustered bar chart** (horizontal).
2. **Y-axis:** `dim_local_authority[local_authority_name]`.
3. **X-axis:** `Sales`.
4. Sort descending: **More options (...) → Sort axis → Sales → Sort descending**.
5. Turn on data labels.

**Optional sixth visual:** a table or column chart of `Sales` by `dim_date[Year]`. It is useful because it reproduces the yearly checkpoint figures.

**Check:** clear all slicers and compare against the checkpoints below.

---

## 8. Phase 6 – Page 2 Data quality

Page question: *Which sales could be linked to EPC data, and does that bias the sample?* Switch to the `2 Data quality` page.

### 8.1 Measures for page 2
Create these in `_Measures` with **Display folder** `Data quality`.

1. **Matched Sales**: whole number.
   ```dax
   Matched Sales = CALCULATE ( [Sales], fact_sales[epc_matched] = TRUE () )
   ```
2. **Match Rate**: **Percentage**, **1 decimal place**.
   ```dax
   Match Rate = DIVIDE ( [Matched Sales], [Sales] )
   ```
3. **Median Price Matched**: **Currency**, £, 0 decimal places.
   ```dax
   Median Price Matched = CALCULATE ( [Median Price], fact_sales[epc_matched] = TRUE () )
   ```
4. **Median Price Unmatched**: **Currency**, £, 0 decimal places.
   ```dax
   Median Price Unmatched = CALCULATE ( [Median Price], fact_sales[epc_matched] = FALSE () )
   ```

`CALCULATE` evaluates its first argument after changing the filter context. Here the Boolean argument becomes a filter on `fact_sales[epc_matched]`, replacing any existing filter on that column. That is the "filter modification" you will describe in interviews.

### 8.2 Visuals for page 2
**Visual A: card, Match Rate**
1. Insert a **Card** and add `Match Rate`.

**Visual B: bar chart, Match Rate by local authority**
1. Insert a **Clustered bar chart**.
2. **Y-axis:** `dim_local_authority[local_authority_name]`.
3. **X-axis:** `Match Rate`.
4. Sort by `Match Rate` ascending or descending; turn on data labels with one decimal.
5. Title: `Match rate by local authority`.

**Visual C: bar chart, Match Rate by property type**
1. Insert a **Clustered bar chart**.
2. **Y-axis:** `dim_property_type[property_type_name]`.
3. **X-axis:** `Match Rate`.
4. Because of the sort-by-column setting in Phase 3, property types show in logical order.

**Visual D: clustered bar, Median Price Matched vs Unmatched by property type**
1. Insert a **Clustered bar chart** (or clustered column).
2. **Y-axis:** `dim_property_type[property_type_name]`.
3. **X-axis:** `Median Price Matched` and `Median Price Unmatched` (both in the same well).
4. Turn on data labels. Set the two series to the first two theme colours.
5. Title: `Median price: matched and unmatched sales`.

**Text box: the finding (one sentence)**
1. Insert a **Text box** beside the charts.
2. Write one sentence that states what the chart shows, using your own words and the figures you verified in the checkpoints. For example, the checkpoint figures show that Flat/Maisonette sales are far less likely to link (87.4%) than other types (95.2% to 97.8%), and that unmatched flats have a median of £300,000 against £200,000 for matched flats. A true sentence is something like: "Flats and maisonettes link least often, and the unmatched ones are priced higher, so a model trained only on matched sales under-represents expensive flats." Check that this still matches your own screen before keeping it, and **do not** copy a figure you have not seen on your own report.

---

## 9. Checkpoints – do your numbers match?

Clear **all slicers** (including date range) before checking. All figures come from the current export (256,638 sales). If you have re-run the export after new data, expect different figures.

### 9.1 Overall

| Item | Expected |
|---|---|
| Sales | 256,638 |
| Matched Sales | 243,320 |
| Match Rate | 94.8% |
| Median Price | £275,000 |
| Earliest sale date | 2 Jan 2020 |
| Latest sale date | 28 Aug 2026 |

To check the dates, create two temporary measures and show them in cards. Measures can read `sale_date` even after you hid it in Phase 3; delete them once checked.
```dax
First Sale = MIN ( fact_sales[sale_date] )
Last Sale = MAX ( fact_sales[sale_date] )
```

### 9.2 By local authority

| Local authority | Sales | Match Rate | Median Price |
|---|---|---|---|
| Camden | 13,132 | 80.2% | £790,000 |
| Cardiff | 30,500 | 96.3% | £255,000 |
| Cornwall | 60,575 | 93.6% | £280,000 |
| Leeds | 68,637 | 97.7% | £230,000 |
| Manchester | 34,957 | 92.8% | £240,000 |
| Milton Keynes | 27,025 | 97.4% | £340,000 |
| Trafford | 21,812 | 95.9% | £332,500 |

### 9.3 By property type

| Property type | Sales | Match Rate | Median Price Matched | Median Price Unmatched |
|---|---|---|---|---|
| Detached | 54,626 | 95.2% | £425,000 | £420,000 |
| Flat/Maisonette | 57,254 | 87.4% | £200,000 | £300,000 |
| Semi-detached | 74,247 | 97.8% | £275,000 | £265,000 |
| Terraced | 70,511 | 97.4% | £230,000 | £210,000 |

### 9.4 By year

| Year | Sales | Median Price |
|---|---|---|
| 2020 | 37,571 | £245,000 |
| 2021 | 51,182 | £263,500 |
| 2022 | 43,029 | £280,000 |
| 2023 | 34,519 | £280,000 |
| 2024 | 36,912 | £286,000 |
| 2025 | 37,314 | £290,000 |
| 2026 (to 28 Aug) | 16,111 | £285,000 |

Use a table visual with `dim_date[Year]`, `Sales` and `Median Price`.

### 9.5 Match status counts

| `match_status` | Count |
|---|---|
| matched | 243,320 |
| no_address_match | 9,697 |
| certificates_only_after_sale | 1,580 |
| ambiguous | 1,351 |
| no_epc_at_postcode | 690 |

These sum to 256,638. Use a table visual with `fact_sales[match_status]` and `Sales`. A sixth status, `no_postcode`, exists in the data model but does not appear in the export (see below).

### 9.6 Why `reports/match_quality.md` shows a slightly different total
`reports/match_quality.md` reports **256,677** sales because it includes **39 sales with no postcode**. Those cannot be given an area, so the export leaves them out (`WHERE s.postcode_district IS NOT NULL`). Small differences between the report and this model come from that, for example Terraced unmatched median £212,000 there against £210,000 here. Differences of this kind are expected and are not an error in your model.

### 9.7 If your numbers do not match
Check these in order:
1. **Slicers not cleared.** The most common cause. Clear every slicer and check that the filter pane on the page shows nothing.
2. **Wrong cardinality or direction.** In **Model view**, each relationship must be many-to-one with a single filter direction from the dimension. A one-to-one or bidirectional relationship will give odd totals.
3. **Inactive relationship (dotted line).** An inactive relationship does not filter. Double-click the line and tick **Make this relationship active**. If Power BI refuses because of ambiguity, you have created an extra relationship; delete it.
4. **Auto date/time still on.** Re-open **Options → Current File → Data Load** and untick it. Delete any hidden `LocalDateTable_...` tables if they exist (they appear in **Model view** only when the option is on).
5. **A column typed as text.** Return to Power Query and check the Phase 2 type checklist, especially `price` (must be Whole Number, or `MEDIAN` gives errors or odd results), `sale_date` (Date) and `epc_matched` (True/False).
6. **Wrong date table.** `dim_date` must be marked as a date table, and the relationship from `fact_sales[sale_date]` must exist.
7. **"File not found" or "could not find a part of the path" on refresh.** The parameter `DataFolder` must point at the data folder and end with a backslash, and the export (Phase 1) must have been run.

---

## 10. Phase 7 – Save and commit

1. Click **File → Save as**. Choose **Power BI project (.pbip)** as the file type. If the option is missing, return to Phase 0 and enable the preview feature, then restart.
2. Save into `D:\UK_Valuation_Reliability_Monitor\dashboards\power_bi\` with the name `UK_Valuation_Reliability_Monitor.pbip`.
3. Power BI creates these items next to each other:
   - `UK_Valuation_Reliability_Monitor.pbip`: the small project pointer file.
   - `UK_Valuation_Reliability_Monitor.Report/`: the report definition (pages and visuals).
   - `UK_Valuation_Reliability_Monitor.SemanticModel/`: the model definition (tables, relationships, measures, in TMDL if you enabled it).
4. After the first save, re-check **Options → Current File → Data Load → Auto date/time** (it should still be off) and re-check the `DataFolder` parameter.
5. `.gitignore` already excludes `.pbix` files, `dashboards/power_bi/data/**`, `**/.pbi/cache.abf` and `**/.pbi/localSettings.json`. The cache holds a copy of the data, so it must never be committed.
6. **Export evidence images.** Power BI Desktop has no built-in PNG export.
   - **Whole report:** **File → Export → Export to PDF** (the label may differ slightly between versions). Save it as `reports/power_bi_report.pdf`.
   - **Each page:** prepare the page, capture it and save the image.
     - Collapse the **Filters**, **Visualizations** and **Data** panes using the arrows on their headers.
     - Set **View → Page view → Fit to page** (the label may differ slightly between versions).
     - Capture the canvas with the Windows Snipping Tool (**Windows key + Shift + S**).

   Save the page images to `reports/figures/`:
   - `pbi_01_market_overview.png`
   - `pbi_02_data_quality.png`
   - `pbi_03_model_performance.png` (later)
   - `pbi_04_reliability_monitor.png` (later)

   Clear all slicers before capturing, so the images show the full data and agree with the checkpoints. Make sure no screenshot shows an address, a street name or a postcode-level value other than the district `LS6`.
7. Open PowerShell in the project folder and run:
   ```powershell
   git status
   ```
   Review the list carefully. You should see the `.pbip`, the `.Report` and `.SemanticModel` folders and the PNG files. You must **not** see any `.parquet` file, any `.pbix` file or any `cache.abf`. If one appears, stop and fix `.gitignore` before going further.
8. Stage and commit only what you reviewed, with an imperative-mood message:
   ```powershell
   git add dashboards/power_bi reports/figures
   git status
   git commit -m "Add Power BI pages 1 and 2: market overview and data quality"
   git push
   ```
9. Before pushing, run `gh auth status` and confirm the active account is `tanmay-kalokhe`. The other account must never push this repository.

---

## 11. Phase 8 – Page 3 Model performance (after Week 2)

> **Partly possible after Week 2.** The accuracy columns (`in_test_set`, `estimate_model`, `estimate_baseline`, `ape_model`, `ape_baseline`) arrive in Week 2: build the Model measures, Visual A and Visual C now. The coverage measures and Visual B need the price-range columns from Week 3. Re-run the export first (`py -3.12 -m valuation_monitor.exports`).

Page question: *Does the model beat the simple baseline, and are its ranges honest?*

### 11.1 Refresh
1. Re-run the export (Phase 1) and check that `fact_sales.parquet` now has the model columns.
2. In Power BI, click **Home → Refresh**.
3. In **Power Query** (**Home → Transform data**), set the new column types. Week 2: `in_test_set` True/False; `estimate_model`, `estimate_baseline` Whole Number; `ape_model`, `ape_baseline` Decimal Number. Week 3 adds: `covered` True/False; `range_lower`, `range_upper` Whole Number; `interval_width_pct`, `lower_ratio` Decimal Number; `decision` Text. Close & Apply.
4. Duplicate a template page and name it `3 Model performance`. Replace the title with the page question.

### 11.2 Measures
Create these in `_Measures`. Display folder `Model` for the first four, `Reliability` for the rest. Percentages with 1 decimal place.

```dax
Test Sales = CALCULATE ( [Sales], fact_sales[in_test_set] = TRUE () )
Model MdAPE = CALCULATE ( MEDIAN ( fact_sales[ape_model] ), fact_sales[in_test_set] = TRUE () )
Baseline MdAPE = CALCULATE ( MEDIAN ( fact_sales[ape_baseline] ), fact_sales[in_test_set] = TRUE () )
Improvement vs Baseline = DIVIDE ( [Baseline MdAPE] - [Model MdAPE], [Baseline MdAPE] )
```

```dax
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
```

Create `Areas on Alert` in Phase 9 (it needs `fact_monitoring`). Note that `Target Coverage` is a measure with a constant 0.90, formatted as a percentage.

### 11.3 Visuals
**Visual A: clustered bar, Model vs Baseline MdAPE by local authority**
1. Insert a **Clustered bar chart**.
2. **Y-axis:** `dim_local_authority[local_authority_name]`.
3. **X-axis:** `Model MdAPE` and `Baseline MdAPE`.
4. Format as percentage; data labels on; lower is better, so say so in the title: `Median absolute percentage error (lower is better)`.

**Visual B: bar chart, Coverage by local authority, with a 90% line**
1. Insert a **Clustered column chart**.
2. **X-axis:** `dim_local_authority[local_authority_name]`. **Y-axis:** `Coverage`.
3. Select the chart, open the **Analytics** pane (the magnifying-glass icon beside **Format**), expand **Constant line**, click **Add line**.
4. Click **fx** beside **Value** and choose **Field value**, then pick `Target Coverage`; or type `0.9`. Label the line `Target 90%`.
5. Use a dashed line and a visible colour. Set the Y-axis minimum to something like 0.7 only if you state the truncated axis in the title.

**Visual C: card, Improvement vs Baseline**
1. Insert a **Card** and add `Improvement vs Baseline` (percentage, 1 decimal place).

**Optional:** a card for `Test Sales`, so viewers see the sample size behind every figure.

Save, then export `pbi_03_model_performance.png` and commit (Phase 7 steps 6 to 8).

---

## 12. Phase 9 – Page 4 Reliability monitor (after Week 3)

> **Not yet possible.** `fact_monitoring` and the final model columns arrive in Week 3. Re-run the export first.

Page question: *Where and when can the valuations be trusted?*

### 12.1 Refresh and add `fact_monitoring`
1. Re-run the export (Phase 1). `fact_monitoring.parquet` should now be in `dashboards/power_bi/data/`.
2. In **Power Query**, add a new Parquet query exactly as in Phase 2:
   ```powerquery
   let
       Source = Parquet.Document(File.Contents(DataFolder & "fact_monitoring.parquet"))
   in
       Source
   ```
   Rename it `fact_monitoring`.
3. Set the types: `month_start` Date; `local_authority_code` Text; `test_sales` Whole Number; `coverage`, `coverage_ci_lower`, `coverage_ci_upper` and `mdape` Decimal Number; `alert` True/False; `alert_reason` Text.
4. Click **Close & Apply**, then **Home → Refresh**.
5. In **Model view** create the two relationships (many-to-one, single direction):

| From (many) | To (one) |
|---|---|
| `fact_monitoring[month_start]` | `dim_date[date]` |
| `fact_monitoring[local_authority_code]` | `dim_local_authority[local_authority_code]` |

6. Hide `fact_monitoring[month_start]` and `fact_monitoring[local_authority_code]`.
7. Create the measure `Areas on Alert` (folder `Reliability`):
   ```dax
   Areas on Alert =
   CALCULATE ( DISTINCTCOUNT ( fact_monitoring[local_authority_code] ), fact_monitoring[alert] = TRUE () )
   ```
8. Duplicate a template page and name it `4 Reliability monitor`.

### 12.2 The two what-if parameters
1. Click **Modeling → New parameter → Numeric range**. (In some versions it is **Modeling → What-if → New parameter**; the label may differ slightly between versions.)
2. Create the first parameter:
   - **Name:** `LTV`
   - **Data type:** Decimal number
   - **Minimum:** 0.50. **Maximum:** 0.95. **Increment:** 0.05. **Default:** 0.75.
   - Tick **Add slicer to this page**. Click **Create**.
3. Create the second parameter:
   - **Name:** `Stress Cap`
   - **Data type:** Decimal number
   - **Minimum:** 0.90. **Maximum:** 1.00. **Increment:** 0.01. **Default:** 1.00.
   - Tick **Add slicer to this page**. Click **Create**.
4. Power BI creates the tables `LTV` and `Stress Cap`, their slicers and the measures `LTV Value` and `Stress Cap Value`. Move those two measures to the `Reliability` display folder if you wish (they are in the new tables, so you may leave them).
5. Format the slicers as **Slider** (**Format → Slicer settings → Options → Style → Slider**, label may differ). Format the values as percentages.

### 12.3 The decision-rule measures
**What the rule means (decision D-013), in plain English.**
- The **loan** is the LTV multiplied by the estimated value: a 75% LTV loan on a £200,000 estimate is £150,000.
- The **stressed LTV** is that loan divided by the **lower end of the 90% price range**. It asks: if the property were worth only the pessimistic value, how big would the loan be relative to it?
- The valuation is **accepted** when the stressed LTV is **at or below the stress cap**. Otherwise it is **referred** to a surveyor.
- Algebraically, this is the same as saying: accept when `lower_ratio >= LTV / Stress Cap`, where `lower_ratio = range_lower / estimate_model`. This turns the decision into a comparison of one column with one number, which DAX can evaluate over any selection of sales.
- The effect: a 60% LTV loan tolerates a wide price range, whereas a 95% LTV loan needs a tight one.

Create these in `_Measures` (folder `Reliability`):

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

**Why the variable comes first (context transition).**
- **What the shorthand means:** a filter such as `fact_sales[lower_ratio] >= x` inside `CALCULATE` is short for `FILTER ( ALL ( fact_sales[lower_ratio] ), fact_sales[lower_ratio] >= x )`. That `FILTER` iterates over every distinct value of `lower_ratio`, each in its own row context.
- **Without the variable:** if `x` were the measure `[Min Lower Ratio]`, it would be evaluated once per value. Each evaluation triggers context transition: the row becomes a filter. This is slow, and it risks evaluating the slicer value in the wrong context. Some versions reject a measure in such a filter altogether.
- **With the variable:** `VAR MinRatio = [Min Lower Ratio]` is evaluated **once**, in the filter context the viewer chose, before `CALCULATE` runs. `CALCULATE` then compares each value with a fixed number.

This is a standard interview question on context transition. Format `Automation Rate`, `Accepted Coverage` and `Accepted MdAPE` as percentages with 1 decimal place.

**Caveat to state on the report:** the stress cap, its default (100%) and the LTV default (75%) are **illustrative design choices, not any lender's policy**. Add a small text box saying so on page 4.

### 12.4 Visuals for page 4
**Visual A: matrix, local authority by month, showing Coverage**
1. Insert a **Matrix**.
2. **Rows:** `dim_local_authority[local_authority_name]`. **Columns:** `dim_date[Year Month]`. **Values:** `Coverage`.
3. Format the **Values** as a percentage with 1 decimal place. Turn off row and column subtotals if they clutter the matrix.
4. Conditional formatting, using the status colours **and** icons (never colour alone):
   1. In **Format → Cell elements**, choose the series `Coverage`, then turn on **Background colour**; click **fx**.
   2. Set **Format style** to **Rules**. Add rules: `Coverage >= 0.90` is green `#0CA30C`; `Coverage >= 0.85 and < 0.90` is amber `#FAB219`; `Coverage < 0.85` is red `#D03B3B`. The 0.85 boundary is the provisional alert threshold in `config/project_config.yaml` (`monitoring.coverage_alert_below`); if it changes in Week 3, change the rule to match, and state it in the legend text. Match the text colour for contrast.
   3. Turn on **Icons** in the same **Cell elements** section and set rules with different shapes (for example a tick, a warning triangle and a cross), so the status is readable without colour.
5. Note on the measure: the matrix uses the `Coverage` measure from `fact_sales`. `fact_monitoring` also has its own `coverage` column computed in Python with confidence intervals. Keep the two consistent: if they disagree, investigate which filter is in play before publishing.

**Visual B: table, alerts with their reasons**
1. Insert a **Table**.
2. **Columns:** `dim_local_authority[local_authority_name]`, `fact_monitoring[month_start]`, `fact_monitoring[test_sales]`, `fact_monitoring[alert_reason]`.
3. Add a visual-level filter: `fact_monitoring[alert]` is **True**.
4. Turn off the summarisation for `test_sales` if you want a row-level view, using **Don't summarize**.

**Visual C: cards for the decision rule**
1. Insert three **Cards**: `Automation Rate`, `Accepted Coverage`, `Accepted MdAPE`.
2. Insert a fourth card: `Areas on Alert`.

**Visual D: line chart, trade-off across LTV values**
1. Insert a **Line chart**.
2. **X-axis:** `LTV[LTV]` (the parameter's column).
3. **Y-axis:** `Automation Rate` and `Accepted Coverage`.
4. Each point on the x-axis evaluates the measures at that LTV, which shows automation falling as LTV rises.
5. Add a constant line at 90% (**Analytics → Constant line**), as on page 3, so viewers can see where accepted coverage sits against the target.

6. **Stop the LTV slider filtering this chart.** Otherwise the slider's single value filters the chart's x-axis, and the line collapses to one point.
   - Select the LTV slicer, then **Format → Edit interactions**.
   - On the line chart, click the **None** icon.
   - The cards still follow the slider, while the chart shows every LTV.
7. **Check:** each point on the line should differ, and the cards should change when you move the slider. If every point is identical, check that the measure `LTV Value` is the one Power BI created (it uses `SELECTEDVALUE` on `LTV[LTV]`) and that you did not replace it.

**Visual E: map of alerts by local authority (Shape map)**
1. Use the **Shape map** visual, which needs a custom TopoJSON of ONS local-authority boundaries. That file is prepared in **Week 4**, so leave this visual until then.
2. When ready: click the visual, then **Format → Map settings → Add map** (the label may differ slightly between versions) and load the TopoJSON. Put the local-authority name in **Location** and `Areas on Alert` in **Colour saturation**.
3. Shape map avoids the Bing and Azure Maps sign-in settings. It is a preview or default visual depending on version; if the **Shape map** icon is absent, enable it under **File → Options and settings → Options → Preview features** (the name may differ slightly between versions).

Save, export `pbi_04_reliability_monitor.png` and commit with a message such as "Add Power BI pages 3 and 4: model performance and reliability monitor".

---

## 13. Optional extras that show depth

### Drill-through: local authority to postcode districts
1. Insert a new page named `Detail: postcode districts`.
2. Add `dim_area[postcode_district]` and `Sales` and `Match Rate` to a table.
3. In **Visualizations → Build visual → Drill through**, drag `dim_local_authority[local_authority_name]` into **Add drill-through fields here**.
4. Power BI adds a back button automatically. Right-click a local authority on any other page and choose **Drill through → Detail: postcode districts**.
5. Do not show any street or address text; district level (for example `LS6`) is the finest level.

### Report-page tooltip on the matrix
1. Add a page named `Tooltip: coverage`. In **Format → Page information**, tick **Allow use as tooltip**. Under **Format → Canvas settings**, set **Type** to **Tooltip**.
2. Add small visuals, for example `Test Sales`, `Coverage` and `Median Interval Width %` as cards.
3. On the matrix, open **Format → General → Tooltips**, set **Type** to **Report page** and choose the tooltip page.

### Bookmark panel: "About this report"
1. Add a rectangle and a text box on a page explaining the data sources, the match rate and the caveat that the stress cap is illustrative. Group them (**Format → Group**).
2. Open **View → Bookmarks** and **Selection pane**. Create a bookmark `About hidden` with the group hidden, and `About shown` with it visible.
3. Insert two buttons (**Insert → Buttons → Information** and **Back**) and set each button's **Action → Type → Bookmark** to the relevant bookmark.

---

## 14. What to say about it (interview notes)

Use these only after you have built each item. Do not claim anything you have not done.

- **Power Query typing and parameters.** You loaded Parquet through a `DataFolder` parameter and set explicit types, so the model refreshes reproducibly and does not rely on guessed types. You can explain why `sale_date` is a Date and not Date/Time.
- **Star schema with a snowflaked dimension.** `fact_sales` connects to `dim_date`, `dim_property_type` and `dim_area`, and `dim_area` connects to `dim_local_authority`. You can explain why `area_key` combines authority code and district, and why filters flow one way.
- **DAX date table and time intelligence.** You built `dim_date` in DAX, marked it, turned off Auto date/time, and used `DATEADD` for year-on-year change. You can explain why that measure goes blank without date context.
- **`CALCULATE` and filter modification.** Matched, unmatched and test-set measures all use `CALCULATE` with Boolean filters. You can explain how it replaces filters on a column.
- **What-if parameters with variables.** The LTV and Stress Cap sliders drive an accept-or-refer rule. You can explain the variable-before-`CALCULATE` pattern (context transition) and why the algebra reduces the rule to one column.
- **Conditional formatting and accessibility.** The matrix uses status colours plus icons, and the theme palette was checked for colour-blind viewers. You can explain why colour alone is not enough.
- **Honest reporting.** The data-quality page shows that unmatched sales are not a random sample, and page 4 states that the stress cap is illustrative.

**Sample CV bullet (template; fill only with true figures once built):**

> Built a four-page Power BI report (Power Query, star schema, [N] DAX measures, [N] what-if parameters) on [N] linked UK property sales, showing [true finding, for example match rate by property type] and monthly valuation reliability by local authority for a lender's valuation team.

Replace each `[N]` with the real number you counted in your finished report, and delete anything you did not build.

---

## 15. Progress checklist

Tick each item as you complete it.

- [ ] Phase 0: Power BI Desktop installed
- [ ] Phase 0: Power BI Project (.pbip) preview option enabled (and TMDL option, if listed)
- [ ] Phase 0: Auto date/time turned off for the current file
- [ ] Phase 0: Regional settings set to English (United Kingdom)
- [ ] Phase 1: Export run with `py -3.12 -m valuation_monitor.exports`
- [ ] Phase 1: Four Parquet files present in `dashboards/power_bi/data/`
- [ ] Phase 2: `DataFolder` parameter created
- [ ] Phase 2: Four Parquet queries created and renamed
- [ ] Phase 2: Column types set and checked
- [ ] Phase 2: Close & Apply completed
- [ ] Phase 3: `dim_date` built, sorted and marked as date table
- [ ] Phase 3: Four relationships created and checked
- [ ] Phase 3: Key columns hidden and `property_type_name` sorted by `sort_order`
- [ ] Phase 3: `_Measures` table created with hidden dummy column
- [ ] Phase 4: Theme imported
- [ ] Phase 4: Page template built with three slicers and synced
- [ ] Phase 5: Page 1 measures created (`Sales`, `Median Price`, `Median Price YoY %`)
- [ ] Phase 5: Page 1 visuals built
- [ ] Phase 6: Page 2 measures created (four)
- [ ] Phase 6: Page 2 visuals and finding text box built
- [ ] Checkpoints: overall, local authority, property type, year and match status figures all match
- [ ] Phase 7: Saved as `UK_Valuation_Reliability_Monitor.pbip` in `dashboards/power_bi/`
- [ ] Phase 7: `git status` reviewed; no Parquet, `.pbix` or `cache.abf` listed
- [ ] Phase 7: `pbi_01_market_overview.png` and `pbi_02_data_quality.png` saved to `reports/figures/`
- [ ] Phase 7: Committed and pushed (`gh auth status` checked)
- [ ] Phase 8 (after Week 2): export re-run, columns typed, refreshed
- [ ] Phase 8: Page 3 measures created
- [ ] Phase 8: Page 3 visuals built, including the 90% constant line
- [ ] Phase 8: `pbi_03_model_performance.png` saved; committed
- [ ] Phase 9 (after Week 3): `fact_monitoring` loaded with two relationships
- [ ] Phase 9: `LTV` and `Stress Cap` parameters created
- [ ] Phase 9: Decision-rule measures created
- [ ] Phase 9: Matrix with colour and icon conditional formatting built
- [ ] Phase 9: Alerts table, cards and LTV line chart built
- [ ] Phase 9: Illustrative-caveat text box added
- [ ] Phase 9 (Week 4): Shape map added with custom TopoJSON
- [ ] Phase 9: `pbi_04_reliability_monitor.png` saved; committed
- [ ] Optional: drill-through page
- [ ] Optional: report-page tooltip
- [ ] Optional: "About this report" bookmark panel
- [ ] Interview notes read; CV bullet filled with true figures only
