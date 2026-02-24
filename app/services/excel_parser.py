"""Excel parsing utilities with robust header detection and schema inference.

This module focuses on durable Excel parsing for production: better error
handling, logging, improved header detection heuristics, hidden column
detection, and conservative schema inference.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import HTTPException
from openpyxl import load_workbook

logger = logging.getLogger(__name__)


# -----------------------------
# Utilities
# -----------------------------


def _normalize_col(name: Any) -> str:
    if name is None:
        return ""
    s = str(name).strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^0-9a-zA-Z_]+", "", s)
    s = re.sub(r"_+", "_", s)
    s = s.strip("_")
    s = s.lower()
    if not s:
        return ""
    if s[0].isdigit():
        s = f"c_{s}"
    return s


def _ensure_path(path: Any) -> Path:
    p = Path(path)
    if not p.exists():
        logger.debug("Path does not exist: %s", p)
        raise HTTPException(status_code=400, detail="File not found")
    return p


def _read_single_sheet(path: Any, sheet_name: Optional[str] = None, header: Optional[int] = None) -> pd.DataFrame:
    p = _ensure_path(path)

    try:
        # Validate sheet exists when a name is provided
        if sheet_name is not None:
            try:
                wb = load_workbook(filename=str(p), read_only=True, data_only=True)
                if sheet_name not in wb.sheetnames:
                    wb.close()
                    raise HTTPException(status_code=400, detail=f"Sheet '{sheet_name}' not found")
                wb.close()
            except HTTPException:
                raise
            except Exception as e:  # pragma: no cover - IO/runtime issues
                logger.exception("Error validating workbook: %s", e)
                raise HTTPException(status_code=400, detail=f"Failed to open workbook: {e}")

        df = pd.read_excel(
            str(p),
            sheet_name=sheet_name,
            header=header,
            engine="openpyxl",
        )
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover - pandas/read errors
        logger.exception("Failed to read Excel file: %s", e)
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {e}")

    if isinstance(df, dict):
        if not df:
            raise HTTPException(status_code=400, detail="Excel file contains no sheets")
        df = next(iter(df.values()))

    if df is None or getattr(df, "empty", True):
        raise HTTPException(status_code=400, detail="Excel sheet is empty")

    return df


# -----------------------------
# Smart Header Detection
# -----------------------------


def _detect_header_row(path: Any, sheet_name: Optional[str] = None, max_scan_rows: int = 20) -> int:
    """Detect the most likely header row index (0-based) within the first
    `max_scan_rows` rows.
    """
    df_raw = _read_single_sheet(path, sheet_name=sheet_name, header=None)
    df_raw = df_raw.head(max_scan_rows)
    df_raw = df_raw.dropna(how="all")

    if df_raw.empty:
        raise HTTPException(status_code=400, detail="Excel contains only empty rows")

    best_score = float("-inf")
    best_index = 0

    for idx, row in df_raw.iterrows():
        values = row.dropna()
        if values.empty:
            continue

        # counts
        text_count = sum(isinstance(v, str) for v in values)
        numeric_count = sum(isinstance(v, (int, float)) for v in values)
        nonempty_ratio = len(values) / max(1, len(row))

        # uniqueness among string values (headers tend to be unique)
        str_vals = [str(v).strip() for v in values if isinstance(v, str) and str(v).strip()]
        unique_ratio = (len(set(str_vals)) / len(str_vals)) if str_vals else 0.0

        # Basic heuristic: prefer rows with many strings, high uniqueness and many non-empty cells
        score = (text_count - numeric_count) + (unique_ratio * 2.0) + (nonempty_ratio * 0.5)

        if score > best_score:
            best_score = score
            best_index = int(idx)

    return int(best_index)


# -----------------------------
# Hidden Columns Detection
# -----------------------------


def _hidden_columns(path: Any, sheet_name: Optional[str] = None) -> List[int]:
    p = Path(path)
    try:
        wb = load_workbook(filename=str(p), read_only=True, data_only=True)
        ws = wb[sheet_name] if sheet_name else wb.active

        hidden = []

        def col_letter_to_index(letter: str) -> int:
            idx = 0
            for ch in letter.upper():
                if "A" <= ch <= "Z":
                    idx = idx * 26 + (ord(ch) - ord("A") + 1)
            return idx - 1

        # column_dimensions keys are column letters (e.g., 'A', 'B', 'AA')
        for col_letter, col_dim in ws.column_dimensions.items():
            try:
                if getattr(col_dim, "hidden", False):
                    hidden.append(col_letter_to_index(col_letter))
            except Exception:
                continue

        wb.close()
        return hidden
    except Exception as e:  # pragma: no cover - IO/runtime
        logger.debug("Could not determine hidden columns: %s", e)
        return []


# -----------------------------
# Schema Inference
# -----------------------------


def _infer_schema(df: pd.DataFrame) -> Dict[str, str]:
    schema: Dict[str, str] = {}
    for col in df.columns:
        series = df[col].dropna()
        # sample up to 200 non-null values to infer
        sample = series.iloc[:200]

        if sample.empty:
            schema[col] = "string"
            continue

        if pd.api.types.is_bool_dtype(sample) or sample.astype(str).str.lower().isin(["true", "false", "0", "1"]).all():
            schema[col] = "boolean"
        elif pd.api.types.is_integer_dtype(sample) or pd.api.types.is_float_dtype(sample):
            schema[col] = "number"
        elif pd.api.types.is_datetime64_any_dtype(sample):
            schema[col] = "datetime"
        else:
            # fallback: try parsing datetimes on sample
            try:
                parsed = pd.to_datetime(sample, errors="coerce")
                if parsed.notna().sum() / max(1, len(parsed)) > 0.8:
                    schema[col] = "datetime"
                    continue
            except Exception:
                pass
            schema[col] = "string"

    return schema


# -----------------------------
# Main Parser
# -----------------------------


def parse_excel(
    path: Any,
    sheet_name: Optional[str] = None,
    required_columns: Optional[List[str]] = None,
    max_scan_rows: int = 20,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Parse an Excel file and return a cleaned DataFrame plus metadata.

    - Detects header row automatically within the first `max_scan_rows` rows.
    - Normalizes column names to safe identifiers.
    - Removes empty rows/columns and hidden columns.
    - Infers a simple schema for each column.
    """
    p = _ensure_path(path)

    header_row = _detect_header_row(p, sheet_name=sheet_name, max_scan_rows=max_scan_rows)
    df = _read_single_sheet(p, sheet_name=sheet_name, header=header_row)

    # Drop completely empty rows/columns
    df = df.dropna(axis=0, how="all")
    df = df.dropna(axis=1, how="all")

    if df.empty:
        raise HTTPException(status_code=400, detail="No usable data found")

    # Normalize columns
    new_cols: List[str] = []
    for idx, col in enumerate(df.columns):
        nc = _normalize_col(col)
        if not nc:
            nc = f"col_{idx}"
        new_cols.append(nc)

    df.columns = new_cols

    # Remove hidden columns if any
    hidden_idx = _hidden_columns(p, sheet_name)
    if hidden_idx:
        cols_to_drop = [df.columns[i] for i in hidden_idx if 0 <= i < len(df.columns)]
        if cols_to_drop:
            logger.debug("Dropping hidden columns: %s", cols_to_drop)
            df = df.drop(columns=cols_to_drop, errors="ignore")

    # Normalize missing values to None (JSON-friendly)
    df = df.where(pd.notnull(df), None)

    # Trim string fields
    for col in df.select_dtypes(include=[object]).columns:
        df[col] = df[col].apply(lambda v: v.strip() if isinstance(v, str) else v)

    # Required column check (original names preserved in required_columns param)
    missing: List[str] = []
    if required_columns:
        norm_required = [_normalize_col(c) for c in required_columns]
        for orig, norm in zip(required_columns, norm_required):
            if norm not in df.columns:
                missing.append(orig)

    schema = _infer_schema(df)

    meta: Dict[str, Any] = {
        "header_row": header_row,
        "columns": list(df.columns),
        "row_count": len(df),
        "schema": schema,
        "missing_required": missing,
    }

    return df, meta


__all__ = ["parse_excel", "_detect_header_row", "_hidden_columns"]
