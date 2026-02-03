from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


IssueLevel = Literal["info", "warning", "critical"]


class DataQualityIssue(BaseModel):
    id: str
    level: IssueLevel
    message: str
    affected_columns: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)


class DataQualityReport(BaseModel):
    company_id: str
    dataset: str
    generated_at: str

    row_count: int
    column_count: int

    date_column: Optional[str] = None
    date_min: Optional[str] = None
    date_max: Optional[str] = None

    missing_values: Dict[str, Dict[str, Any]]
    invalid_values: Dict[str, Dict[str, Any]]
    duplicates: Dict[str, Any]
    outliers: Dict[str, Dict[str, Any]]

    quality_score: int
    issues: List[DataQualityIssue]


def _infer_date_column(df: pd.DataFrame) -> Optional[str]:
    candidates = ["OrderDate", "Sale_Date", "Order_Date", "Date", "order_date", "date"]
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _safe_to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _iqr_outliers(values: pd.Series) -> Dict[str, Any]:
    values = values.dropna()
    if values.empty:
        return {"count": 0}

    q1 = float(values.quantile(0.25))
    q3 = float(values.quantile(0.75))
    iqr = q3 - q1
    if iqr == 0:
        return {"count": 0, "q1": q1, "q3": q3, "lower": q1, "upper": q3}

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    out = values[(values < lower) | (values > upper)]
    return {
        "count": int(out.shape[0]),
        "q1": round(q1, 6),
        "q3": round(q3, 6),
        "lower": round(float(lower), 6),
        "upper": round(float(upper), 6),
    }


def generate_data_quality_report(
    *,
    company_id: str,
    dataset: str,
    df: pd.DataFrame,
    max_columns: int = 60,
) -> DataQualityReport:
    """Generate a deterministic data-quality report for a dataset.

    Detects:
    - missing values
    - invalid types (date parsing, numeric coercion)
    - date inconsistencies (future dates, unparsable)
    - duplicates
    - outliers (IQR) for key numeric columns
    """

    if df is None or df.empty:
        return DataQualityReport(
            company_id=company_id,
            dataset=dataset,
            generated_at=datetime.now(timezone.utc).isoformat(),
            row_count=0,
            column_count=int(0 if df is None else df.shape[1]),
            date_column=None,
            date_min=None,
            date_max=None,
            missing_values={},
            invalid_values={},
            duplicates={"duplicate_rows": 0, "duplicate_pct": 0.0},
            outliers={},
            quality_score=0,
            issues=[
                DataQualityIssue(
                    id="no_data",
                    level="critical",
                    message="No data available to analyze.",
                    affected_columns=[],
                    metrics={},
                )
            ],
        )

    # Limit column processing to keep payload sane
    cols = list(df.columns)[: max_columns]
    working = df[cols].copy()

    row_count = int(len(working))
    col_count = int(len(cols))

    # Missing values
    missing_values: Dict[str, Dict[str, Any]] = {}
    for c in cols:
        missing_count = int(working[c].isna().sum())
        if missing_count:
            missing_values[c] = {
                "missing_count": missing_count,
                "missing_pct": round(missing_count / row_count * 100.0, 2),
            }

    # Invalid values: date parsing + numeric coercion for common numeric columns
    invalid_values: Dict[str, Dict[str, Any]] = {}

    date_col = _infer_date_column(working)
    date_min = date_max = None
    if date_col:
        # Normalize to tz-naive timestamps for safe comparisons
        parsed = pd.to_datetime(working[date_col], errors="coerce", utc=True).dt.tz_convert(None)
        invalid_dates = int(parsed.isna().sum())
        if invalid_dates:
            invalid_values[date_col] = {
                "invalid_count": invalid_dates,
                "invalid_pct": round(invalid_dates / row_count * 100.0, 2),
                "type": "date",
            }
        valid = parsed.dropna()
        if not valid.empty:
            date_min = valid.min().isoformat()
            date_max = valid.max().isoformat()

        # Future dates
        now = pd.Timestamp.now()
        future = int((valid > now).sum()) if not valid.empty else 0
        if future:
            invalid_values[f"{date_col}__future"] = {
                "invalid_count": future,
                "invalid_pct": round(future / row_count * 100.0, 2),
                "type": "future_date",
            }

    numeric_candidates = [
        "TotalPrice",
        "Price",
        "Sales_Amount",
        "SalesAmount",
        "Revenue",
        "Amount",
        "amount",
        "price",
        "Quantity",
        "Quantity_Sold",
        "Unit_Price",
    ]

    for c in cols:
        if c in numeric_candidates:
            coerced = _safe_to_numeric(working[c])
            invalid = int(coerced.isna().sum()) - int(working[c].isna().sum())
            if invalid > 0:
                invalid_values[c] = {
                    "invalid_count": invalid,
                    "invalid_pct": round(invalid / row_count * 100.0, 2),
                    "type": "numeric",
                }

    # Duplicates
    dup_rows = int(working.duplicated().sum())
    duplicates = {
        "duplicate_rows": dup_rows,
        "duplicate_pct": round(dup_rows / row_count * 100.0, 2),
    }

    # Outliers (IQR) for key numeric columns available
    outliers: Dict[str, Dict[str, Any]] = {}
    for c in ["TotalPrice", "Revenue", "Amount", "Price"]:
        if c in cols:
            values = _safe_to_numeric(working[c])
            outliers[c] = _iqr_outliers(values)

    # Issues + quality score
    issues: List[DataQualityIssue] = []

    total_missing = sum(v["missing_count"] for v in missing_values.values())
    total_invalid = sum(v.get("invalid_count", 0) for v in invalid_values.values())
    total_outliers = sum(v.get("count", 0) for v in outliers.values())

    missing_pct = (total_missing / (row_count * col_count)) * 100.0 if row_count and col_count else 100.0

    if missing_pct >= 5:
        issues.append(
            DataQualityIssue(
                id="missing_values",
                level="warning" if missing_pct < 15 else "critical",
                message=f"Missing values are present across the dataset ({missing_pct:.2f}% of cells).",
                affected_columns=sorted(list(missing_values.keys()))[:10],
                metrics={"missing_cell_pct": round(missing_pct, 2), "missing_cells": total_missing},
            )
        )

    if total_invalid > 0:
        issues.append(
            DataQualityIssue(
                id="invalid_values",
                level="warning" if total_invalid < (0.02 * row_count) else "critical",
                message="Some values could not be parsed to the expected types (dates/numbers).",
                affected_columns=sorted(list({k.split("__")[0] for k in invalid_values.keys()}))[:10],
                metrics={"invalid_values": total_invalid},
            )
        )

    if dup_rows > 0:
        issues.append(
            DataQualityIssue(
                id="duplicates",
                level="info" if duplicates["duplicate_pct"] < 2 else "warning",
                message=f"Duplicate rows detected ({duplicates['duplicate_pct']}%).",
                affected_columns=[],
                metrics=duplicates,
            )
        )

    if total_outliers > 0:
        issues.append(
            DataQualityIssue(
                id="outliers",
                level="info" if total_outliers < (0.01 * row_count) else "warning",
                message="Outliers detected in key numeric fields (IQR method).",
                affected_columns=[k for k, v in outliers.items() if v.get("count", 0) > 0],
                metrics={"outlier_rows": total_outliers},
            )
        )

    if not issues:
        issues.append(
            DataQualityIssue(
                id="healthy",
                level="info",
                message="No major data quality issues detected.",
                affected_columns=[],
                metrics={},
            )
        )

    # Deterministic score: start at 100, subtract penalties
    score = 100
    score -= int(min(60, missing_pct * 4))
    score -= int(min(25, (total_invalid / max(1, row_count)) * 200))
    score -= int(min(10, duplicates["duplicate_pct"] * 2))
    score -= int(min(20, (total_outliers / max(1, row_count)) * 200))
    score = max(0, min(100, score))

    return DataQualityReport(
        company_id=company_id,
        dataset=dataset,
        generated_at=datetime.now(timezone.utc).isoformat(),
        row_count=row_count,
        column_count=col_count,
        date_column=date_col,
        date_min=date_min,
        date_max=date_max,
        missing_values=missing_values,
        invalid_values=invalid_values,
        duplicates=duplicates,
        outliers=outliers,
        quality_score=score,
        issues=issues,
    )
