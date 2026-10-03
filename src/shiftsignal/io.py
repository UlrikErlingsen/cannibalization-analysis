"""Local CSV parsing and reproducible, spreadsheet-safe evidence downloads."""
from __future__ import annotations

import csv
import hashlib
from io import BytesIO
import json
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from shiftsignal import __version__
from shiftsignal.analysis import MAX_ROWS, DataProblem
from shiftsignal.research import SOURCES, LIMITS

# One cap for the whole app: the launchers, Docker image and .streamlit/config.toml all default to the same 1000 MB.
MAX_UPLOAD_MB = 1000
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
# Evidence packs copy the input table up to this many rows; larger inputs are identified by their SHA-256 instead.
EVIDENCE_INPUT_MAX_ROWS = 250_000
_HASH_CHUNK_ROWS = 250_000


def _delimiter(payload: bytes) -> tuple[str, bool]:
    """Sniff the delimiter from the header line, as pandas' sep=None does, without the slow Python parser."""
    first_line = payload[:65536].decode("utf-8-sig", errors="ignore").splitlines()[:1]
    try:
        dialect = csv.Sniffer().sniff(first_line[0] if first_line else "")
    except csv.Error:
        return ",", False
    return dialect.delimiter, bool(dialect.skipinitialspace)


def read_csv(payload: bytes) -> pd.DataFrame:
    if len(payload) > MAX_UPLOAD_BYTES:
        raise DataProblem(f"Use a CSV file smaller than {MAX_UPLOAD_MB:,} MB.")
    delimiter, skip_space = _delimiter(payload)
    try:
        # The C parser reads a few million rows in seconds; parsing stops one row past the limit.
        frame = pd.read_csv(BytesIO(payload), sep=delimiter, skipinitialspace=skip_space, encoding="utf-8-sig",
                            nrows=MAX_ROWS + 1)
    except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
        raise DataProblem("Could not read the CSV. Export as UTF-8 CSV with a header and decimal points.") from exc
    if len(frame) > MAX_ROWS:
        raise DataProblem(
            f"Use at most {MAX_ROWS:,} rows per upload. Aggregate to weekly periods or fewer items, then upload again."
        )
    if frame.empty:
        raise DataProblem("The CSV has no data rows.")
    return frame


def input_sha256(frame: pd.DataFrame) -> str:
    """SHA-256 of ``frame.to_csv(index=False)``, streamed in chunks so a large table is never serialized at once."""
    digest = hashlib.sha256()
    for start in range(0, max(len(frame), 1), _HASH_CHUNK_ROWS):
        chunk = frame.iloc[start:start + _HASH_CHUNK_ROWS]
        digest.update(chunk.to_csv(index=False, header=start == 0).encode())
    return digest.hexdigest()


def csv_bytes(frame: pd.DataFrame) -> bytes:
    safe = frame.copy()
    for column in safe.select_dtypes(include=["object", "string"]).columns:
        safe[column] = safe[column].map(
            lambda x: "'" + x if isinstance(x, str) and x.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else x
        )
    return safe.to_csv(index=False).encode("utf-8-sig")


def evidence_pack(kind: str, inputs: pd.DataFrame, result: dict, config: dict, source: str,
                  *, input_digest: str | None = None) -> bytes:
    """Include only the explicitly supplied study inputs, never filesystem metadata.

    Inputs above ``EVIDENCE_INPUT_MAX_ROWS`` rows are not copied into the ZIP; ``evidence.json`` says so and keeps
    their SHA-256, so the pack stays small and the source file can still be matched exactly.
    """
    output = BytesIO()
    include_inputs = len(inputs) <= EVIDENCE_INPUT_MAX_ROWS
    metadata = {"app": "Shift Signal", "version": __version__, "analysis_type": kind,
                "source": source, "config": config,
                "input_sha256": input_digest or input_sha256(inputs),
                "input_rows": int(len(inputs)),
                "summary": result["summary"], "warnings": result.get("warnings", []),
                "audit": result.get("audit"), "placebo": result.get("placebo"),
                "sources": SOURCES, "limits": LIMITS,
                "csv_note": "Text starting with formula characters is prefixed with an apostrophe in exported CSV files."}
    if not include_inputs:
        metadata["inputs_note"] = (
            f"The {len(inputs):,}-row input table is not copied into this pack (the limit is "
            f"{EVIDENCE_INPUT_MAX_ROWS:,} rows). Keep the source file; input_sha256 identifies it exactly "
            "(SHA-256 of the loaded table written as CSV without an index)."
        )
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("evidence.json", json.dumps(metadata, indent=2, ensure_ascii=False, allow_nan=False))
        if include_inputs:
            archive.writestr("inputs.csv", csv_bytes(inputs))
        for name in ["items", "series", "descriptive", "sensitivity"]:
            if isinstance(result.get(name), pd.DataFrame):
                archive.writestr(f"{name}.csv", csv_bytes(result[name]))
    return output.getvalue()
