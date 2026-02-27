"""
Unit tests for ML lifecycle scripts
Run with: pytest tests/test_ml_scripts.py -v
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestDataValidation:
    """Test data validation utilities."""
    
    def test_empty_dataframe_detection(self):
        """Test detection of empty dataframes."""
        df_empty = pd.DataFrame()
        assert len(df_empty) == 0
    
    def test_required_columns_check(self):
        """Test required columns validation."""
        df = pd.DataFrame({
            "OrderDate": ["2024-01-01"],
            "TotalPrice": [100.0]
        })
        required_cols = {"OrderDate", "TotalPrice"}
        missing = required_cols - set(df.columns)
        assert len(missing) == 0


class TestDateProcessing:
    """Test date parsing and processing."""
    
    def test_date_parsing_valid(self):
        """Test parsing valid dates."""
        df = pd.DataFrame({"OrderDate": ["2024-01-01", "2024-01-02"]})
        df["OrderDate"] = pd.to_datetime(df["OrderDate"], errors="coerce")
        assert df["OrderDate"].isna().sum() == 0
    
    def test_date_parsing_invalid(self):
        """Test parsing invalid dates."""
        df = pd.DataFrame({"OrderDate": ["invalid-date", "2024-01-02"]})
        df["OrderDate"] = pd.to_datetime(df["OrderDate"], errors="coerce")
        invalid_count = df["OrderDate"].isna().sum()
        assert invalid_count == 1


class TestMonthlyAggregation:
    """Test monthly sales aggregation."""
    
    def test_monthly_grouping(self):
        """Test grouping sales by month."""
        df = pd.DataFrame({
            "OrderDate": pd.date_range("2024-01-01", periods=90, freq="D"),
            "TotalPrice": np.random.randint(100, 1000, 90)
        })
        
        monthly = df.groupby(pd.Grouper(key="OrderDate", freq="MS"))["TotalPrice"].sum()
        # 90 days should give us 3 months
        assert len(monthly) >= 3


class TestForecastingLogic:
    """Test forecasting logic without full model training."""
    
    def test_future_periods_generation(self):
        """Test generation of future time periods."""
        periods = 6
        last_date = pd.Timestamp("2024-03-01")
        future_dates = pd.date_range(
            start=last_date + pd.DateOffset(months=1),
            periods=periods,
            freq="MS"
        )
        assert len(future_dates) == periods
    
    def test_month_index_feature(self):
        """Test MonthIndex feature creation."""
        df = pd.DataFrame({
            "OrderDate": pd.date_range("2024-01-01", periods=5, freq="MS")
        })
        df["MonthIndex"] = range(len(df))
        assert df["MonthIndex"].tolist() == [0, 1, 2, 3, 4]


class TestRFMCalculations:
    """Test RFM (Recency, Frequency, Monetary) calculations."""
    
    def test_recency_calculation(self):
        """Test recency calculation."""
        analysis_date = pd.Timestamp("2024-12-31")
        last_purchase = pd.Timestamp("2024-12-15")
        recency = (analysis_date - last_purchase).days
        assert recency == 16
    
    def test_frequency_calculation(self):
        """Test frequency calculation."""
        df = pd.DataFrame({
            "CustomerID": ["C1", "C1", "C2", "C2", "C2"],
            "OrderID": [1, 2, 3, 4, 5]
        })
        frequency = df.groupby("CustomerID")["OrderID"].nunique()
        assert frequency["C1"] == 2
        assert frequency["C2"] == 3


class TestSentimentAnalysis:
    """Test Customer Feedback logic."""
    
    def test_positive_sentiment(self):
        """Test positive sentiment detection."""
        from textblob import TextBlob
        text = "This product is excellent and amazing!"
        blob = TextBlob(text)
        assert blob.sentiment.polarity > 0
    
    def test_negative_sentiment(self):
        """Test negative sentiment detection."""
        from textblob import TextBlob
        text = "This product is terrible and awful!"
        blob = TextBlob(text)
        assert blob.sentiment.polarity < 0
    
    def test_neutral_sentiment(self):
        """Test neutral sentiment detection."""
        from textblob import TextBlob
        text = "This is a product."
        blob = TextBlob(text)
        # Neutral should be close to 0
        assert abs(blob.sentiment.polarity) < 0.2


class TestDataCleaning:
    """Test data cleaning utilities."""
    
    def test_duplicate_removal(self):
        """Test duplicate row removal."""
        df = pd.DataFrame({
            "OrderID": [1, 1, 2, 3],
            "Value": [100, 100, 200, 300]
        })
        df_clean = df.drop_duplicates()
        assert len(df_clean) == 3
    
    def test_missing_value_handling(self):
        """Test missing value handling."""
        df = pd.DataFrame({
            "A": [1, 2, None, 4],
            "B": ["x", None, "z", "w"]
        })
        # Numeric: fill with median
        df["A"] = df["A"].fillna(df["A"].median())
        assert df["A"].isna().sum() == 0
        
        # Categorical: fill with mode
        mode_val = df["B"].mode()[0] if not df["B"].mode().empty else "Unknown"
        df["B"] = df["B"].fillna(mode_val)
        assert df["B"].isna().sum() == 0


# Parametrized tests
@pytest.mark.parametrize("test_size,min_train", [
    (0.2, 2),
    (0.3, 3),
    (0.25, 2)
])
def test_train_test_split_params(test_size, min_train):
    """Test different train/test split parameters."""
    total_samples = 10
    test_samples = int(total_samples * test_size)
    train_samples = total_samples - test_samples
    assert train_samples >= min_train


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
