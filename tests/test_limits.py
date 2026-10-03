"""Data limits: none locally, demo caps only with SIGNAL_PUBLIC=1, plus the launchers' shared upload cap."""
from io import BytesIO
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest

import shiftsignal.io as shift_io
from shiftsignal import limits
from shiftsignal.analysis import DataProblem, analyze_launch, validate_panel, validate_portfolio

ROOT = Path(__file__).resolve().parents[1]
STREAMLIT_UPLOAD_MB = 10000  # Streamlit's transport cap only; the app adds no data limit locally


def wide_panel(locations_per_group: int, items: int = 10, periods: int = 8) -> pd.DataFrame:
    dates = pd.date_range("2026-01-05", periods=periods, freq="7D").strftime("%Y-%m-%d").to_numpy()
    names = np.array([f"Item {i}" for i in range(items - 1)] + ["New"])
    locations = np.array([f"{g}-{i}" for g in ["test", "control"] for i in range(locations_per_group)])
    groups = np.repeat(["test", "control"], locations_per_group)
    d, loc, it = (axis.ravel() for axis in np.meshgrid(np.arange(periods), np.arange(len(locations)), np.arange(items),
                                                        indexing="ij"))
    treated = (groups[loc] == "test") & (d >= periods // 2)
    units = np.where(it == items - 1, np.where(treated, 20.0, 0.0), 50.0 + loc % 7 + d - 5.0 * treated)
    return pd.DataFrame({"date": dates[d], "location": locations[loc], "group": groups[loc], "item": names[it],
                         "units": units, "price": 10.0, "unit_cost": 4.0})


def test_local_mode_accepts_input_beyond_every_demo_cap(monkeypatch):
    monkeypatch.delenv("SIGNAL_PUBLIC", raising=False)
    frame = wide_panel(1_600)  # more rows than the demo cap
    assert len(frame) > limits.DEMO_MAX_ROWS
    loaded = shift_io.read_csv(frame.to_csv(index=False).encode())
    assert len(loaded) == len(frame)
    result = analyze_launch(loaded, "2026-02-02", "New", iterations=200)
    assert result["summary"]["new_item_units"]["estimate"] == pytest.approx(20.0 * 1_600 * 4)
    many_items = wide_panel(4, items=limits.DEMO_MAX_ITEMS + 2)  # more items than the demo cap
    _, audit = validate_panel(many_items, "2026-02-02", "New")
    assert len(audit["items"]) == limits.DEMO_MAX_ITEMS + 2
    draws = analyze_launch(wide_panel(4), "2026-02-02", "New", iterations=limits.DEMO_MAX_BOOTSTRAP_DRAWS + 1)
    assert draws["config"]["iterations"] == limits.DEMO_MAX_BOOTSTRAP_DRAWS + 1
    portfolio = pd.DataFrame({"item": [f"I{i}" for i in range(limits.DEMO_MAX_ITEMS + 1)], "units": 10.0,
                              "price": 5.0, "unit_cost": 2.0, "overlap": 0.5})
    assert len(validate_portfolio(portfolio)) == limits.DEMO_MAX_ITEMS + 1
    assert limits.max_upload_bytes() is None and limits.max_rows() is None and limits.max_bootstrap_draws() is None


def test_public_demo_enforces_its_caps_with_a_demo_message(monkeypatch):
    monkeypatch.setenv("SIGNAL_PUBLIC", "1")
    frame = wide_panel(4)
    raw = frame.to_csv(index=False).encode()
    monkeypatch.setattr(limits, "DEMO_MAX_ROWS", 100)
    with pytest.raises(DataProblem, match="at most 100 rows per upload.*downloadable Shift Signal app has no built-in"):
        shift_io.read_csv(raw)
    with pytest.raises(DataProblem, match="at most 100 panel rows.*public demo only"):
        validate_panel(frame, "2026-02-02", "New")
    monkeypatch.setattr(limits, "DEMO_MAX_ROWS", 250_000)
    monkeypatch.setattr(limits, "DEMO_MAX_ITEMS", 5)
    with pytest.raises(DataProblem, match="at most 5 items"):
        validate_panel(frame, "2026-02-02", "New")
    with pytest.raises(DataProblem, match="at most 5,000 bootstrap draws"):
        analyze_launch(frame, "2026-02-02", "New", iterations=5_001)
    monkeypatch.setattr(limits, "DEMO_MAX_UPLOAD_MB", 0)
    with pytest.raises(DataProblem, match="CSV files up to 0 MB"):
        shift_io.read_csv(raw)


def test_running_out_of_memory_is_reported_plainly(monkeypatch):
    def no_memory(*args, **kwargs):
        raise MemoryError

    monkeypatch.setattr(shift_io.pd, "read_csv", no_memory)
    with pytest.raises(DataProblem, match="not enough memory on this computer"):
        shift_io.read_csv(b"item,units\nA,1\n")


def test_evidence_pack_holds_full_inputs_and_a_chunked_hash(monkeypatch):
    frame = wide_panel(4)
    frame.loc[0, "location"] = "=cmd"
    result = analyze_launch(wide_panel(4), "2026-02-02", "New", iterations=200)
    expected = hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()
    monkeypatch.setattr(shift_io, "_HASH_CHUNK_ROWS", 37)
    assert shift_io.input_sha256(frame) == expected
    with ZipFile(BytesIO(shift_io.evidence_pack("historical", frame, result, result["config"], "test"))) as archive:
        metadata = json.loads(archive.read("evidence.json"))
        exported = pd.read_csv(BytesIO(archive.read("inputs.csv")))
    assert metadata["input_sha256"] == expected and metadata["input_rows"] == len(frame)
    assert len(exported) == len(frame) and exported.loc[0, "location"] == "'=cmd"


def test_launchers_docker_and_config_share_the_suite_upload_cap():
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    windows = (ROOT / "run_app.bat").read_text(encoding="utf-8")
    macos = (ROOT / "run_app.command").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    cap = STREAMLIT_UPLOAD_MB
    assert f"maxUploadSize = {cap}" in config
    assert f"set SHIFTSIGNAL_MAX_UPLOAD_MB={cap}" in windows
    assert "--server.maxUploadSize=%SHIFTSIGNAL_MAX_UPLOAD_MB%" in windows
    assert f'--server.maxUploadSize="${{SHIFTSIGNAL_MAX_UPLOAD_MB:-{cap}}}"' in macos
    assert f"STREAMLIT_SERVER_MAX_UPLOAD_SIZE={cap}" in dockerfile
    assert "--server.maxUploadSize" not in dockerfile
