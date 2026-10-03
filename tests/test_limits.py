"""Large-data limits: the 1000 MB / 5,000,000-row caps, their messages, and the launchers that share them."""
from io import BytesIO
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest

import shiftsignal.io as shift_io
from shiftsignal.analysis import MAX_ROWS, DataProblem, analyze_launch, validate_panel

ROOT = Path(__file__).resolve().parents[1]


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


def test_panels_above_the_old_250000_row_limit_are_analyzed():
    frame = wide_panel(1_600)
    assert len(frame) > 250_000
    loaded = shift_io.read_csv(frame.to_csv(index=False).encode())
    assert len(loaded) == len(frame)
    _, audit = validate_panel(loaded, "2026-02-02", "New")
    assert audit["test_locations"] == audit["control_locations"] == 1_600
    result = analyze_launch(loaded, "2026-02-02", "New", iterations=200)
    assert result["summary"]["new_item_units"]["estimate"] == pytest.approx(20.0 * 1_600 * 4)
    assert MAX_ROWS == 5_000_000
    assert shift_io.MAX_UPLOAD_BYTES == shift_io.MAX_UPLOAD_MB * 1024 * 1024 == 1000 * 1024 * 1024


def test_row_and_size_limits_name_the_new_caps(monkeypatch):
    raw = wide_panel(4).to_csv(index=False).encode()
    monkeypatch.setattr(shift_io, "MAX_ROWS", 100)
    with pytest.raises(DataProblem, match="at most 100 rows per upload"):
        shift_io.read_csv(raw)
    monkeypatch.setattr(shift_io, "MAX_UPLOAD_BYTES", 10)
    with pytest.raises(DataProblem, match="smaller than 1,000 MB"):
        shift_io.read_csv(raw)


def test_large_inputs_are_hashed_not_copied_into_the_evidence_pack(monkeypatch):
    frame = wide_panel(4)
    result = analyze_launch(frame, "2026-02-02", "New", iterations=200)
    expected = hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()
    monkeypatch.setattr(shift_io, "_HASH_CHUNK_ROWS", 37)
    assert shift_io.input_sha256(frame) == expected
    monkeypatch.setattr(shift_io, "EVIDENCE_INPUT_MAX_ROWS", 10)
    with ZipFile(BytesIO(shift_io.evidence_pack("historical", frame, result, result["config"], "test"))) as archive:
        metadata = json.loads(archive.read("evidence.json"))
        assert "inputs.csv" not in archive.namelist()
        assert "items.csv" in archive.namelist()
    assert metadata["input_sha256"] == expected
    assert metadata["input_rows"] == len(frame)
    assert "not copied into this pack" in metadata["inputs_note"]


def test_launchers_docker_and_config_share_the_1000_mb_cap():
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    windows = (ROOT / "run_app.bat").read_text(encoding="utf-8")
    macos = (ROOT / "run_app.command").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    cap = shift_io.MAX_UPLOAD_MB
    assert f"maxUploadSize = {cap}" in config
    assert f"set SHIFTSIGNAL_MAX_UPLOAD_MB={cap}" in windows
    assert "--server.maxUploadSize=%SHIFTSIGNAL_MAX_UPLOAD_MB%" in windows
    assert f'--server.maxUploadSize="${{SHIFTSIGNAL_MAX_UPLOAD_MB:-{cap}}}"' in macos
    assert f"STREAMLIT_SERVER_MAX_UPLOAD_SIZE={cap}" in dockerfile
    assert "--server.maxUploadSize" not in dockerfile
