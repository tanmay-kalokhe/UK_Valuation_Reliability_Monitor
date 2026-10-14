"""Match-quality report: how many sales were linked to an EPC, and is the linked set biased?

Writes reports/match_quality.md (aggregated figures only, no addresses) and two charts in
reports/figures/. Run after the matching stage:
    python -m valuation_monitor.matching
"""

from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from valuation_monitor.config import PROJECT_ROOT  # noqa: E402
from valuation_monitor.db import connect  # noqa: E402

BLUE, ORANGE = "#2A78D6", "#EB6834"  # colour-blind-checked palette (dashboards theme)
INK, MUTED = "#13212A", "#4B5B64"

STATUS_TEXT = {
    "matched": "Linked to a certificate lodged on or before the sale",
    "no_address_match": "Certificates exist at the postcode, but none for this address",
    "certificates_only_after_sale": "The property's certificates were all lodged after the sale",
    "ambiguous": "Two or more properties tied at the best rule, so left unmatched",
    "no_epc_at_postcode": "No certificate at all at the sale's postcode",
    "no_postcode": "The sale has no postcode",
}
TIER_TEXT = {
    1: "Exact address",
    2: "Same house/flat numbers and street",
    3: "Named house, similar name",
    4: "Named house, certificate adds the hamlet",
}
TYPE_NAMES = {"D": "Detached", "S": "Semi-detached", "T": "Terraced", "F": "Flat/maisonette"}


def _table(headers: list[str], rows: list[tuple], align: str | None = None) -> str:
    align = align or "l" + "r" * (len(headers) - 1)
    rule = ["---:" if a == "r" else "---" for a in align]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(rule) + " |"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def _pct(x: float) -> str:
    return f"{x:.1%}"


def _gbp(x: float) -> str:
    return f"£{x:,.0f}"


def collect(con) -> dict:
    """Run every aggregate query the report needs."""
    q = lambda sql: con.execute(sql).fetchall()  # noqa: E731
    base = """
        FROM match_outcome AS o
        INNER JOIN match_sales AS s ON o.transaction_id = s.transaction_id
        INNER JOIN study_area AS a ON s.lad_code = a.lad_code
    """
    rate = "avg((o.match_status = 'matched')::INT)"
    return {
        "total": q(
            "SELECT count(*), count(*) FILTER (WHERE match_status = 'matched') FROM match_outcome"
        )[0],
        "status": q("SELECT match_status, count(*) FROM match_outcome GROUP BY 1 ORDER BY 2 DESC"),
        "tier": q(
            "SELECT match_tier, count(*) FROM match_outcome "
            "WHERE match_status = 'matched' GROUP BY 1 ORDER BY 1"
        ),
        "by_area": q(f"SELECT a.lad_name, count(*), {rate} {base} GROUP BY 1 ORDER BY 3"),
        "by_type": q(f"SELECT s.property_type, count(*), {rate} {base} GROUP BY 1 ORDER BY 1"),
        "by_new": q(f"SELECT s.is_new_build, count(*), {rate} {base} GROUP BY 1 ORDER BY 1"),
        "by_tenure": q(f"SELECT s.tenure, count(*), {rate} {base} GROUP BY 1 ORDER BY 1"),
        "by_year": q(f"SELECT year(s.sale_date), count(*), {rate} {base} GROUP BY 1 ORDER BY 1"),
        "price_bias": q(f"""
            SELECT s.property_type,
                   median(s.price) FILTER (WHERE o.match_status = 'matched'),
                   median(s.price) FILTER (WHERE o.match_status <> 'matched'),
                   count(*) FILTER (WHERE o.match_status <> 'matched')
            {base} GROUP BY 1 ORDER BY 1"""),
        "age": q("""
            SELECT median(days_before_sale),
                   avg((days_before_sale <= 365)::INT),
                   avg((days_before_sale > 3650)::INT)
            FROM match_outcome WHERE match_status = 'matched'""")[0],
        "type_check": q("""
            SELECT
                avg(CASE
                    WHEN s.property_type = 'F' THEN e.epc_property_type IN ('Flat', 'Maisonette')
                    ELSE e.epc_property_type IN ('House', 'Bungalow', 'Park home')
                END::INT),
                count(*)
            FROM match_outcome AS o
            INNER JOIN match_sales AS s ON o.transaction_id = s.transaction_id
            INNER JOIN match_epc AS e ON o.certificate_number = e.certificate_number
            WHERE o.match_status = 'matched'""")[0],
        "type_check_by_tier": q("""
            SELECT o.match_tier,
                avg(CASE
                    WHEN s.property_type = 'F' THEN e.epc_property_type IN ('Flat', 'Maisonette')
                    ELSE e.epc_property_type IN ('House', 'Bungalow', 'Park home')
                END::INT)
            FROM match_outcome AS o
            INNER JOIN match_sales AS s ON o.transaction_id = s.transaction_id
            INNER JOIN match_epc AS e ON o.certificate_number = e.certificate_number
            WHERE o.match_status = 'matched' GROUP BY 1 ORDER BY 1"""),
        "lookup_check": q("""
            SELECT avg((l.lad_code = p.lad_code)::INT), count(*) FILTER (WHERE l.lad_code IS NULL)
            FROM stg_price_paid AS p
            LEFT JOIN stg_postcode_lookup AS l ON p.postcode_key = l.postcode_key""")[0],
        "revisions": q(
            "SELECT record_status, count(*) FROM stg_price_paid_changes GROUP BY 1 ORDER BY 1"
        ),
        "categories": q("SELECT ppd_category, count(*) FROM stg_price_paid GROUP BY 1 ORDER BY 1"),
    }


def _charts(m: dict, figures) -> list[str]:
    figures.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})

    # Figure 1: match rate by local authority (single series, labelled bars)
    names = [r[0] for r in m["by_area"]]
    rates = [r[2] for r in m["by_area"]]
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    bars = ax.barh(names, rates, color=BLUE, height=0.6)
    for bar, value in zip(bars, rates, strict=True):
        ax.text(
            value + 0.004, bar.get_y() + bar.get_height() / 2, _pct(value), va="center", color=INK
        )
    lowest = min(rates)
    ax.set_xlim(max(0, lowest - 0.08), 1.0)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("Share of Category A sales linked to an EPC", color=MUTED)
    ax.set_title("EPC match rate by local authority, sales 2020 to Aug 2026", loc="left", color=INK)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=MUTED)
    fig.tight_layout()
    first = "01_match_rate_by_area.png"
    fig.savefig(figures / first, dpi=160)
    plt.close(fig)

    # Figure 2: median price of matched vs unmatched sales by property type
    rows = [r for r in m["price_bias"] if r[0] in TYPE_NAMES]
    labels = [TYPE_NAMES[r[0]] for r in rows]
    x = range(len(rows))
    width = 0.38
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    ax.bar([i - width / 2 for i in x], [r[1] for r in rows], width, color=BLUE, label="Matched")
    ax.bar([i + width / 2 for i in x], [r[2] for r in rows], width, color=ORANGE, label="Unmatched")
    ax.set_xticks(list(x), labels)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"£{v / 1000:.0f}k"))
    ax.set_title("Median sale price: matched vs unmatched sales", loc="left", color=INK)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=MUTED)
    fig.tight_layout()
    second = "02_matched_vs_unmatched_price.png"
    fig.savefig(figures / second, dpi=160)
    plt.close(fig)
    return [first, second]


def render(m: dict, charts: list[str]) -> str:
    total, matched = m["total"]
    type_ok, type_n = m["type_check"]
    lookup_agree, no_lookup = m["lookup_check"]
    median_days, within_year, over_ten = m["age"]
    tier_consistency = dict(m["type_check_by_tier"])
    low_area, _, low_rate = m["by_area"][0]
    flat_rate = next(r for t, _, r in m["by_type"] if t == "F")
    _, flat_matched, flat_unmatched, _ = next(r for r in m["price_bias"] if r[0] == "F")
    parts = [
        "# Match quality: Land Registry sales to EPC certificates",
        "",
        f"_Generated {date.today():%d %B %Y} by `python -m valuation_monitor.matching`. "
        "Aggregated figures only; no addresses. Data snapshot: decision D-015._",
        "",
        "## Headline",
        f"- **{matched:,} of {total:,}** Category A sales (2020 to 28 Aug 2026) were linked to "
        f"an EPC certificate lodged on or before the sale: **{_pct(matched / total)}**.",
        f"- Property-type consistency check: in **{_pct(type_ok)}** of {type_n:,} links, Land "
        "Registry and the EPC agree on whether the home is a flat. This is a proxy for false "
        "matches; precision is measured properly in Week 2 on 300 hand-checked pairs.",
        f"- The linked certificate was lodged a median of **{median_days:,.0f} days** before the "
        f"sale; {_pct(within_year)} within a year and {_pct(over_ten)} more than ten years "
        "earlier. Older certificates may not reflect later extensions or refurbishment.",
        "",
        "## Outcome of every sale",
        _table(
            ["Status", "Sales", "Share", "Meaning"],
            [(f"`{s}`", f"{n:,}", _pct(n / total), STATUS_TEXT[s]) for s, n in m["status"]],
            "lrrl",
        ),
        "",
        "## Matched sales by rule tier",
        _table(
            ["Tier", "Rule", "Sales", "Share of matched", "Type consistency"],
            [
                (t, TIER_TEXT[t], f"{n:,}", _pct(n / matched), _pct(tier_consistency[t]))
                for t, n in m["tier"]
            ],
            "llrrr",
        ),
        "",
        "## Is the matched set biased?",
        f"- **Lowest match rate: {low_area} ({_pct(low_rate)})**, against "
        f"{_pct(matched / total)} overall. Flats match least often ({_pct(flat_rate)}).",
        f"- **Unmatched flats are worth more:** median {_gbp(flat_unmatched)} against "
        f"{_gbp(flat_matched)} for matched flats. The model will therefore see fewer "
        "high-value flats than the market contains, so its accuracy on them must be reported "
        "separately rather than assumed.",
        "- For houses the matched and unmatched medians are close, so exclusion bias there is "
        "small.",
        "",
        f"![Match rate by local authority](figures/{charts[0]})",
        "",
        _table(
            ["Local authority", "Sales", "Match rate"],
            [(a, f"{n:,}", _pct(r)) for a, n, r in m["by_area"]],
        ),
        "",
        _table(
            ["Property type", "Sales", "Match rate"],
            [(TYPE_NAMES.get(t, t), f"{n:,}", _pct(r)) for t, n, r in m["by_type"]],
        ),
        "",
        _table(
            ["New build", "Sales", "Match rate"],
            [("Yes" if b else "No", f"{n:,}", _pct(r)) for b, n, r in m["by_new"]],
        ),
        "",
        _table(
            ["Tenure", "Sales", "Match rate"],
            [
                ({"F": "Freehold", "L": "Leasehold"}.get(t, t), f"{n:,}", _pct(r))
                for t, n, r in m["by_tenure"]
            ],
        ),
        "",
        _table(
            ["Sale year", "Sales", "Match rate"],
            [(y, f"{n:,}", _pct(r)) for y, n, r in m["by_year"]],
        ),
        "",
        f"![Matched vs unmatched median price](figures/{charts[1]})",
        "",
        _table(
            ["Property type", "Median price, matched", "Median price, unmatched", "Unmatched"],
            [
                (TYPE_NAMES.get(t, t), _gbp(a), _gbp(b) if b else "–", f"{n:,}")
                for t, a, b, n in m["price_bias"]
            ],
        ),
        "",
        "## Other data checks",
        f"- Land Registry's district field agrees with the ONS postcode lookup for "
        f"{_pct(lookup_agree)} of study-area sales; {no_lookup:,} sales have no postcode in the "
        "lookup (most have no postcode at all).",
        "- Price Paid categories in the study area: "
        + ", ".join(f"{c} = {n:,}" for c, n in m["categories"])
        + ". Only Category A is modelled (decision D-002).",
        "- Revisions in the latest monthly update for the study area: "
        + ", ".join(f"{s} = {n:,}" for s, n in m["revisions"])
        + " (A added, C changed, D deleted).",
        "",
        "## Limitations and next steps",
        "- Thresholds (Jaro-Winkler 0.85 and 0.92) and tier 4 are first choices. Week 2 measures "
        "precision and recall on 300 hand-checked pairs and compares the rules with Splink.",
        "- Ambiguous ties are left unmatched on purpose: a wrong certificate would give the "
        "model wrong floor areas, which is worse than a missing one.",
        "- Unmatched sales are excluded from modelling. The tables above show where that "
        "exclusion falls, so its effect on the results can be discussed.",
        "",
    ]
    return "\n".join(parts)


def write_match_report(config: dict) -> None:
    reports = PROJECT_ROOT / "reports"
    with connect(config, read_only=True) as con:
        metrics = collect(con)
    charts = _charts(metrics, reports / "figures")
    (reports / "match_quality.md").write_text(
        render(metrics, charts), encoding="utf-8", newline="\n"
    )
    print("  wrote reports/match_quality.md and", ", ".join(charts))
