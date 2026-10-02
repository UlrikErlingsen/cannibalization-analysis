"""Local CSV parsing and reproducible, spreadsheet-safe evidence downloads."""
from __future__ import annotations

import hashlib
from io import BytesIO, StringIO
import json
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from shiftsignal import __version__
from shiftsignal.analysis import DataProblem
from shiftsignal.research import SOURCES, LIMITS


def read_csv(payload: bytes) -> pd.DataFrame:
    if len(payload) > 20 * 1024 * 1024:
        raise DataProblem("Use a CSV file smaller than 20 MB.")
    try:
        text = payload.decode("utf-8-sig")
        frame = pd.read_csv(StringIO(text), sep=None, engine="python")
    except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
        raise DataProblem("Could not read the CSV. Export as UTF-8 CSV with a header and decimal points.") from exc
    if len(frame) > 250_000:
        raise DataProblem("Use at most 250,000 rows per upload.")
    if frame.empty:
        raise DataProblem("The CSV has no data rows.")
    return frame


def csv_bytes(frame: pd.DataFrame) -> bytes:
    safe = frame.copy()
    for column in safe.select_dtypes(include=["object", "string"]).columns:
        safe[column] = safe[column].map(
            lambda x: "'" + x if isinstance(x, str) and x.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else x
        )
    return safe.to_csv(index=False).encode("utf-8-sig")


def evidence_pack(kind: str, inputs: pd.DataFrame, result: dict, config: dict, source: str) -> bytes:
    """Include only the explicitly supplied study inputs, never filesystem metadata."""
    output = BytesIO()
    metadata = {"app": "Shift Signal", "version": __version__, "analysis_type": kind,
                "source": source, "config": config,
                "input_sha256": hashlib.sha256(inputs.to_csv(index=False).encode()).hexdigest(),
                "summary": result["summary"], "warnings": result.get("warnings", []),
                "audit": result.get("audit"), "placebo": result.get("placebo"),
                "sources": SOURCES, "limits": LIMITS,
                "csv_note": "Text starting with formula characters is prefixed with an apostrophe in exported CSV files."}
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("evidence.json", json.dumps(metadata, indent=2, ensure_ascii=False, allow_nan=False))
        archive.writestr("inputs.csv", csv_bytes(inputs))
        for name in ["items", "series", "descriptive", "sensitivity"]:
            if isinstance(result.get(name), pd.DataFrame):
                archive.writestr(f"{name}.csv", csv_bytes(result[name]))
    return output.getvalue()
