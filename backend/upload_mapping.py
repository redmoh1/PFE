from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence
from uuid import uuid4

import pandas as pd
from fastapi import HTTPException

from backend.database.connection import SessionLocal, init_db as init_sqlalchemy_db
from backend.database.models import PendingDatasetUpload, UploadMappingProfile

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    from difflib import SequenceMatcher

try:
    from src.tenant_paths import ensure_tenant_directories
except ImportError:
    ensure_tenant_directories = None


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PREVIEW_ROW_LIMIT = 8
PENDING_UPLOAD_TTL_HOURS = 24
FUZZY_MATCH_THRESHOLD = 72.0


@dataclass(frozen=True)
class MappingFieldDefinition:
    key: str
    label: str
    required: bool
    canonical_column: str
    aliases: Sequence[str]
    description: str

    @property
    def search_terms(self) -> List[str]:
        return [self.label, self.canonical_column, *self.aliases]


DATASET_FIELD_DEFINITIONS: Dict[str, List[MappingFieldDefinition]] = {
    "sales": [
        MappingFieldDefinition(
            key="order_date",
            label="Date",
            required=True,
            canonical_column="OrderDate",
            aliases=["order date", "sale date", "transaction date", "invoice date", "purchase date", "date"],
            description="Required for forecasting and time-based analytics.",
        ),
        MappingFieldDefinition(
            key="total_price",
            label="Sales Amount",
            required=True,
            canonical_column="TotalPrice",
            aliases=["total sales", "sales amount", "total amount", "revenue", "sales", "amount", "order total", "line total"],
            description="Required unless you provide both Unit Price and Quantity.",
        ),
        MappingFieldDefinition(
            key="product",
            label="Product Name",
            required=True,
            canonical_column="ProductID",
            aliases=["product", "product name", "item", "item name", "description", "sku", "stock code"],
            description="Required for product analytics and recommendations.",
        ),
        MappingFieldDefinition(
            key="customer_id",
            label="Customer ID",
            required=False,
            canonical_column="CustomerID",
            aliases=["customer id", "customer_id", "customer number", "client id", "buyer id", "user id"],
            description="Optional, but enables RFM segmentation directly from sales data.",
        ),
        MappingFieldDefinition(
            key="order_id",
            label="Order ID",
            required=False,
            canonical_column="OrderID",
            aliases=["order id", "invoice no", "transaction id", "receipt"],
            description="Optional. If omitted, the system will generate synthetic order IDs.",
        ),
        MappingFieldDefinition(
            key="city",
            label="Customer City",
            required=False,
            canonical_column="City",
            aliases=["city", "location", "region", "state", "market"],
            description="Optional geographic dimension for branch and city analytics.",
        ),
        MappingFieldDefinition(
            key="quantity",
            label="Quantity",
            required=False,
            canonical_column="Quantity_Sold",
            aliases=["quantity", "qty", "units", "count", "number of items"],
            description="Optional. Pair with Unit Price when Sales Amount is not provided.",
        ),
        MappingFieldDefinition(
            key="unit_price",
            label="Unit Price",
            required=False,
            canonical_column="Unit_Price",
            aliases=["unit price", "price", "item price", "price per unit", "cost"],
            description="Optional. Pair with Quantity when Sales Amount is not provided.",
        ),
    ],
    "customers": [
        MappingFieldDefinition(
            key="customer_id",
            label="Customer ID",
            required=True,
            canonical_column="CustomerID",
            aliases=["customer id", "customer_id", "customer number", "client id", "buyer id", "user id"],
            description="Required for joining customer records with sales history.",
        ),
        MappingFieldDefinition(
            key="customer_name",
            label="Customer Name",
            required=False,
            canonical_column="CustomerName",
            aliases=["customer name", "client name", "full name", "name"],
            description="Optional display name for CRM and segmentation views.",
        ),
        MappingFieldDefinition(
            key="city",
            label="Customer City",
            required=False,
            canonical_column="City",
            aliases=["city", "location", "region", "state"],
            description="Optional location field for geographic analysis.",
        ),
    ],
    "reviews": [
        MappingFieldDefinition(
            key="review_text",
            label="Review Text",
            required=True,
            canonical_column="ReviewText",
            aliases=["review text", "review", "comment", "feedback", "text"],
            description="Required for customer feedback and sentiment analysis.",
        ),
        MappingFieldDefinition(
            key="rating",
            label="Rating",
            required=False,
            canonical_column="Rating",
            aliases=["rating", "score", "stars", "rate"],
            description="Optional numeric score to enrich sentiment results.",
        ),
        MappingFieldDefinition(
            key="review_date",
            label="Review Date",
            required=False,
            canonical_column="ReviewDate",
            aliases=["review date", "date", "submitted at", "created at"],
            description="Optional date for review trend analysis.",
        ),
        MappingFieldDefinition(
            key="customer_id",
            label="Customer ID",
            required=False,
            canonical_column="CustomerID",
            aliases=["customer id", "customer number", "client id"],
            description="Optional link back to the customer profile.",
        ),
        MappingFieldDefinition(
            key="customer_name",
            label="Customer Name",
            required=False,
            canonical_column="CustomerName",
            aliases=["customer name", "client name", "full name", "name"],
            description="Optional display name for review-level drilldowns.",
        ),
        MappingFieldDefinition(
            key="product",
            label="Product Name",
            required=False,
            canonical_column="ProductID",
            aliases=["product", "product name", "item", "sku"],
            description="Optional product context for review analysis.",
        ),
    ],
}


def _now_utc() -> datetime:
    return datetime.utcnow()


def _normalize_token(value: object) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _column_signature(columns: Iterable[str]) -> str:
    normalized = sorted(_normalize_token(column) for column in columns if str(column or "").strip())
    return hashlib.sha256("|".join(normalized).encode("utf-8")).hexdigest()


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if RAPIDFUZZ_AVAILABLE:
        return float(fuzz.token_sort_ratio(left, right))
    return float(SequenceMatcher(None, left, right).ratio() * 100)


def _pending_upload_dir(company_id: str, branch_id: Optional[str]) -> Path:
    if ensure_tenant_directories is not None:
        tenant_dirs = ensure_tenant_directories(DATA_DIR, company_id, branch_id)
        pending_dir = tenant_dirs["scope"] / "pending_uploads"
    else:
        company_part = str(company_id or "unknown").strip() or "unknown"
        branch_part = str(branch_id or "GLOBAL").strip() or "GLOBAL"
        pending_dir = DATA_DIR / company_part / branch_part / "pending_uploads"
    pending_dir.mkdir(parents=True, exist_ok=True)
    return pending_dir


def _read_csv(file_path: Path) -> pd.DataFrame:
    last_error: Optional[Exception] = None
    for encoding in (None, "utf-8-sig", "latin-1"):
        try:
            if encoding is None:
                return pd.read_csv(file_path)
            return pd.read_csv(file_path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"CSV validation failed: {exc}") from exc
    raise HTTPException(status_code=400, detail=f"CSV validation failed: {last_error}")


def _serialize_preview_rows(df: pd.DataFrame) -> List[Dict[str, Any]]:
    preview_df = df.head(PREVIEW_ROW_LIMIT).copy()
    return json.loads(preview_df.to_json(orient="records", date_format="iso"))


def _mapping_user_key(user_id: Optional[object]) -> Optional[str]:
    value = str(user_id or "").strip()
    return value or None


def get_field_definitions(dataset_type: str) -> List[MappingFieldDefinition]:
    definitions = DATASET_FIELD_DEFINITIONS.get(dataset_type)
    if not definitions:
        raise HTTPException(status_code=400, detail="Unsupported dataset_type")
    return definitions


def serialize_field_definitions(dataset_type: str) -> List[Dict[str, Any]]:
    return [
        {
            "key": definition.key,
            "label": definition.label,
            "required": definition.required,
            "description": definition.description,
            "canonical_column": definition.canonical_column,
        }
        for definition in get_field_definitions(dataset_type)
    ]


def normalize_mapping_payload(dataset_type: str, mapping: Optional[Dict[str, Optional[str]]]) -> Dict[str, Optional[str]]:
    raw_mapping = mapping or {}
    normalized: Dict[str, Optional[str]] = {}
    for definition in get_field_definitions(dataset_type):
        candidate = raw_mapping.get(definition.key)
        if candidate is None:
            normalized[definition.key] = None
            continue
        value = str(candidate).strip()
        normalized[definition.key] = value or None
    return normalized


def validate_mapping_configuration(dataset_type: str, available_columns: Sequence[str], mapping: Optional[Dict[str, Optional[str]]]) -> Dict[str, Any]:
    normalized_mapping = normalize_mapping_payload(dataset_type, mapping)
    available = {str(column) for column in available_columns}
    errors: List[str] = []
    warnings: List[str] = []
    used_columns: Dict[str, str] = {}

    for definition in get_field_definitions(dataset_type):
        mapped_column = normalized_mapping.get(definition.key)
        if not mapped_column:
            continue
        if mapped_column not in available:
            errors.append(f"{definition.label} maps to an unknown CSV column: {mapped_column}")
            continue
        existing = used_columns.get(mapped_column)
        if existing and existing != definition.label:
            errors.append(f"CSV column '{mapped_column}' is assigned more than once")
            continue
        used_columns[mapped_column] = definition.label

    if dataset_type == "sales":
        if not normalized_mapping.get("order_date"):
            errors.append("Date is required for sales uploads")
        if not normalized_mapping.get("product"):
            errors.append("Product Name is required for sales uploads")
        has_total = bool(normalized_mapping.get("total_price"))
        has_unit_price = bool(normalized_mapping.get("unit_price"))
        has_quantity = bool(normalized_mapping.get("quantity"))
        if not has_total and not (has_unit_price and has_quantity):
            errors.append("Map Sales Amount, or provide both Unit Price and Quantity")
        if not normalized_mapping.get("customer_id"):
            warnings.append("Customer ID is not mapped. RFM segmentation will only work if customers.csv provides CustomerID.")
    elif dataset_type == "customers":
        if not normalized_mapping.get("customer_id"):
            errors.append("Customer ID is required for customer uploads")
    elif dataset_type == "reviews":
        if not normalized_mapping.get("review_text"):
            errors.append("Review Text is required for review uploads")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "mapping": normalized_mapping,
    }


def apply_column_mapping(df: pd.DataFrame, dataset_type: str, mapping: Optional[Dict[str, Optional[str]]]) -> pd.DataFrame:
    renamed = df.copy()
    normalized_mapping = normalize_mapping_payload(dataset_type, mapping)
    rename_map: Dict[str, str] = {}
    for definition in get_field_definitions(dataset_type):
        source_column = normalized_mapping.get(definition.key)
        if not source_column or source_column not in renamed.columns:
            continue
        if source_column == definition.canonical_column:
            continue
        if definition.canonical_column in renamed.columns:
            continue
        rename_map[source_column] = definition.canonical_column
    if rename_map:
        renamed = renamed.rename(columns=rename_map)
    return renamed


def suggest_mapping(dataset_type: str, columns: Sequence[str]) -> Dict[str, Optional[str]]:
    normalized_columns = {str(column): _normalize_token(column) for column in columns if str(column).strip()}
    assignments: Dict[str, Optional[str]] = {}
    candidates: List[tuple[float, str, str]] = []

    for definition in get_field_definitions(dataset_type):
        terms = [_normalize_token(term) for term in definition.search_terms]
        terms = [term for term in terms if term]
        for column, normalized_column in normalized_columns.items():
            best_score = max((_similarity(term, normalized_column) for term in terms), default=0.0)
            if normalized_column in terms:
                best_score = max(best_score, 100.0)
            if best_score >= FUZZY_MATCH_THRESHOLD:
                candidates.append((best_score, definition.key, column))

    used_columns: set[str] = set()
    for score, field_key, column in sorted(candidates, key=lambda item: (-item[0], item[1], item[2])):
        if field_key in assignments:
            continue
        if column in used_columns:
            continue
        assignments[field_key] = column
        used_columns.add(column)

    return {definition.key: assignments.get(definition.key) for definition in get_field_definitions(dataset_type)}


def _filter_available_mapping(dataset_type: str, mapping: Optional[Dict[str, Optional[str]]], columns: Sequence[str]) -> Dict[str, Optional[str]]:
    available = {str(column) for column in columns}
    filtered = normalize_mapping_payload(dataset_type, mapping)
    return {key: value if value in available else None for key, value in filtered.items()}


def _profile_scope_matches(profile: UploadMappingProfile, branch_id: Optional[str], user_id: Optional[str]) -> bool:
    if branch_id and profile.branch_id and str(profile.branch_id) != str(branch_id):
        return False
    if user_id and profile.user_id and str(profile.user_id) != str(user_id):
        return False
    return True


def _serialize_profile(profile: UploadMappingProfile) -> Dict[str, Any]:
    return {
        "id": int(profile.id),
        "company_id": str(profile.company_id),
        "branch_id": str(profile.branch_id) if profile.branch_id is not None else None,
        "user_id": str(profile.user_id) if profile.user_id is not None else None,
        "dataset_type": str(profile.dataset_type),
        "source_columns": list(profile.source_columns or []),
        "mapping": normalize_mapping_payload(str(profile.dataset_type), profile.field_mapping or {}),
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        "last_used_at": profile.last_used_at.isoformat() if profile.last_used_at else None,
    }


def _select_saved_profile(company_id: str, branch_id: Optional[str], user_id: Optional[str], dataset_type: str, columns: Sequence[str]) -> Optional[Dict[str, Any]]:
    init_sqlalchemy_db()
    current_signature = _column_signature(columns)
    current_set = {_normalize_token(column) for column in columns if str(column).strip()}
    db = SessionLocal()
    try:
        profiles = db.query(UploadMappingProfile).filter(
            UploadMappingProfile.company_id == company_id,
            UploadMappingProfile.dataset_type == dataset_type,
        ).all()
        exact_matches = [profile for profile in profiles if profile.source_signature == current_signature and _profile_scope_matches(profile, branch_id, user_id)]
        if exact_matches:
            exact_matches.sort(
                key=lambda profile: (
                    1 if user_id and str(profile.user_id or "") == user_id else 0,
                    1 if branch_id and str(profile.branch_id or "") == str(branch_id) else 0,
                    profile.last_used_at or profile.updated_at or profile.created_at,
                ),
                reverse=True,
            )
            return _serialize_profile(exact_matches[0])

        best_profile: Optional[UploadMappingProfile] = None
        best_score = 0.0
        for profile in profiles:
            if not _profile_scope_matches(profile, branch_id, user_id):
                continue
            stored_set = {_normalize_token(column) for column in (profile.source_columns or []) if str(column).strip()}
            if not stored_set:
                continue
            overlap = len(current_set & stored_set) / max(len(current_set | stored_set), 1)
            overlap += 0.05 if branch_id and str(profile.branch_id or "") == str(branch_id) else 0.0
            overlap += 0.05 if user_id and str(profile.user_id or "") == user_id else 0.0
            if overlap > best_score:
                best_score = overlap
                best_profile = profile

        if best_profile and best_score >= 0.45:
            return _serialize_profile(best_profile)
        return None
    finally:
        db.close()


def list_mapping_profiles(company_id: str, branch_id: Optional[str], user_id: Optional[object], dataset_type: str) -> List[Dict[str, Any]]:
    init_sqlalchemy_db()
    user_key = _mapping_user_key(user_id)
    db = SessionLocal()
    try:
        profiles = db.query(UploadMappingProfile).filter(
            UploadMappingProfile.company_id == company_id,
            UploadMappingProfile.dataset_type == dataset_type,
        ).all()
        filtered = [profile for profile in profiles if _profile_scope_matches(profile, branch_id, user_key)]
        filtered.sort(key=lambda profile: profile.last_used_at or profile.updated_at or profile.created_at, reverse=True)
        return [_serialize_profile(profile) for profile in filtered]
    finally:
        db.close()


def save_mapping_profile(company_id: str, branch_id: Optional[str], user_id: Optional[object], dataset_type: str, columns: Sequence[str], mapping: Optional[Dict[str, Optional[str]]]) -> Dict[str, Any]:
    init_sqlalchemy_db()
    user_key = _mapping_user_key(user_id)
    normalized_mapping = {key: value for key, value in normalize_mapping_payload(dataset_type, mapping).items() if value}
    source_signature = _column_signature(columns)
    now = _now_utc()

    db = SessionLocal()
    try:
        profile = db.query(UploadMappingProfile).filter(
            UploadMappingProfile.company_id == company_id,
            UploadMappingProfile.branch_id == branch_id,
            UploadMappingProfile.user_id == user_key,
            UploadMappingProfile.dataset_type == dataset_type,
            UploadMappingProfile.source_signature == source_signature,
        ).first()

        if profile is None:
            profile = UploadMappingProfile(
                company_id=company_id,
                branch_id=branch_id,
                user_id=user_key,
                dataset_type=dataset_type,
                source_signature=source_signature,
                source_columns=list(columns),
                field_mapping=normalized_mapping,
                created_at=now,
                updated_at=now,
                last_used_at=now,
            )
            db.add(profile)
        else:
            profile.source_columns = list(columns)
            profile.field_mapping = normalized_mapping
            profile.updated_at = now
            profile.last_used_at = now

        db.commit()
        db.refresh(profile)
        return _serialize_profile(profile)
    finally:
        db.close()


def _cleanup_pending_uploads() -> None:
    init_sqlalchemy_db()
    now = _now_utc()
    db = SessionLocal()
    try:
        expired = db.query(PendingDatasetUpload).filter(PendingDatasetUpload.expires_at < now).all()
        for upload in expired:
            Path(str(upload.staged_file_path)).unlink(missing_ok=True)
            db.delete(upload)
        if expired:
            db.commit()
    finally:
        db.close()


def _serialize_pending_upload(upload: PendingDatasetUpload) -> Dict[str, Any]:
    return {
        "upload_id": str(upload.id),
        "company_id": str(upload.company_id),
        "branch_id": str(upload.branch_id) if upload.branch_id is not None else None,
        "user_id": str(upload.user_id) if upload.user_id is not None else None,
        "dataset_type": str(upload.dataset_type),
        "file_name": str(upload.original_file_name),
        "staged_file_path": str(upload.staged_file_path),
        "columns": list(upload.extracted_columns or []),
        "preview_rows": list(upload.preview_rows or []),
        "row_count": int(upload.row_count or 0),
        "replace_dataset_id": int(upload.replace_dataset_id) if upload.replace_dataset_id is not None else None,
        "created_at": upload.created_at.isoformat() if upload.created_at else None,
        "expires_at": upload.expires_at.isoformat() if upload.expires_at else None,
    }


def prepare_dataset_upload(company_id: str, branch_id: Optional[str], user_id: Optional[object], dataset_type: str, original_filename: str, file_bytes: bytes, replace_dataset_id: Optional[int] = None) -> Dict[str, Any]:
    _cleanup_pending_uploads()
    init_sqlalchemy_db()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded CSV file is empty")

    pending_dir = _pending_upload_dir(company_id, branch_id)
    suffix = Path(original_filename or "upload.csv").suffix or ".csv"
    upload_id = uuid4().hex
    staged_path = pending_dir / f"{upload_id}{suffix}"
    staged_path.write_bytes(file_bytes)

    try:
        df = _read_csv(staged_path)
        columns = [str(column) for column in df.columns]
        if not columns:
            raise HTTPException(status_code=400, detail="Uploaded CSV does not contain any columns")
        if df.empty:
            raise HTTPException(status_code=400, detail="Uploaded CSV does not contain any data rows")

        preview_rows = _serialize_preview_rows(df)
        user_key = _mapping_user_key(user_id)
        now = _now_utc()
        expires_at = now + timedelta(hours=PENDING_UPLOAD_TTL_HOURS)
        saved_profile = _select_saved_profile(company_id, branch_id, user_key, dataset_type, columns)
        suggested_mapping = suggest_mapping(dataset_type, columns)
        saved_mapping = _filter_available_mapping(dataset_type, (saved_profile or {}).get("mapping"), columns)
        initial_mapping = saved_mapping if any(saved_mapping.values()) else suggested_mapping
        mapping_source = "saved_profile" if any(saved_mapping.values()) else ("fuzzy_suggestion" if any(initial_mapping.values()) else None)

        db = SessionLocal()
        try:
            pending_upload = PendingDatasetUpload(
                id=upload_id,
                company_id=company_id,
                branch_id=branch_id,
                user_id=user_key,
                dataset_type=dataset_type,
                original_file_name=str(original_filename),
                staged_file_path=str(staged_path),
                column_signature=_column_signature(columns),
                extracted_columns=columns,
                preview_rows=preview_rows,
                row_count=int(len(df)),
                replace_dataset_id=replace_dataset_id,
                created_at=now,
                expires_at=expires_at,
                status="pending",
            )
            db.add(pending_upload)
            db.commit()
        finally:
            db.close()

        return {
            "upload_id": upload_id,
            "dataset_type": dataset_type,
            "file_name": str(original_filename),
            "row_count": int(len(df)),
            "columns": columns,
            "preview_rows": preview_rows,
            "fields": serialize_field_definitions(dataset_type),
            "suggested_mapping": suggested_mapping,
            "saved_mapping": saved_mapping,
            "initial_mapping": initial_mapping,
            "mapping_source": mapping_source,
            "profile_id": (saved_profile or {}).get("id"),
            "replace_dataset_id": replace_dataset_id,
            "expires_at": expires_at.isoformat(),
        }
    except Exception:
        staged_path.unlink(missing_ok=True)
        raise


def get_pending_upload(upload_id: str, company_id: str, branch_id: Optional[str], user_id: Optional[object]) -> Dict[str, Any]:
    _cleanup_pending_uploads()
    init_sqlalchemy_db()
    user_key = _mapping_user_key(user_id)
    db = SessionLocal()
    try:
        pending_upload = db.query(PendingDatasetUpload).filter(
            PendingDatasetUpload.id == upload_id,
            PendingDatasetUpload.company_id == company_id,
            PendingDatasetUpload.status == "pending",
        ).first()
        if pending_upload is None:
            raise HTTPException(status_code=404, detail="Pending upload session not found or expired")
        if branch_id and str(pending_upload.branch_id or "") != str(branch_id):
            raise HTTPException(status_code=404, detail="Pending upload session not found or expired")
        if user_key and str(pending_upload.user_id or "") not in {"", user_key}:
            raise HTTPException(status_code=403, detail="This upload session belongs to another user")
        return _serialize_pending_upload(pending_upload)
    finally:
        db.close()


def read_pending_upload_dataframe(pending_upload: Dict[str, Any]) -> pd.DataFrame:
    file_path = Path(str(pending_upload.get("staged_file_path") or ""))
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Uploaded CSV is no longer available")
    return _read_csv(file_path)


def delete_pending_upload(upload_id: str) -> None:
    init_sqlalchemy_db()
    db = SessionLocal()
    try:
        pending_upload = db.query(PendingDatasetUpload).filter(PendingDatasetUpload.id == upload_id).first()
        if pending_upload is None:
            return
        Path(str(pending_upload.staged_file_path)).unlink(missing_ok=True)
        db.delete(pending_upload)
        db.commit()
    finally:
        db.close()