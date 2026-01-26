"""
Pytest configuration file
"""

import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


@pytest.fixture(scope="session")
def test_data_dir():
    """Fixture providing path to test data directory."""
    return project_root / "data"


@pytest.fixture(scope="session")
def sample_sales_data():
    """Fixture providing sample sales data for testing."""
    import pandas as pd
    return pd.DataFrame({
        "OrderID": [1, 2, 3, 4, 5],
        "CustomerID": ["C1", "C2", "C1", "C3", "C2"],
        "OrderDate": pd.date_range("2024-01-01", periods=5, freq="D"),
        "TotalPrice": [100.0, 200.0, 150.0, 300.0, 250.0],
        "Product": ["P1", "P2", "P1", "P3", "P2"],
        "City": ["New York", "Los Angeles", "New York", "Chicago", "Los Angeles"]
    })


@pytest.fixture(scope="session")
def sample_review_data():
    """Fixture providing sample review data for testing."""
    import pandas as pd
    return pd.DataFrame({
        "ReviewID": [1, 2, 3],
        "CustomerID": ["C1", "C2", "C3"],
        "ReviewText": [
            "This product is excellent!",
            "Not satisfied with the quality.",
            "Average product, nothing special."
        ],
        "ReviewDate": pd.date_range("2024-01-01", periods=3, freq="D")
    })
