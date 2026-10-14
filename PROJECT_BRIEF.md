# Project brief: UK Valuation Reliability Monitor
_Tanmay Kalokhe · prepared 14 October 2026 · status: setup complete, build not started_

## 1. What the project is
A property-valuation system for England and Wales that answers three questions about any home, rather than returning a single predicted price:

1. **What is the estimated value?**
2. **How uncertain is that estimate?** The answer is a calibrated price range, for example "£212,000 to £248,000, which should contain the true price 9 times in 10".
3. **Can the estimate be trusted in this area right now?** A reliability indicator, driven by monthly monitoring, recommends either accepting the automated valuation or referring the property to a surveyor.

**Intended user:** a mortgage lender's valuation team. **Study area:** seven contrasting local authorities (Manchester, Trafford, Leeds, Milton Keynes, Camden, Cornwall and Cardiff).

It is built on public data: HM Land Registry **Price Paid Data** (every residential sale), linked to **Energy Performance Certificate** records (floor area, energy rating, property age), with the **UK House Price Index** for the baseline.

## 2. The problem it focuses on
UK lenders and property businesses use **automated valuation models** to value homes without a site visit, and accept them only when confidence is high enough. Three practical problems sit behind that decision:

- **A single price hides risk.** A point estimate gives no basis for deciding when to rely on it.
- **Average accuracy hides local failure.** A model can look accurate nationally while performing badly in particular areas or property types.
- **Markets move.** A model trained last year can drift as prices, the mix of properties sold and the data itself change. Without monitoring, nobody notices until valuations are wrong.

There is also a data problem underneath: the Land Registry and EPC datasets share **no common property identifier**. Linking them is a record-linkage task, and the records that fail to link are not a random sample.

## 3. How it solves it

| Stage | What happens | Why it matters |
|---|---|---|
| **Data linkage (SQL)** | Sales are matched to EPC certificates in DuckDB SQL, using the latest certificate lodged before each sale. Unmatched records are reported and compared with matched ones. | It avoids leaking post-sale information, and it makes bias from missing data visible rather than hidden. |
| **Matching comparison** | The SQL rules are compared with **Splink**, the UK Ministry of Justice's open-source probabilistic record-linkage library, judged on 300 hand-checked pairs. | It shows two professional approaches and measures their precision and recall rather than assuming one is better. |
| **Modelling** | A simple baseline (district median adjusted by the House Price Index) is compared with LightGBM and CatBoost. | A machine-learning model has to beat a simple industry method to justify itself. |
| **Uncertainty** | Conformal prediction produces price ranges with a stated coverage target (90%), checked by area, property type and month. | It gives honest ranges that can be tested, not just a confidence label. |
| **Validation** | Time-based holdouts ("does it still work next month?") and local-authority holdouts ("does it work in an unseen area?"), with bootstrap confidence intervals. | It reflects real use rather than an optimistic random split. |
| **Monitoring** | Past monthly releases are replayed in order. Error, coverage and data changes are tracked per area, and a retraining recommendation fires only when there are enough sales to be confident it is a real problem. | It shows the model being run as a living system, not a one-off notebook. |
| **Reporting** | A four-page Power BI report (market, data quality, model performance, reliability), built by hand with Power Query, a star schema and DAX, including a what-if threshold. | It closes the Power BI gap honestly and speaks to analyst and BI audiences. |
| **Maps** | Maps of alerts by local authority and of error and coverage by small area (MSOA), in both Power BI and Streamlit, using open ONS boundaries. | Shows where a model fails at a glance; geospatial skills are valued in public-sector and property roles. |
| **Decision and demo** | A publicly hosted Streamlit app shows the value, the range, the main contributing factors and an accept-or-refer indicator. It also reports the trade-off between how many valuations are automated and how reliable they are. | It turns technical results into a business decision a non-specialist can act on. |

**Data ethics:** the public repository and demo contain no address-level data, because of the reuse terms attached to the Price Paid address fields and EPC records. Only code, aggregated results and charts are published.

## 4. Relevance to the current job market
A review of about 36 UK entry-level adverts in October 2026 (details in `D:\Job Applications\Portfolio_Project_Plan.md`) found:

- **SQL** in all six Data Scientist adverts reviewed, and in 9 of 11 Data Analyst adverts. This is the largest gap on the current CV, and this project closes it with substantial, non-trivial SQL.
- **Python, statistics and machine learning** in every Data Scientist advert.
- **Evaluation and reliability** of models or outputs named in most AI Engineer adverts, and **golden datasets and regression testing** in senior evaluation roles.
- **Data quality and governance** in analyst and consultancy adverts.

| Target role | Fit | What the project demonstrates |
|---|---|---|
| Junior Data Scientist | **Strong** | SQL, feature engineering, gradient boosting, uncertainty quantification, sound validation |
| AI / model evaluation | **Strong** | Calibration, coverage testing, honest reporting of where a model fails, monitoring thresholds |
| Data Analyst (fallback) | **Strong** | SQL, data quality reporting, a Power BI report with DAX measures (Power BI appeared in about half the analyst adverts reviewed) |
| ML Engineer | **Moderate** | Monitoring, drift detection, retraining triggers, a reproducible pipeline |
| Graduate consultancy (e.g. Capgemini Insights & Data) | **Strong** | A client-style deliverable: requirement, evaluation, risk and data governance |
| Computer vision engineer | **Low** | Not covered; the document-AI and sports projects in the portfolio plan address this |

**Relevant employer types:** lenders and building societies (valuation and credit-risk teams), property platforms and valuation-data providers, insurers, consultancies, and public bodies that value or report on property (for example HM Land Registry, the Valuation Office Agency and the Office for National Statistics).

## 5. How it benefits Tanmay

**In applications**
- It replaces the weakest projects on the CV with one that uses SQL, statistics and machine learning on a real UK business problem.
- It extends the precision-first, evaluation-led approach from the Cranmore placement to a new domain. This shows a consistent professional strength rather than a one-off.
- It provides interview material beyond accuracy scores: why a random split would mislead, why unmatched records matter, how the alert threshold avoids false alarms, and what the accept-or-refer trade-off costs.
- Its results can be quoted in cover letters once they exist. The tracker's cover-letter generator will cite them automatically after they are added to the CV.

**For freelance work (realistic scope)**
- **Transferable services:** record linkage and data cleaning across messy datasets, building model monitoring for an existing model, and uncertainty and validation reviews of a client's model. These skills are not specific to property.
- **Property-specific:** local market analysis for small estate agencies, investors or housing associations, using aggregated public statistics.
- **Licence caution:** commercial work must respect the data terms. Price Paid address fields and EPC records carry reuse restrictions, so freelance deliverables should be built on the methods and on the client's own or properly licensed data, not on redistributed address-level public data.
- A finished, well-documented repository serves as a portfolio sample when bidding for such work.

## 6. Plan and success criteria
Four weeks, as set out in `README.md` (three for the core, plus one for the Splink comparison and maps). The project counts as finished when:
- the match rate and any match bias are reported;
- the model is compared honestly with the baseline on both holdouts;
- interval coverage is reported by area, with confidence intervals;
- the monthly replay shows at least one alert decision and explains it;
- the dashboard runs with one command;
- the README states the results, including limitations.

**Rule:** add the project to the CV and LinkedIn only once these results exist, using the real figures.
