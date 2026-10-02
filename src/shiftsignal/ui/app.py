"""Shift Signal's standalone Streamlit workspace."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from shiftsignal import __version__
from shiftsignal.analysis import DataProblem, Launch, analyze_launch, plan_launch, sensitivity_grid
from shiftsignal.examples import historical_demo, portfolio_demo
from shiftsignal.io import csv_bytes, evidence_pack, read_csv
from shiftsignal.research import LIMITS, SOURCES
from shiftsignal.ui import signal_theme as sig

NS = "shift"
CONTEXTS = ["Restaurant menu", "Product portfolio"]
BLUE = "#4f80a2"
RUST = "#b2622d"
GREEN = "#728157"


def k(name: str) -> str:
    return f"{NS}:{name}"


def money(value: float, currency: str) -> str:
    return f"{value:,.0f} {currency}"


def chart(fig, key: str, height: int = 380) -> None:
    fig.update_layout(height=height, margin=dict(l=15, r=20, t=35, b=25),
                      legend=dict(orientation="h", y=1.12, x=0), hovermode="closest")
    st.plotly_chart(fig, use_container_width=True, key=k(key), config={"displaylogo": False})


def table(frame: pd.DataFrame, **kwargs) -> None:
    st.dataframe(frame, use_container_width=True, hide_index=True, **kwargs)


def overview() -> None:
    sig.hero(NS, eyebrow="MENU & PRODUCT CANNIBALIZATION",
             title="New sales. But how much", em="new business?",
             body="See where a launch gets its volume, which existing items give it up, and whether the whole "
                  "menu or portfolio earns more. Plan a launch, then compare the result against unaffected locations.",
             pills=["Menu substitution", "Product launches", "Portfolio contribution", "Research grounded"])
    sig.cards([
        ("01 / PLAN", "Where will the sales come from?",
         "Set launch volume and switching assumptions. Follow displaced units through your existing items and margins."),
        ("02 / MEASURE", "Did the portfolio actually grow?",
         "Compare test and control locations before and after one launch. Inspect uncertainty and pre-launch patterns."),
        ("03 / DECIDE", "Does the margin justify the move?",
         "Compare incremental contribution after launch cost. Stress-test volume and cannibalization before committing."),
    ])
    st.subheader("A launch can sell well while adding little")
    context = st.radio("Explore a fictional example", CONTEXTS, horizontal=True, key=k("overview_context"))
    portfolio, launch = portfolio_demo(context)
    result = plan_launch(portfolio, launch)["summary"]
    st.caption(f"FICTIONAL DEMO · {launch.name} · one four-week planning period · NOK")
    a, b, c, d = st.columns(4)
    a.metric("New-item sales", f"{result['new_item_units']:,.0f} units")
    b.metric("Moved from own items", f"{result['displaced_units']:,.0f} units")
    c.metric("Additional portfolio units", f"{result['incremental_units']:,.0f}")
    d.metric("Incremental contribution", money(result["incremental_contribution"], "NOK"))
    sig.note("info", "**Feasible, with the right evidence.** The planner is useful before launch as an explicit "
             "what-if. Measuring cannibalization needs comparable units, a credible counterfactual and clean availability data.")
    left, right = st.columns(2)
    with left:
        st.markdown("**For restaurant menus**\n\nCompare substitutes within a meal occasion, such as mains. "
                    "Include food cost and variable preparation cost. A burger and a side can be complements.")
    with right:
        st.markdown("**For product portfolios**\n\nCompare equivalent packs or usage units. Include variable "
                    "manufacturing, fulfillment and channel costs. Own sales alone cannot identify competitor switching.")
    st.caption("Choose Launch planner or Launch evidence in the sidebar. Both open with complete fictional examples.")


def _planner_inputs():
    context = st.radio("Planning context", CONTEXTS, horizontal=True, key=k("planner_context"))
    original, default = portfolio_demo(context)
    with st.expander("Use your own portfolio", expanded=False):
        st.write("Upload one row per incumbent item: item, units, price, unit_cost, overlap. "
                 "Keep all unit volumes in the same planning period. You can edit the table below directly.")
        upload = st.file_uploader("Portfolio CSV", type=["csv"], key=k("portfolio_upload"))
        st.download_button("Download portfolio template", csv_bytes(original), "shift-portfolio-template.csv", "text/csv",
                           key=k("portfolio_template"))
    source = "Editable scenario initialized from a fictional demo"
    digest = context
    if upload is not None:
        original = read_csv(upload.getvalue())
        source = f"Uploaded portfolio: {upload.name} (including any table edits)"
        digest += hashlib.sha256(upload.getvalue()).hexdigest()[:12]
    st.caption(source)
    st.markdown("**Existing items** · overlap is your relative substitution weight: 0 excludes an item; "
                "1 gives it the strongest weight. Allocation also accounts for current volume.")
    edited = st.data_editor(original, num_rows="dynamic", use_container_width=True, hide_index=True,
                            key=k(f"portfolio_editor:{digest}"), column_config={
        "item": st.column_config.TextColumn("Item", required=True),
        "units": st.column_config.NumberColumn("Baseline units", min_value=0.0, required=True),
        "price": st.column_config.NumberColumn("Price / unit", min_value=0.0, required=True),
        "unit_cost": st.column_config.NumberColumn("Variable cost / unit", min_value=0.0, required=True),
        "overlap": st.column_config.NumberColumn("Overlap weight", min_value=0.0, max_value=1.0, step=0.05, required=True),
    })
    st.subheader("The proposed launch")
    left, middle, right = st.columns(3)
    suffix = context
    with left:
        name = st.text_input("New item name", default.name, key=k(f"name:{suffix}"), max_chars=100)
        units = st.number_input("Expected launch units", 0.0, 1e9, float(default.units), step=50.0, key=k(f"units:{suffix}"))
    with middle:
        price = st.number_input("New item price", 0.0, 1e9, float(default.price), key=k(f"price:{suffix}"))
        cost = st.number_input("New item variable cost", 0.0, 1e9, float(default.unit_cost), key=k(f"cost:{suffix}"))
    with right:
        fixed = st.number_input("Total incremental launch cost", 0.0, 1e12, float(default.launch_cost), step=500.0,
                                key=k(f"fixed:{suffix}"), help="Total cost over the declared planning period, deducted once.")
        currency = st.text_input("Currency label", "NOK", max_chars=12, key=k("planner_currency"))
    period = st.text_input("Planning period", "Four weeks", key=k("planning_period"), max_chars=80)
    rate = st.slider("Share of launch sales expected to replace your own existing items", 0, 100,
                     round(default.cannibalization * 100), format="%d%%", key=k(f"rate:{suffix}"))
    st.caption("The remaining share is new to your portfolio, combining competitor switching and category expansion. "
               "It is not necessarily new to the market. Changing price does not automatically change the entered demand.")
    return edited, Launch(name, units, price, cost, rate / 100, fixed), currency, period, source, context


def planner() -> None:
    sig.header("ASSUMPTION-BASED PLANNING", "Where does the new volume come from?",
               "Change the inputs and follow the effect on the whole menu or product portfolio.")
    portfolio, launch, currency, period, source, context = _planner_inputs()
    result = plan_launch(portfolio, launch)
    summary, items = result["summary"], result["items"]
    st.divider()
    st.subheader(f"Portfolio effect · {period or 'declared period'}")
    a, b, c, d = st.columns(4)
    a.metric("Incremental units", f"{summary['incremental_units']:,.0f}")
    b.metric("Displaced units", f"{summary['displaced_units']:,.0f}")
    c.metric("Revenue change", money(summary["incremental_revenue"], currency))
    d.metric("Contribution change", money(summary["incremental_contribution"], currency))
    if summary["incremental_contribution"] > 0:
        st.success(f"Under these assumptions, the portfolio adds {money(summary['incremental_contribution'], currency)} "
                   "of contribution after the declared launch cost.")
    else:
        st.warning("Under these assumptions, the launch does not add contribution after the declared launch cost.")
    left, right = st.columns(2)
    with left:
        st.markdown("**Source of launch volume**")
        positive = items[items.displaced_units > 0]
        labels = list(positive.item) + ["New to portfolio", launch.name]
        values = list(positive.displaced_units) + [summary["incremental_units"]]
        colors = [RUST] * len(positive) + [GREEN, BLUE]
        fig = go.Figure(go.Sankey(node=dict(label=labels, color=colors, pad=15, thickness=12),
                                 link=dict(source=list(range(len(values))), target=[len(labels) - 1] * len(values),
                                           value=values, color="rgba(79,128,162,0.25)")))
        chart(fig, "source_flow")
    with right:
        st.markdown("**Contribution bridge**")
        fig = go.Figure(go.Waterfall(
            x=["New item", "Incumbent change", "Launch cost", "Net change"],
            y=[summary["new_item_contribution"], -summary["lost_incumbent_contribution"], -launch.launch_cost, 0],
            measure=["relative", "relative", "relative", "total"],
            increasing=dict(marker_color=GREEN), decreasing=dict(marker_color=RUST), totals=dict(marker_color=BLUE)))
        fig.update_yaxes(title=currency)
        chart(fig, "contribution_bridge")
    st.markdown("**Item-level substitution**")
    table(items.rename(columns={"displaced_units": "Displaced units", "remaining_units": "Remaining units",
                               "lost_contribution": "Contribution displaced"}))
    if (items.unit_margin < 0).any() or launch.price < launch.unit_cost:
        st.info("At least one item has a negative unit margin. Displacing loss-making units can improve contribution.")
    st.subheader("How fragile is the result?")
    st.caption("Sensitivity scenarios, not confidence intervals. Launch volume varies ±25%; all prices and costs stay fixed. "
               "Infeasible combinations are omitted, not silently capped.")
    grid = sensitivity_grid(portfolio, launch)
    result["sensitivity"] = grid
    plot = grid.copy()
    plot["Volume"] = plot.volume_multiplier.map({0.75: "75% of planned volume", 1.0: "Planned volume", 1.25: "125% of planned volume"})
    plot["Cannibalization (%)"] = plot.cannibalization_rate * 100
    fig = px.line(plot, x="Cannibalization (%)", y="incremental_contribution", color="Volume",
                  color_discrete_sequence=[RUST, BLUE, GREEN], labels={"incremental_contribution": f"Contribution change ({currency})"})
    fig.add_hline(y=0, line_dash="dot", line_color="#645c50")
    fig.add_vline(x=launch.cannibalization * 100, line_dash="dot", line_color=BLUE)
    chart(fig, "sensitivity", 330)
    st.caption("Baseline → scenario: "
               f"{summary['baseline_units']:,.0f} → {summary['scenario_units']:,.0f} units · "
               f"{money(summary['baseline_contribution'], currency)} → {money(summary['scenario_contribution'], currency)} contribution.")
    config = {"launch": asdict(launch), "currency": currency, "period": period, "context": context,
              "method": "capacity-constrained source-of-volume accounting; user-assumed weights and cannibalization"}
    st.download_button("Download planning evidence pack", evidence_pack("planning scenario", portfolio, result, config, source),
                       "shift-planning-evidence.zip", "application/zip", key=k("planner_export"))
    st.caption("ZIP includes the entered portfolio, assumptions, item effects, sensitivity scenarios and research links.")


def _historical_inputs():
    context = st.radio("Evidence context", CONTEXTS, horizontal=True, key=k("history_context"))
    data, default_date, default_item = historical_demo(context)
    source_type = st.radio("Data source", ["Fictional demo", "Upload CSV"], horizontal=True, key=k("history_source"))
    source = f"Fictional synthetic {context.lower()} data; seed 214"
    if source_type == "Upload CSV":
        upload = st.file_uploader("Daily or weekly location × item sales", type=["csv"], key=k("history_upload"))
        if upload is None:
            st.info("Upload a panel CSV or switch back to the fictional demo. The Data guide explains the schema.")
            return None
        data = read_csv(upload.getvalue())
        source = f"Uploaded panel: {upload.name}"
        if not {"item", "date"}.issubset(data.columns):
            raise DataProblem("The panel CSV needs item and date columns. Open the Data guide for the complete schema.")
        choices = sorted(data.item.dropna().astype(str).unique())
        if not choices:
            raise DataProblem("No item names found in the uploaded panel.")
        default_item = choices[-1]
        valid_dates = pd.to_datetime(data.date, errors="coerce", utc=True).dropna().dt.tz_localize(None).sort_values().unique()
        if not len(valid_dates):
            raise DataProblem("No valid dates found. Use YYYY-MM-DD dates.")
        default_date = str(pd.Timestamp(valid_dates[len(valid_dates) // 2]).date())
    st.caption(source)
    digest = hashlib.sha256(csv_bytes(data)).hexdigest()
    choices = sorted(data.item.dropna().astype(str).unique())
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    with c1:
        new_item = st.selectbox("Launch item", choices, index=choices.index(default_item), key=k(f"launch_item:{digest}"))
    with c2:
        date = st.date_input("First full launch period", value=pd.Timestamp(default_date).date(), key=k(f"launch_date:{digest}"))
    with c3:
        fixed = st.number_input("Total launch cost", 0.0, 1e12, 12000.0 if source_type == "Fictional demo" else 0.0,
                                key=k(f"history_cost:{digest}"), help="Total for all test locations over all post-launch periods; deducted once.")
    with c4:
        currency = st.text_input("Currency", "NOK", key=k("history_currency"), max_chars=12)
    with st.expander(f"Inspect input data · {len(data):,} rows"):
        table(data.head(500))
        st.caption("Preview limited to 500 rows; the analysis uses every validated row.")
    st.caption("Use one common launch date. Controls must not offer the new item or be affected by the launch. "
               "Units, prices and costs must be comparable across the whole study.")
    signature = f"{digest}:{new_item}:{date}:{fixed}"
    run = st.button("Analyze launch", type="primary", key=k("run_history"))
    if run or (source_type == "Fictional demo" and st.session_state.get(k("history_signature")) != signature):
        st.session_state.pop(k("history_result"), None)
        st.session_state.pop(k("history_signature"), None)
        with st.spinner("Comparing locations and resampling complete location histories…"):
            result = analyze_launch(data, date, new_item, launch_cost=fixed)
        st.session_state[k("history_result")] = result
        st.session_state[k("history_signature")] = signature
    if st.session_state.get(k("history_signature")) != signature:
        st.info("Click Analyze launch to calculate results for the current data and settings.")
        return None
    return data, st.session_state[k("history_result")], source, currency


def _metric(container, title: str, values: dict, currency: str | None = None, percent: bool = False) -> None:
    def format_value(value):
        if percent:
            return f"{value:.0%}"
        return money(value, currency) if currency else f"{value:,.0f}"
    container.metric(title, format_value(values["estimate"]))
    if values["low"] is not None:
        container.caption(f"95% interval: {format_value(values['low'])} to {format_value(values['high'])}")
    else:
        container.caption("Interval unavailable: sparse launch volume")


def evidence() -> None:
    sig.header("HISTORICAL LAUNCH COMPARISON", "What changed beyond the launch item?",
               "Difference-in-differences across comparable test and control locations.")
    inputs = _historical_inputs()
    if inputs is None:
        return
    data, result, source, currency = inputs
    summary, audit = result["summary"], result["audit"]
    st.divider()
    st.caption(f"TOTAL EFFECT · {audit['test_locations']} test locations × {audit['post_periods']} post-launch periods · "
               f"{audit['control_locations']} control locations · equal location weights")
    a, b, c, d = st.columns(4)
    _metric(a, "New-item units", summary["new_item_units"])
    _metric(b, "Net incumbent displacement", summary["net_displaced_units"])
    _metric(c, "Net displacement / new units", summary["net_displacement_rate"], percent=True)
    _metric(d, "Contribution change", summary["incremental_contribution"], currency=currency)
    contribution = summary["incremental_contribution"]
    if contribution["low"] > 0:
        st.success("The estimated contribution effect and its interval are above zero, conditional on the comparison design and declared costs.")
    elif contribution["high"] < 0:
        st.warning("The estimated contribution effect and its interval are below zero, conditional on the comparison design and declared costs.")
    else:
        st.info("The contribution interval crosses zero. These data do not resolve whether the launch improved contribution.")
    sig.note("warn", result["warnings"][0])
    st.caption(f"Estimated portfolio change: {summary['incremental_units']['estimate']:,.0f} units and "
               f"{money(summary['incremental_revenue']['estimate'], currency)} revenue. "
               "Net displacement allows incumbent gains to offset losses; it does not identify individual switchers.")
    left, right = st.columns(2)
    with left:
        st.markdown("**Incumbent demand before and after launch**")
        fig = px.line(result["series"], x="date", y="incumbent_units", color="group",
                      color_discrete_map={"test": BLUE, "control": RUST},
                      labels={"incumbent_units": "Incumbent units / location", "date": "", "group": ""})
        fig.add_vline(x=pd.Timestamp(audit["launch_date"]).timestamp() * 1000, line_dash="dot", line_color="#645c50")
        chart(fig, "observed_history")
    with right:
        st.markdown("**Estimated item effects · units**")
        item_plot = result["items"].copy()
        # The percentile interval need not straddle the point estimate. Draw endpoints directly.
        fig = go.Figure()
        for _, row in item_plot.iterrows():
            fig.add_trace(go.Scatter(x=[row.units_low, row.units_high], y=[row["item"], row["item"]],
                                    mode="lines", line=dict(color="#a19786", width=3), showlegend=False,
                                    hovertemplate="95% endpoint: %{x:,.0f}<extra></extra>"))
        fig.add_trace(go.Scatter(x=item_plot.units_estimate, y=item_plot.item, mode="markers", showlegend=False,
                                marker=dict(color=[BLUE if v == "launch" else RUST for v in item_plot.role], size=10),
                                hovertemplate="%{y}: %{x:,.0f} units<extra></extra>"))
        fig.add_vline(x=0, line_color="#645c50", line_dash="dot")
        fig.update_xaxes(title="Effect across all test locations / post periods")
        chart(fig, "item_effects")
    st.caption("Item intervals are exploratory and are not corrected for multiple comparisons. "
               "Portfolio intervals preserve correlations across items by resampling whole locations.")
    with st.expander("Study diagnostics and uncertainty", expanded=True):
        placebo = result["placebo"]
        st.markdown(f"**Pre-launch placebo:** {placebo['estimate']:,.1f} incumbent units per location-period "
                    f"(95% interval {placebo['low']:,.1f} to {placebo['high']:,.1f}). "
                    "This compares the first and second halves of the pre-period. An interval crossing zero does not prove parallel trends.")
        for warning in result["warnings"][1:]:
            st.warning(warning)
        st.caption(f"{audit['pre_periods']} pre-periods; {audit['post_periods']} post-periods; "
                   f"{'daily' if audit['period_days'] == 1 else 'weekly'} observations. "
                   "2,000 bootstrap draws; fixed seed for reproducibility. No automatic outlier removal or missing-value imputation.")
        st.markdown("**Observed location-period total units · all dates**")
        table(result["descriptive"].round(1))
    with st.expander("Full item estimates and counterfactual totals"):
        table(result["items"].round(2))
        st.caption("Item contribution effects exclude the overall fixed launch cost, which is deducted once in the portfolio metric.")
    config = {**result["config"], "currency": currency, "evidence_tier": "historical group comparison"}
    st.download_button("Download launch evidence pack", evidence_pack("historical launch", data, result, config, source),
                       "shift-launch-evidence.zip", "application/zip", key=k("history_export"))
    st.caption("ZIP includes the loaded input data, estimates, diagnostics, assumptions and references.")


def data_guide() -> None:
    sig.header("DATA & STUDY DESIGN", "Bring the right comparison.",
               "Start with an editable template, or use the fictional examples to explore the workflow.")
    context = st.radio("Template context", CONTEXTS, horizontal=True, key=k("template_context"))
    portfolio, _ = portfolio_demo(context)
    panel, date, item = historical_demo(context)
    a, b = st.columns(2)
    a.download_button("Portfolio CSV template", csv_bytes(portfolio), "shift-portfolio-template.csv", "text/csv", key=k("guide_portfolio"))
    b.download_button("Complete launch-panel example", csv_bytes(panel), "shift-launch-panel-demo.csv", "text/csv", key=k("guide_panel"))
    st.caption(f"Both downloads contain fictional values. Panel launch: {date}; new item: {item}.")
    st.subheader("Launch planner schema")
    table(pd.DataFrame([
        ("item", "Unique incumbent item name"), ("units", "Baseline volume in the declared planning period"),
        ("price", "Net selling price per comparable unit"), ("unit_cost", "All variable costs per comparable unit"),
        ("overlap", "Your relative substitution weight from 0 to 1; 0 excludes an item")], columns=["Column", "Meaning"]))
    st.subheader("Launch evidence schema")
    table(pd.DataFrame([
        ("date", "YYYY-MM-DD; one complete daily or weekly calendar"),
        ("location", "Independent restaurant, store or other assignment unit; stable identifier"),
        ("group", "Exactly test or control; stable for each location"),
        ("item", "One row for every date × location × item combination"),
        ("units", "Finite, nonnegative sales volume; explicit verified zeros"),
        ("price", "Average realized price per unit for this row"),
        ("unit_cost", "Average variable cost per unit for this row")], columns=["Column", "Meaning"]))
    st.markdown("**Before upload**\n\n"
                "1. Define one comparable choice set and convert pack sizes to equivalent units.\n"
                "2. Choose independent test and control locations with comparable trends; randomize where practical.\n"
                "3. Use one common launch date, at least four periods on either side and at least four locations per group. More independent locations are preferable.\n"
                "4. Include a complete panel, with zero new-item sales before launch and in controls. Missing data are not zero sales.\n"
                "5. Review price changes, promotions, holidays, distribution, stockouts, spillovers and kitchen capacity. They can invalidate the comparison.\n"
                "6. Aggregate transactions using unit-weighted prices and costs. Use a finite price and cost even for zero-sales rows.")
    sig.note("info", "**Only one location or ordinary sales history?** You can use the planner, but the historical "
             "route needs a credible comparison group. Staggered launches, changing assortments and basket effects require a different study design.")
    st.caption("CSV: UTF-8, comma or semicolon delimited, decimal points. Limits: 20 MB, 250,000 rows, 100 items. "
               "Uploaded rows stay in the running app; there is no external analytics API or automatic persistence.")


def research() -> None:
    sig.header("RESEARCH & LIMITS", "Yes, this can be built. Evidence decides what it can claim.",
               "Primary research supports the problem; the implemented methods and their boundaries are explicit.")
    table(pd.DataFrame([
        ("Before launch", "Portfolio volumes, margins and explicit switching assumptions", "Accounting scenario; sensitivity to assumptions"),
        ("After a common launch", "Complete test/control panel with unaffected controls", "Estimated net displacement and contribution with conditional intervals"),
        ("Customer switching", "Choice experiments or individual-level behavior with a valid design", "Not estimated by this app"),
        ("Own vs competitor vs category growth", "Own, competitor and category demand with identification", "Own-sales-only input cannot separate all three")],
        columns=["Question", "Evidence needed", "Current scope"]))
    st.subheader("How the planner works")
    st.latex(r"D = Q_{new}c,\qquad \Delta Q = Q_{new}-D")
    st.markdown("Displaced units **D** equal entered launch volume times the assumed cannibalization share. "
                "Allocate D in proportion to incumbent units × overlap weight. If an item runs out of volume, "
                "redistribute its remaining allocation across eligible items. Reject infeasible totals.")
    st.latex(r"\Delta C=Q_{new}(P_{new}-V_{new})-\sum_i D_i(P_i-V_i)-F")
    st.caption("P = price; V = variable unit cost; F = total incremental launch cost. All quantities refer to the same period.")
    st.subheader("How the historical comparison works")
    st.latex(r"\widehat{\Delta}_i=(\bar y_{T,post,i}-\bar y_{T,pre,i})-(\bar y_{C,post,i}-\bar y_{C,pre,i})")
    st.markdown("Compute each location's pre- and post-period mean, then average locations equally within each group. "
                "Scale the contrast by test locations × post-periods to report a total effect. Repeat separately for units, "
                "revenue and contribution. The new item's untreated sales are structurally zero in this design.")
    st.latex(r"\widehat c_{net}=\frac{-\sum_{i\in incumbents}\widehat{\Delta}_i}{\bar Q_{T,post,new}}")
    st.markdown("Resample whole locations within each group 2,000 times; keep every item's history together. "
                "Report percentile intervals and a split-pre placebo. This simple balanced comparison supports one "
                "common launch, not staggered treatment or automatic causal discovery.")
    st.subheader("Articles and method sources")
    for source in SOURCES:
        st.markdown(f"**[{source['title']}]({source['url']})**  \n{source['authors']} · {source['year']}")
        st.write(source["finding"])
        st.caption(source["application"])
        st.markdown(f"[Source record / access]({source['access']}) · {source['evidence']}")
        st.divider()
    st.subheader("Interpretation boundaries")
    for limit in LIMITS:
        st.markdown(f"- {limit}")
    st.download_button("Download research references", json.dumps(SOURCES, indent=2, ensure_ascii=False),
                       "shift-research-sources.json", "application/json", key=k("sources_export"))


PAGES = {"Overview": overview, "Launch planner": planner, "Launch evidence": evidence,
         "Data guide": data_guide, "Research & limits": research}


def render() -> None:
    sig.apply(NS)
    sig.sidebar_brand(NS, "New demand, or demand moved around?")
    with st.sidebar:
        page = st.radio("Navigate", list(PAGES), label_visibility="collapsed", key=k("page"))
        st.divider()
        st.caption("MENU + PRODUCT PORTFOLIOS")
        st.write("Make the whole portfolio count.")
        st.caption("Local analysis · CSV inputs · no external AI calls")
    sig.masthead(NS, ["Trace substitution", "Count contribution", "Keep uncertainty"], "VOLUME → SUBSTITUTION → VALUE")
    try:
        PAGES[page]()
    except (DataProblem, pd.errors.ParserError) as exc:
        st.error(str(exc))
    sig.footer(NS, __version__, "portfolio effects, with assumptions in view")
