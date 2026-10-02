from dataclasses import replace
from io import BytesIO
import json
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest

from shiftsignal.analysis import DataProblem, Launch, analyze_launch, plan_launch, sensitivity_grid, validate_panel
from shiftsignal.examples import historical_demo, portfolio_demo
from shiftsignal.io import csv_bytes, evidence_pack, read_csv


def exact_panel():
    rows = []
    for group in ["test", "control"]:
        for location in range(4):
            for t, date in enumerate(pd.date_range("2026-01-05", periods=8, freq="7D")):
                treated = group == "test" and t >= 4
                for item, units, price, cost in [
                    ("A", 100 + location * 10 + t * 2 - 20 * treated, 10, 5),
                    ("B", 50 + location * 4 + t - 10 * treated, 12, 4),
                    ("New", 50 * treated, 18, 8),
                ]:
                    rows.append((str(date.date()), f"{group}-{location}", group, item, units, price, cost))
    return pd.DataFrame(rows, columns=["date", "location", "group", "item", "units", "price", "unit_cost"])


def analyze(frame, **kwargs):
    return analyze_launch(frame, "2026-02-02", "New", iterations=200, **kwargs)


@pytest.mark.parametrize("context", ["Restaurant menu", "Product portfolio"])
def test_planner_conserves_units_and_money(context):
    portfolio, launch = portfolio_demo(context)
    result = plan_launch(portfolio, launch)
    s, items = result["summary"], result["items"]
    assert items.displaced_units.sum() == pytest.approx(launch.units * launch.cannibalization)
    assert np.all(items.remaining_units >= 0)
    assert s["scenario_units"] == pytest.approx(items.remaining_units.sum() + launch.units)
    actual = (items.remaining_units * (items.price - items.unit_cost)).sum()
    actual += launch.units * (launch.price - launch.unit_cost) - launch.launch_cost
    assert s["scenario_contribution"] == pytest.approx(actual)


def test_allocation_saturates_and_redistributes():
    frame = pd.DataFrame([("A", 10, 10, 2, 1), ("B", 100, 10, 2, 0.01)],
                         columns=["item", "units", "price", "unit_cost", "overlap"])
    result = plan_launch(frame, Launch(units=50, cannibalization=1))["items"]
    assert list(result.displaced_units) == pytest.approx([10, 40])


def test_capacity_never_silently_changes_assumptions():
    frame, launch = portfolio_demo()
    frame.overlap = 0
    with pytest.raises(DataProblem, match="eligible incumbents"):
        plan_launch(frame, launch)
    result = plan_launch(frame, replace(launch, cannibalization=0))["summary"]
    assert result["displaced_units"] == 0
    assert result["incremental_units"] == launch.units


def test_zero_launch_and_negative_margin():
    frame, launch = portfolio_demo()
    result = plan_launch(frame, replace(launch, units=0))["summary"]
    assert result["cannibalization_rate"] is None
    assert result["incremental_contribution"] == -launch.launch_cost
    result = plan_launch(frame, replace(launch, price=1, unit_cost=10))["summary"]
    assert result["incremental_contribution"] < 0


@pytest.mark.parametrize("column,value", [("units", -1), ("units", np.nan), ("price", np.inf), ("overlap", 2)])
def test_invalid_portfolio_is_rejected(column, value):
    frame, launch = portfolio_demo()
    frame[column] = frame[column].astype(float)
    frame.loc[0, column] = value
    with pytest.raises(DataProblem):
        plan_launch(frame, launch)


def test_sensitivity_marks_impossible_scenarios():
    frame, launch = portfolio_demo()
    grid = sensitivity_grid(frame, replace(launch, units=1e6))
    assert not grid.feasible.all()
    assert grid.loc[~grid.feasible, "incremental_contribution"].isna().all()
    assert grid.loc[grid.cannibalization_rate.eq(0), "feasible"].all()


def test_exact_did_recovers_known_effect_and_deducts_cost_once():
    result = analyze(exact_panel(), launch_cost=100)
    summary = result["summary"]
    for key, truth in {"new_item_units": 800, "net_displaced_units": 480,
                       "incremental_units": 320, "incremental_contribution": 5020,
                       "net_displacement_rate": 0.6}.items():
        assert summary[key]["estimate"] == pytest.approx(truth)
        assert summary[key]["low"] == pytest.approx(truth)
        assert summary[key]["high"] == pytest.approx(truth)
    assert result["placebo"]["estimate"] == pytest.approx(0)


def test_cluster_bootstrap_preserves_cross_item_correlation():
    frame = exact_panel()
    for loc in range(4):
        post = frame.location.eq(f"test-{loc}") & frame.date.ge("2026-02-02")
        frame.loc[post & frame.item.eq("A"), "units"] += loc * 3
        frame.loc[post & frame.item.eq("B"), "units"] -= loc * 3
    result = analyze(frame)
    summary = result["summary"]["incremental_units"]
    assert summary["low"] == pytest.approx(summary["high"])
    assert (result["items"].units_high - result["items"].units_low).max() > 0


def test_halo_and_rates_above_one_are_not_clipped():
    frame = exact_panel()
    mask = frame.group.eq("test") & frame.date.ge("2026-02-02") & frame.item.eq("A")
    frame.loc[mask, "units"] += 50
    result = analyze(frame)
    assert result["summary"]["net_displacement_rate"]["estimate"] < 0
    assert any("halo" in text for text in result["warnings"])
    frame.loc[mask, "units"] -= 90
    result = analyze(frame)
    assert result["summary"]["net_displacement_rate"]["estimate"] > 1
    assert any("exceeds" in text for text in result["warnings"])


def test_analysis_is_order_independent_and_reproducible():
    panel, launch_date, item = historical_demo()
    first = analyze_launch(panel, launch_date, item, iterations=200)
    second = analyze_launch(panel.sample(frac=1, random_state=5), launch_date, item, iterations=200)
    assert first["summary"] == second["summary"]
    assert abs(first["summary"]["net_displacement_rate"]["estimate"] - 0.6) < 0.12


@pytest.mark.parametrize("damage,match", [
    (lambda x: x.iloc[:-1], "incomplete"),
    (lambda x: pd.concat([x, x.iloc[[0]]]), "Duplicate"),
    (lambda x: x[~x.location.eq("control-0")], "4 independent"),
    (lambda x: x[~x.date.eq("2026-01-12")], "calendar"),
    (lambda x: x.assign(group="test"), "exactly"),
    (lambda x: x.assign(units=np.nan), "finite"),
])
def test_bad_panels_fail_with_actionable_messages(damage, match):
    with pytest.raises(DataProblem, match=match):
        analyze(damage(exact_panel()))


def test_control_contamination_and_prelaunch_sales_rejected():
    for group, date in [("control", "2026-02-02"), ("test", "2026-01-05")]:
        frame = exact_panel()
        frame.loc[frame.item.eq("New") & frame.group.eq(group) & frame.date.eq(date), "units"] = 1
        with pytest.raises(DataProblem, match="pre-launch or control"):
            analyze(frame)


def test_missing_launch_date_not_guessed():
    with pytest.raises(DataProblem, match="period start"):
        validate_panel(exact_panel(), "2026-02-03", "New")


def test_exports_are_reproducible_and_include_the_actual_inputs():
    frame = exact_panel()
    result = analyze(frame)
    pack = evidence_pack("historical", frame, result, result["config"], "fictional test")
    with ZipFile(BytesIO(pack)) as archive:
        metadata = json.loads(archive.read("evidence.json"))
        assert metadata["summary"]["incremental_units"]["estimate"] == 320
        assert metadata["sources"]
        exported = pd.read_csv(BytesIO(archive.read("inputs.csv")))
        pd.testing.assert_frame_equal(exported, frame)


def test_csv_handles_semicolons_and_protects_formula_labels():
    frame = read_csv(b"item;units;price;unit_cost;overlap\nA;10;5;2;0.8\n")
    assert frame.units.iloc[0] == 10
    frame.loc[0, "item"] = "=1+1"
    assert "'=1+1" in csv_bytes(frame).decode("utf-8-sig")


def test_ui_is_not_imported_by_analysis_module():
    import subprocess
    import sys
    output = subprocess.check_output([sys.executable, "-c",
        "import shiftsignal.analysis, sys; print('streamlit' in sys.modules)"], text=True)
    assert output.strip() == "False"
