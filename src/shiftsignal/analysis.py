"""Transparent source-of-volume scenarios and balanced-panel launch comparisons.

The planner is an accounting scenario, not an estimated choice model. Historical
estimates use one common launch date, two groups and equal-weight locations.
Bootstrap sampling keeps every item and period of a location together.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


class DataProblem(ValueError):
    """An actionable input or study-design problem."""


def _required(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise DataProblem("Add at least one data row.")
    if frame.columns.duplicated().any():
        raise DataProblem("Column names must be unique.")
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise DataProblem("Missing columns: " + ", ".join(missing) + ". Download a template for the required format.")
    return frame[columns].copy()


def _numbers(frame: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        if not np.isfinite(values.to_numpy(dtype=float)).all() or (values < 0).any():
            raise DataProblem(f"{column}: every value must be a finite, nonnegative number; blanks are not zeros.")
        frame[column] = values.astype(float)


def _labels(frame: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        if frame[column].isna().any():
            raise DataProblem(f"{column}: missing labels are not allowed.")
        frame[column] = frame[column].astype(str).str.strip()
        if frame[column].eq("").any():
            raise DataProblem(f"{column}: blank labels are not allowed.")


def validate_portfolio(frame: pd.DataFrame) -> pd.DataFrame:
    frame = _required(frame, ["item", "units", "price", "unit_cost", "overlap"])
    if len(frame) > 100:
        raise DataProblem("Use at most 100 incumbent items in one comparable choice set.")
    _labels(frame, ["item"])
    _numbers(frame, ["units", "price", "unit_cost", "overlap"])
    if frame.item.duplicated().any():
        raise DataProblem("Use one row per incumbent item, with unique item names.")
    if (frame.overlap > 1).any():
        raise DataProblem("overlap must be between 0 and 1. It is a relative substitution weight, not a probability.")
    return frame.reset_index(drop=True)


@dataclass(frozen=True)
class Launch:
    name: str = "New item"
    units: float = 500.0
    price: float = 175.0
    unit_cost: float = 65.0
    cannibalization: float = 0.55
    launch_cost: float = 10000.0


def _validate_launch(launch: Launch, items: pd.Series) -> None:
    if not launch.name.strip() or launch.name.strip() in items.values:
        raise DataProblem("Give the new item a nonblank name different from every incumbent item.")
    for name in ["units", "price", "unit_cost", "cannibalization", "launch_cost"]:
        value = getattr(launch, name)
        if not np.isfinite(value) or value < 0:
            raise DataProblem(f"Launch {name} must be finite and nonnegative.")
    if launch.cannibalization > 1:
        raise DataProblem("The planned cannibalization share must be between 0 and 1.")


def _allocate(capacity: np.ndarray, weights: np.ndarray, demand: float) -> np.ndarray:
    """Proportional allocation with saturation and redistribution; conserve units."""
    eligible = weights > 0
    available = float(capacity[eligible].sum())
    if demand > available + 1e-8:
        raise DataProblem(
            f"This scenario needs {demand:,.0f} displaced units, but eligible incumbents only sell "
            f"{available:,.0f}. Reduce launch volume or cannibalization, or review zero overlap weights."
        )
    lost = np.zeros_like(capacity, dtype=float)
    remaining = demand
    for _ in range(len(capacity) + 1):
        active = eligible & (capacity - lost > 1e-10)
        if remaining <= 1e-8 or not active.any():
            break
        proposed = remaining * weights[active] / weights[active].sum()
        allocated = np.minimum(proposed, capacity[active] - lost[active])
        lost[active] += allocated
        remaining -= float(allocated.sum())
    return lost


def plan_launch(portfolio: pd.DataFrame, launch: Launch) -> dict:
    table = validate_portfolio(portfolio)
    _validate_launch(launch, table.item)
    displaced = launch.units * launch.cannibalization
    table["displaced_units"] = _allocate(
        table.units.to_numpy(), (table.units * table.overlap).to_numpy(), displaced
    )
    table["remaining_units"] = table.units - table.displaced_units
    table["unit_margin"] = table.price - table.unit_cost
    table["lost_revenue"] = table.displaced_units * table.price
    table["lost_contribution"] = table.displaced_units * table.unit_margin
    baseline_revenue = float((table.units * table.price).sum())
    baseline_contribution = float((table.units * table.unit_margin).sum())
    new_contribution = launch.units * (launch.price - launch.unit_cost)
    revenue_change = launch.units * launch.price - float(table.lost_revenue.sum())
    contribution_change = new_contribution - float(table.lost_contribution.sum()) - launch.launch_cost
    summary = {
        "new_item_units": launch.units,
        "displaced_units": displaced,
        "incremental_units": launch.units - displaced,
        "cannibalization_rate": launch.cannibalization if launch.units > 0 else None,
        "baseline_units": float(table.units.sum()),
        "scenario_units": float(table.units.sum()) + launch.units - displaced,
        "baseline_revenue": baseline_revenue,
        "scenario_revenue": baseline_revenue + revenue_change,
        "incremental_revenue": revenue_change,
        "baseline_contribution": baseline_contribution,
        "new_item_contribution": new_contribution,
        "lost_incumbent_contribution": float(table.lost_contribution.sum()),
        "launch_cost": launch.launch_cost,
        "incremental_contribution": contribution_change,
        "scenario_contribution": baseline_contribution + contribution_change,
    }
    return {"summary": summary, "items": table}


def sensitivity_grid(portfolio: pd.DataFrame, launch: Launch) -> pd.DataFrame:
    from dataclasses import replace

    rows = []
    for multiplier in [0.75, 1.0, 1.25]:
        for rate in np.linspace(0, 1, 21):
            candidate = replace(launch, units=launch.units * multiplier, cannibalization=float(rate))
            try:
                result = plan_launch(portfolio, candidate)["summary"]
                value = result["incremental_contribution"]
                feasible = True
            except DataProblem:
                value, feasible = np.nan, False
            rows.append({"volume_multiplier": multiplier, "launch_units": candidate.units,
                         "cannibalization_rate": rate, "incremental_contribution": value, "feasible": feasible})
    return pd.DataFrame(rows)


def validate_panel(frame: pd.DataFrame, launch_date, new_item: str) -> tuple[pd.DataFrame, dict]:
    frame = _required(frame, ["date", "location", "group", "item", "units", "price", "unit_cost"])
    if len(frame) > 250_000:
        raise DataProblem("Use at most 250,000 rows per analysis.")
    _labels(frame, ["location", "group", "item"])
    _numbers(frame, ["units", "price", "unit_cost"])
    dates = pd.to_datetime(frame.date, errors="coerce", utc=True)
    if dates.isna().any() or (dates != dates.dt.normalize()).any():
        raise DataProblem("date must contain valid dates without times, for example 2026-05-04.")
    frame["date"] = dates.dt.tz_localize(None)
    try:
        boundary = pd.Timestamp(launch_date)
        if pd.isna(boundary) or boundary.tzinfo is not None or boundary != boundary.normalize():
            raise ValueError
    except (ValueError, TypeError):
        raise DataProblem("Choose a valid launch date without time or timezone.") from None
    if set(frame.group) != {"test", "control"}:
        raise DataProblem("group must contain exactly 'test' and 'control'.")
    if frame.groupby("location").group.nunique().max() != 1:
        raise DataProblem("Each location must stay in one group throughout the study.")
    if frame.duplicated(["date", "location", "item"]).any():
        raise DataProblem("Duplicate date/location/item rows found. Aggregate transactions to one row per cell first.")
    item_names = sorted(frame.item.unique())
    if not 2 <= len(item_names) <= 100 or new_item not in item_names:
        raise DataProblem("Select one launch item and include between 1 and 99 incumbent items.")
    calendar = pd.DatetimeIndex(sorted(frame.date.unique()))
    gaps = np.diff(calendar.values).astype("timedelta64[D]").astype(int)
    if len(gaps) == 0 or len(set(gaps)) != 1 or gaps[0] not in (1, 7):
        raise DataProblem("Use a complete daily or weekly calendar with equally spaced dates. Missing periods are not zeros.")
    if boundary not in calendar:
        raise DataProblem("The launch date must be a period start present in the data. Use the first full launch period.")
    pre_dates, post_dates = calendar[calendar < boundary], calendar[calendar >= boundary]
    if len(pre_dates) < 4 or len(post_dates) < 4:
        raise DataProblem("Include at least 4 pre-launch and 4 post-launch periods; longer comparable windows are preferable.")
    counts = frame[["location", "group"]].drop_duplicates().groupby("group").size().to_dict()
    if min(counts.values()) < 4:
        raise DataProblem("Historical comparison needs at least 4 independent locations per group; 10 or more is preferable.")
    expected_rows = len(calendar) * frame.location.nunique() * len(item_names)
    if len(frame) != expected_rows:
        raise DataProblem(
            f"The panel is incomplete: expected {expected_rows:,} date/location/item rows, received {len(frame):,}. "
            "Provide explicit zeros only for verified zero sales, including the launch item before launch and in controls."
        )
    is_new = frame.item.eq(new_item)
    forbidden = is_new & ((frame.date < boundary) | frame.group.eq("control"))
    if (frame.loc[forbidden, "units"] > 0).any():
        raise DataProblem("The launch item has pre-launch or control sales. This design requires a new item available only in test locations after launch.")
    if frame.loc[is_new, "units"].sum() <= 0:
        raise DataProblem("There are no post-launch sales for the selected launch item.")
    frame["revenue"] = frame.units * frame.price
    frame["contribution"] = frame.units * (frame.price - frame.unit_cost)
    if not np.isfinite(frame[["revenue", "contribution"]].to_numpy()).all():
        raise DataProblem("Revenue or contribution overflowed. Check the scale of units, price and unit_cost.")
    frame["post"] = frame.date >= boundary
    return frame, {"pre_periods": len(pre_dates), "post_periods": len(post_dates),
                   "test_locations": counts["test"], "control_locations": counts["control"],
                   "period_days": int(gaps[0]), "items": item_names, "launch_date": str(boundary.date())}


def analyze_launch(frame: pd.DataFrame, launch_date, new_item: str, *, launch_cost: float = 0,
                   iterations: int = 2000, seed: int = 20261002) -> dict:
    """Equal-location difference-in-differences, scaled to treated post-period totals.

    launch_cost is the total fixed incremental cost over ALL treated locations and
    ALL post periods. Percentile intervals resample locations within each group.
    They quantify sampling variation conditional on the design, not confounding.
    """
    if not np.isfinite(launch_cost) or launch_cost < 0:
        raise DataProblem("Total launch cost must be finite and nonnegative.")
    if not isinstance(iterations, int) or not 200 <= iterations <= 5000:
        raise DataProblem("Use between 200 and 5,000 bootstrap draws.")
    frame, audit = validate_panel(frame, launch_date, new_item)
    items = audit["items"]
    metrics = ["units", "revenue", "contribution"]
    new_index = items.index(new_item)
    incumbent = np.arange(len(items)) != new_index
    arrays = {}
    for group in ["test", "control"]:
        part = frame[frame.group.eq(group)]
        locations = sorted(part.location.unique())
        for post in [False, True]:
            means = part[part.post.eq(post)].groupby(["location", "item"])[metrics].mean()
            index = pd.MultiIndex.from_product([locations, items], names=["location", "item"])
            arrays[group, post] = means.reindex(index).to_numpy().reshape(len(locations), len(items), 3)
    t0, t1 = arrays["test", False], arrays["test", True]
    c0, c1 = arrays["control", False], arrays["control", True]
    dt, dc = t1 - t0, c1 - c0
    effect = dt.mean(axis=0) - dc.mean(axis=0)
    counterfactual = t0.mean(axis=0) + dc.mean(axis=0)
    scale = audit["test_locations"] * audit["post_periods"]
    rng = np.random.default_rng(seed)
    draws = np.empty((iterations, len(items), 3))
    for b in range(iterations):
        ti = rng.integers(0, len(dt), len(dt))
        ci = rng.integers(0, len(dc), len(dc))
        draws[b] = dt[ti].mean(axis=0) - dc[ci].mean(axis=0)

    def interval(estimate, values):
        lo, hi = np.quantile(values, [0.025, 0.975])
        return {"estimate": float(estimate), "low": float(lo), "high": float(hi)}

    summary = {}
    for j, metric in enumerate(metrics):
        summary[f"incremental_{metric}"] = interval(effect[:, j].sum() * scale, draws[:, :, j].sum(axis=1) * scale)
    summary["incremental_contribution"] = {
        k: v - launch_cost for k, v in summary["incremental_contribution"].items()
    }
    new_units = effect[new_index, 0] * scale
    displacement = -effect[incumbent, 0].sum() * scale
    summary["new_item_units"] = interval(new_units, draws[:, new_index, 0] * scale)
    summary["net_displaced_units"] = interval(displacement, -draws[:, incumbent, 0].sum(axis=1) * scale)
    valid = draws[:, new_index, 0] > 1e-9
    ratio = -draws[valid][:, incumbent, 0].sum(axis=1) / draws[valid, new_index, 0]
    summary["net_displacement_rate"] = (
        interval(displacement / new_units, ratio) if valid.mean() >= 0.95 else
        {"estimate": float(displacement / new_units), "low": None, "high": None}
    )
    rows = []
    for i, name in enumerate(items):
        row = {"item": name, "role": "launch" if i == new_index else "incumbent",
               "observed_units": float(t1[:, i, 0].mean() * scale),
               "counterfactual_units": float(counterfactual[i, 0] * scale)}
        for j, metric in enumerate(metrics):
            result = interval(effect[i, j] * scale, draws[:, i, j] * scale)
            row.update({f"{metric}_{key}": value for key, value in result.items()})
        rows.append(row)

    # A split-pre placebo tests whether the incumbent gap was already moving.
    pre = frame[(~frame.post) & (~frame.item.eq(new_item))].copy()
    pre_dates = sorted(pre.date.unique())
    pre["late"] = pre.date >= pre_dates[len(pre_dates) // 2]
    totals = pre.groupby(["group", "location", "date", "late"]).units.sum().reset_index()
    differences = totals.groupby(["group", "location", "late"]).units.mean().unstack("late")
    ptest = (differences[True] - differences[False]).loc["test"].to_numpy()
    pcontrol = (differences[True] - differences[False]).loc["control"].to_numpy()
    placebo_draws = np.array([
        rng.choice(ptest, len(ptest), replace=True).mean() - rng.choice(pcontrol, len(pcontrol), replace=True).mean()
        for _ in range(iterations)
    ])
    placebo = interval(ptest.mean() - pcontrol.mean(), placebo_draws)
    warnings = [
        "Historical association: causal interpretation requires parallel untreated trends, independent locations, "
        "no spillovers or anticipation, and no other changes that differ between groups.",
        "Intervals are 95% location-bootstrap percentile intervals. They do not include model bias, confounding, "
        "future demand uncertainty or uncertainty in entered costs.",
    ]
    if min(len(dt), len(dc)) < 10:
        warnings.append("Fewer than 10 locations in at least one group: bootstrap intervals may be unstable. Treat this as exploratory.")
    if placebo["low"] > 0 or placebo["high"] < 0:
        warnings.append("The split-pre placebo interval excludes zero: the groups were already changing differently before launch.")
    if (counterfactual[incumbent, 0] < 0).any():
        warnings.append("The additive comparison produces a negative counterfactual for an incumbent. Reconsider comparability; values are not clipped.")
    if summary["net_displacement_rate"]["estimate"] < 0:
        warnings.append("Negative net displacement indicates an estimated incumbent halo, not negative physical switching.")
    elif summary["net_displacement_rate"]["estimate"] > 1:
        warnings.append("Net displacement exceeds new-item volume. This can reflect wider decline or confounding; it is not a valid customer-switching fraction.")
    if valid.mean() < 0.95:
        warnings.append("Too many bootstrap samples have zero launch volume. The rate interval is withheld; use the unit effects.")
    period_series = frame.assign(incumbent_units=np.where(frame.item.eq(new_item), 0, frame.units)).groupby(
        ["date", "group"]
    )[["units", "incumbent_units", "revenue", "contribution"]].sum().reset_index()
    for group, count in [("test", len(dt)), ("control", len(dc))]:
        mask = period_series.group.eq(group)
        period_series.loc[mask, ["units", "incumbent_units", "revenue", "contribution"]] /= count
    describe = frame.groupby(["group", "location", "date"]).units.sum().groupby("group").agg(
        mean="mean", median="median", std="std", minimum="min", maximum="max"
    ).reset_index()
    return {"summary": summary, "items": pd.DataFrame(rows), "series": period_series,
            "audit": audit, "placebo": placebo, "warnings": warnings, "descriptive": describe,
            "config": {"new_item": new_item, "launch_date": audit["launch_date"], "launch_cost": launch_cost,
                       "iterations": iterations, "seed": seed, "method": "equal-location difference-in-differences"}}
