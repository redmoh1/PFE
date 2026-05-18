import pandas as pd

from backend.main import build_canonical_sales_dataframe
from backend.upload_mapping import apply_column_mapping, validate_mapping_configuration


def test_sales_mapping_validation_accepts_manual_required_fields():
    columns = ["Sale Date", "Total Sales", "SKU", "Client_Number"]
    mapping = {
        "order_date": "Sale Date",
        "total_price": "Total Sales",
        "product": "SKU",
        "customer_id": "Client_Number",
    }

    result = validate_mapping_configuration("sales", columns, mapping)

    assert result["valid"] is True
    assert result["errors"] == []
    assert result["mapping"]["product"] == "SKU"


def test_apply_column_mapping_and_sales_canonicalization_preserves_customer_id():
    raw_df = pd.DataFrame(
        {
            "Sale Date": ["2024-01-01", "2024-01-02"],
            "Total Sales": [100.0, 150.0],
            "SKU": ["Widget A", "Widget B"],
            "Client_Number": ["C-1", "C-2"],
            "Region": ["Setif", "Algiers"],
        }
    )

    mapped_df = apply_column_mapping(
        raw_df,
        "sales",
        {
            "order_date": "Sale Date",
            "total_price": "Total Sales",
            "product": "SKU",
            "customer_id": "Client_Number",
            "city": "Region",
        },
    )
    canonical = build_canonical_sales_dataframe(mapped_df)

    assert list(canonical.columns) == ["OrderID", "OrderDate", "TotalPrice", "ProductID", "Product", "City", "CustomerID"]
    assert canonical["CustomerID"].tolist() == ["C-1", "C-2"]
    assert canonical["ProductID"].tolist() == ["Widget A", "Widget B"]
    assert canonical["Product"].tolist() == ["Widget A", "Widget B"]