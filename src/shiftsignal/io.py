"""Local CSV parsing and reproducible, spreadsheet-safe evidence downloads."""
from __future__ import annotations

import csv
import hashlib
from io import BytesIO
import json
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pandas as pd

from shiftsignal import __version__, limits
from shiftsignal.analysis import DataProblem
from shiftsignal.research import SOURCES, LIMITS

_HASH_CHUNK_ROWS = 250_000
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _delimiter(payload: bytes) -> tuple[str, bool]:
    """Sniff the delimiter from the header line, as pandas' sep=None does, without the slow Python parser."""
    first_line = payload[:65536].decode("utf-8-sig", errors="ignore").splitlines()[:1]
    try:
        dialect = csv.Sniffer().sniff(first_line[0] if first_line else "")
    except csv.Error:
        return ",", False
    return dialect.delimiter, bool(dialect.skipinitialspace)


def read_csv(payload: bytes) -> pd.DataFrame:
    """Read a UTF-8 CSV. No size or row limit locally; a public demo applies :mod:`shiftsignal.limits`."""
    byte_cap = limits.max_upload_bytes()
    if byte_cap is not None and len(payload) > byte_cap:
        raise DataProblem(limits.demo_limit(f"The public demo accepts CSV files up to {limits.DEMO_MAX_UPLOAD_MB} MB."))
    row_cap = limits.max_rows()
    delimiter, skip_space = _delimiter(payload)
    try:
        # The C parser reads a few million rows in seconds; on the demo, parsing stops one row past the cap.
        frame = pd.read_csv(BytesIO(payload), sep=delimiter, skipinitialspace=skip_space, encoding="utf-8-sig",
                            nrows=None if row_cap is None else row_cap + 1)
    except MemoryError as exc:
        raise DataProblem(limits.MEMORY_MESSAGE) from exc
    except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
        raise DataProblem("Could not read the CSV. Export as UTF-8 CSV with a header and decimal points.") from exc
    if row_cap is not None and len(frame) > row_cap:
        raise DataProblem(limits.demo_limit(f"The public demo accepts at most {row_cap:,} rows per upload."))
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


def _neutralize(value: object) -> object:
    if isinstance(value, str) and value.lstrip().startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def csv_bytes(frame: pd.DataFrame) -> bytes:
    safe = frame.copy()
    for column in safe.select_dtypes(include=["object", "string"]).columns:
        # Neutralize each distinct value once; panels repeat a few labels millions of times.
        codes, uniques = pd.factorize(safe[column], use_na_sentinel=True)
        cleaned = np.array([_neutralize(value) for value in uniques] + [None], dtype=object)
        values = cleaned[codes]
        missing = codes < 0
        if missing.any():
            values[missing] = safe[column].to_numpy(dtype=object)[missing]
        safe[column] = values
    return safe.to_csv(index=False).encode("utf-8-sig")


def evidence_pack(kind: str, inputs: pd.DataFrame, result: dict, config: dict, source: str,
                  *, input_digest: str | None = None) -> bytes:
    """Include only the explicitly supplied study inputs, never filesystem metadata.

    The pack always contains the full input table. ``input_digest`` lets a caller reuse an already computed
    :func:`input_sha256` of a large table.
    """
    output = BytesIO()
    metadata = {"app": "Shift Signal", "version": __version__, "analysis_type": kind,
                "source": source, "config": config,
                "input_sha256": input_digest or input_sha256(inputs),
                "input_rows": int(len(inputs)),
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
