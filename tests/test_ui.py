from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.mark.parametrize("page", ["Overview", "Launch planner", "Launch evidence", "Data guide", "Research & limits"])
def test_all_pages_render_without_errors(page):
    app = AppTest.from_file(str(APP), default_timeout=40).run()
    app.radio(key="shift:page").set_value(page).run()
    assert not app.exception
    assert not app.error
    if page == "Launch evidence":
        assert len(app.metric) == 4
        assert "interval" in " ".join(x.value for x in app.caption)


def test_product_planner_updates_financial_results():
    app = AppTest.from_file(str(APP), default_timeout=40).run()
    app.radio(key="shift:page").set_value("Launch planner").run()
    app.radio(key="shift:planner_context").set_value("Product portfolio").run()
    before = app.metric[0].value
    app.slider(key="shift:rate:Product portfolio").set_value(100).run()
    assert not app.exception
    assert app.metric[0].value != before
    assert app.metric[0].value == "0"


def test_both_historical_examples_and_no_stale_results_for_upload():
    app = AppTest.from_file(str(APP), default_timeout=40).run()
    app.radio(key="shift:page").set_value("Launch evidence").run()
    app.radio(key="shift:history_context").set_value("Product portfolio").run()
    assert not app.exception
    assert not app.error
    assert len(app.metric) == 4
    app.radio(key="shift:history_source").set_value("Upload CSV").run()
    assert len(app.metric) == 0
    assert not app.exception
