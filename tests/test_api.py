"""
Unit tests for Sales Intelligence Backend API
Run with: pytest tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.main import app

client = TestClient(app)


def _auth_headers():
    return {"Authorization": "Bearer demo-token-admin@acme.com"}


class TestRootEndpoints:
    """Test root and health endpoints."""
    
    def test_root_endpoint(self):
        """Test root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
        assert "docs" in data
        assert data["version"] == "1.0.0"
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data
        assert data["status"] in ["healthy", "degraded"]


class TestKPIEndpoints:
    """Test KPI analytics endpoints."""
    
    def test_kpis_without_dates(self):
        """Test KPIs endpoint without date filters."""
        response = client.get("/api/kpis", headers=_auth_headers())
        # Should return 200, 204 (no data), or 503 if data not loaded
        assert response.status_code in [200, 204, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "total_revenue" in data
            assert "total_orders" in data
            assert "average_order_value" in data
    
    def test_kpis_with_valid_dates(self):
        """Test KPIs with valid date range."""
        response = client.get(
            "/api/kpis?start_date=2024-01-01&end_date=2024-12-31",
            headers=_auth_headers(),
        )
        assert response.status_code in [200, 204, 503]
    
    def test_kpis_with_invalid_date_format(self):
        """Test KPIs with invalid date format.
        
        FastAPI Query validation with pattern=r"^\\d{4}-\\d{2}-\\d{2}$" should reject
        strings that don't match YYYY-MM-DD format with a 422 Unprocessable Entity.
        """
        response = client.get("/api/kpis?start_date=invalid-date", headers=_auth_headers())
        # FastAPI returns 422 for validation errors (Query pattern mismatch)
        assert response.status_code == 422
        # Verify error message mentions the invalid parameter
        if response.status_code == 422:
            error_detail = response.json()
            assert "detail" in error_detail


class TestForecastEndpoints:
    """Test forecasting endpoints."""
    
    def test_monthly_sales(self):
        """Test monthly sales endpoint."""
        response = client.get("/api/monthly-sales", headers=_auth_headers())
        assert response.status_code in [200, 204, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)


class TestProductEndpoints:
    """Test product analysis endpoints."""
    
    def test_top_products_default_limit(self):
        """Test top products with default limit."""
        response = client.get("/api/top-products", headers=_auth_headers())
        assert response.status_code in [200, 204, 503]
    
    def test_top_products_custom_limit(self):
        """Test top products with custom limit."""
        response = client.get("/api/top-products?limit=5", headers=_auth_headers())
        assert response.status_code in [200, 204, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert len(data) <= 5
    
    def test_top_products_invalid_limit(self):
        """Test top products with invalid limit (> 100)."""
        response = client.get("/api/top-products?limit=150", headers=_auth_headers())
        # Should return validation error
        assert response.status_code == 422


class TestSentimentEndpoints:
    """Test Customer Feedback endpoints."""
    
    def test_sentiment_endpoint(self):
        """Test Customer Feedback endpoint."""
        response = client.get("/api/sentiment", headers=_auth_headers())
        assert response.status_code in [200, 204, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "sentiment_breakdown" in data
            assert "total_reviews" in data


class TestRecommendationEndpoints:
    """Test product recommendation endpoints."""
    
    def test_recommendations_default(self):
        """Test recommendations with default limit."""
        response = client.get("/api/recommendations", headers=_auth_headers())
        assert response.status_code in [200, 204, 503]
    
    def test_recommendations_with_limit(self):
        """Test recommendations with custom limit."""
        response = client.get("/api/recommendations?limit=5", headers=_auth_headers())
        assert response.status_code in [200, 204, 503]


class TestRawDataEndpoints:
    """Test raw data access endpoints."""
    
    def test_raw_data_default_limit(self):
        """Test raw data with default limit."""
        response = client.get("/api/raw-data", headers=_auth_headers())
        assert response.status_code in [200, 204, 503]
    
    def test_raw_data_with_limit(self):
        """Test raw data with custom limit."""
        response = client.get("/api/raw-data?limit=50", headers=_auth_headers())
        assert response.status_code in [200, 204, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert len(data) <= 50


class TestSummaryEndpoints:
    """Test system summary endpoints."""
    
    def test_summary_endpoint(self):
        """Test system summary endpoint."""
        response = client.get("/api/summary", headers=_auth_headers())
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "data_status" in data
        assert "timestamp" in data


# Parametrized tests for edge cases
@pytest.mark.parametrize("endpoint", [
    "/api/kpis",
    "/api/monthly-sales",
    "/api/top-products",
    "/api/top-cities",
    "/api/sentiment",
    "/api/recommendations",
    "/api/raw-data",
    "/api/summary"
])
def test_all_endpoints_accessible(endpoint):
    """Test that all endpoints are accessible."""
    response = client.get(endpoint, headers=_auth_headers())
    # Should not return 404 or 500
    assert response.status_code != 404
    assert response.status_code != 500


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
