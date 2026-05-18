from __future__ import annotations

from pathlib import Path
from typing import Optional


def _sanitize_segment(value: object, *, prefix: str, fallback: str) -> str:
    raw = str(value if value is not None else "").strip()
    if not raw:
        return f"{prefix}_{fallback}"
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in raw)
    safe = safe.strip("_") or fallback
    return f"{prefix}_{safe}"


def company_dir_name(company_id: object) -> str:
    return _sanitize_segment(company_id, prefix="company", fallback="unknown")


def branch_dir_name(branch_id: object) -> str:
    return _sanitize_segment(branch_id, prefix="branch", fallback="unknown")


def scope_dir_name(branch_id: Optional[object]) -> str:
    return branch_dir_name(branch_id) if branch_id is not None else "company_scope"


def tenant_scope_dir(data_root: Path, company_id: object, branch_id: Optional[object] = None) -> Path:
    return Path(data_root) / company_dir_name(company_id) / scope_dir_name(branch_id)


def tenant_uploads_dir(data_root: Path, company_id: object, branch_id: Optional[object] = None) -> Path:
    return tenant_scope_dir(data_root, company_id, branch_id) / "uploads"


def tenant_outputs_dir(data_root: Path, company_id: object, branch_id: Optional[object] = None) -> Path:
    return tenant_scope_dir(data_root, company_id, branch_id) / "outputs"


def tenant_forecasts_dir(data_root: Path, company_id: object, branch_id: Optional[object] = None) -> Path:
    return tenant_scope_dir(data_root, company_id, branch_id) / "forecasts"


def tenant_segmentation_dir(data_root: Path, company_id: object, branch_id: Optional[object] = None) -> Path:
    return tenant_scope_dir(data_root, company_id, branch_id) / "segmentation"


def tenant_sentiment_dir(data_root: Path, company_id: object, branch_id: Optional[object] = None) -> Path:
    return tenant_scope_dir(data_root, company_id, branch_id) / "sentiment"


def tenant_recommendations_dir(data_root: Path, company_id: object, branch_id: Optional[object] = None) -> Path:
    return tenant_scope_dir(data_root, company_id, branch_id) / "recommendations"


def tenant_notifications_dir(data_root: Path, company_id: object, branch_id: Optional[object] = None) -> Path:
    return tenant_scope_dir(data_root, company_id, branch_id) / "notifications"


def ensure_tenant_directories(data_root: Path, company_id: object, branch_id: Optional[object] = None) -> dict[str, Path]:
    directories = {
        "scope": tenant_scope_dir(data_root, company_id, branch_id),
        "uploads": tenant_uploads_dir(data_root, company_id, branch_id),
        "outputs": tenant_outputs_dir(data_root, company_id, branch_id),
        "forecasts": tenant_forecasts_dir(data_root, company_id, branch_id),
        "segmentation": tenant_segmentation_dir(data_root, company_id, branch_id),
        "sentiment": tenant_sentiment_dir(data_root, company_id, branch_id),
        "recommendations": tenant_recommendations_dir(data_root, company_id, branch_id),
        "notifications": tenant_notifications_dir(data_root, company_id, branch_id),
    }
    for path in directories.values():
        path.mkdir(parents=True, exist_ok=True)
    return directories


def derived_output_paths(data_root: Path, company_id: object, branch_id: Optional[object] = None) -> dict[str, Path]:
    directories = ensure_tenant_directories(data_root, company_id, branch_id)
    return {
        "forecast.csv": directories["scope"] / "forecast.csv",
        "merged_data.csv": directories["outputs"] / "merged_data.csv",
        "cleaned_dataset.csv": directories["outputs"] / "cleaned_dataset.csv",
        "rfm_table.csv": directories["segmentation"] / "rfm_table.csv",
        "product_recommendations.csv": directories["recommendations"] / "product_recommendations.csv",
        "sentiment_results.csv": directories["sentiment"] / "sentiment_results.csv",
        "sales_forecast.csv": directories["forecasts"] / "sales_forecast.csv",
        "sales_forecast_future.csv": directories["forecasts"] / "sales_forecast_future.csv",
        "eda_report.json": directories["outputs"] / "eda_report.json",
        "kpis.csv": directories["outputs"] / "kpis.csv",
        "monthly_sales.csv": directories["outputs"] / "monthly_sales.csv",
        "sales_by_city.csv": directories["outputs"] / "sales_by_city.csv",
        "top_products.csv": directories["outputs"] / "top_products.csv",
        "clv_analysis.csv": directories["outputs"] / "clv_analysis.csv",
        "clv_insights.json": directories["outputs"] / "clv_insights.json",
    }