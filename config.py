"""
Configuration file for Sales Intelligence Project
Load with: python-dotenv or import directly

Usage:
    from config import ML_CONFIG, API_CONFIG
    test_size = ML_CONFIG["forecasting"]["test_size"]
"""

import os
from pathlib import Path

# Project Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
MODEL_DIR = BASE_DIR / "src" / "ml_lifecycle" / "model_registry"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ML Model Configuration
ML_CONFIG = {
    "forecasting": {
        "test_size": 0.2,
        "min_training_months": 2,
        "max_forecast_periods": 60,
        "model_type": "LinearRegression"
    },
    "rfm": {
        "recency_bins": 5,
        "frequency_bins": 5,
        "monetary_bins": 5
    },
    "recommendation": {
        "min_support": 0.01,
        "min_confidence": 0.1,
        "min_lift": 1.0,
        "max_len": 2
    },
    "sentiment": {
        "use_vader": True,
        "min_text_length": 10
    }
}

# API Configuration
API_CONFIG = {
    "host": os.getenv("API_HOST", "0.0.0.0"),
    "port": int(os.getenv("API_PORT", "8000")),
    "reload": os.getenv("API_RELOAD", "true").lower() == "true",
    "workers": int(os.getenv("API_WORKERS", "1")),
    "cors_origins": os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:5173,http://localhost:3000"
    ).split(","),
    "rate_limit": {
        "enabled": os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
        "per_minute": int(os.getenv("RATE_LIMIT_PER_MINUTE", "30")),
        "per_hour": int(os.getenv("RATE_LIMIT_PER_HOUR", "100"))
    }
}

# Data Configuration
DATA_CONFIG = {
    "csv_encoding": "utf-8",
    "date_format": "%Y-%m-%d",
    "max_upload_size_mb": 50,
    "allowed_file_types": [".csv", ".xlsx"]
}

# Logging Configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(levelname)s - %(message)s",
    "file_encoding": "utf-8"
}

# Security Configuration (use environment variables in production)
SECURITY_CONFIG = {
    "secret_key": os.getenv("SECRET_KEY", "CHANGE-THIS-IN-PRODUCTION-USE-RANDOM-256BIT-KEY"),
    "algorithm": "HS256",
    # NOTE: This should match ACCESS_TOKEN_EXPIRE_MINUTES in backend/main.py (24 hours = 1440 minutes)
    "access_token_expire_minutes": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
}

# ============================================================================
# ANALYTICAL SCOPE CONFIGURATION
# ============================================================================
# This section explicitly defines WHAT the system can and cannot analyze.
# This addresses Problem #1: Conceptual & Logical Issues

ANALYTICAL_SCOPE = {
    "system_name": "Intelligent Sales Analytics and Forecasting System",
    "version": "1.0.0",
    
    # What type of data this system is designed for
    "designed_for": "Transactional Sales Data",
    
    # Business questions the system can answer
    "supported_analyses": {
        "forecasting": {
            "question": "What will our sales be in the next N months?",
            "requires": ["date", "revenue/amount"],
            "optional": ["product", "customer"],
            "min_data_points": 30
        },
        "rfm_segmentation": {
            "question": "How do we categorize customers by value?",
            "requires": ["date", "customer_id", "revenue"],
            "optional": ["order_id"],
            "min_data_points": 10
        },
        "product_recommendations": {
            "question": "What products are frequently bought together?",
            "requires": ["product"],
            "optional": ["order_id", "customer_id"],
            "min_data_points": 50
        },
        "sentiment_analysis": {
            "question": "What is customer sentiment from reviews?",
            "requires": ["review_text"],
            "optional": ["rating", "date"],
            "min_data_points": 5,
            "note": "Requires separate reviews dataset"
        }
    },
    
    # What the system CANNOT analyze (explicit limitations)
    "not_supported": [
        "Image or video analysis",
        "Real-time streaming data",
        "Non-transactional data (surveys, logs without transactions)",
        "Data without date/time context",
        "Financial forecasting beyond simple trend extrapolation",
        "Causal inference or A/B test analysis"
    ],
    
    # Data quality requirements
    "data_requirements": {
        "min_rows": 10,
        "max_file_size_mb": 50,
        "supported_formats": [".csv", ".xlsx"],
        "required_for_full_analysis": ["sales.csv"],
        "optional_datasets": ["customers.csv", "reviews.csv"]
    }
}

# Schema configuration - column aliases for flexibility
# This addresses Problem #2: Hard-Coded Column Assumptions
SCHEMA_CONFIG = {
    # Semantic field -> list of acceptable column names
    "column_aliases": {
        "order_date": [
            "OrderDate", "order_date", "Sale_Date", "sale_date",
            "Date", "date", "TransactionDate", "InvoiceDate"
        ],
        "customer_id": [
            "CustomerID", "customer_id", "Customer_ID", "cust_id",
            "client_id", "ClientID", "user_id"
        ],
        "order_id": [
            "OrderID", "order_id", "Order_ID", "InvoiceNo",
            "TransactionID", "Receipt"
        ],
        "product": [
            "Product", "product", "ProductName", "Item",
            "Description", "SKU", "ItemName"
        ],
        "quantity": [
            "Quantity", "quantity", "Qty", "qty", "Units"
        ],
        "unit_price": [
            "UnitPrice", "unit_price", "Price", "price", "ItemPrice"
        ],
        "total_price": [
            "TotalPrice", "total_price", "Total", "Revenue",
            "Sales", "Amount", "Sales_Amount"
        ],
        "city": [
            "City", "city", "Location", "Region", "State"
        ],
        "review_text": [
            "Review", "review", "Comment", "Feedback", "Text"
        ],
        "rating": [
            "Rating", "rating", "Score", "Stars"
        ]
    },
    
    # Auto-compute rules
    "computed_fields": {
        "total_price": {
            "compute_from": ["unit_price", "quantity"],
            "formula": "unit_price * quantity"
        }
    }
}

# Pipeline execution configuration
# This addresses Problem #4: Pipeline Rigidity
PIPELINE_CONFIG = {
    # Enable/disable individual pipeline stages
    "stages": {
        "eda": {"enabled": True, "required": True},
        "forecasting": {"enabled": True, "required": False},
        "rfm": {"enabled": True, "required": False},
        "recommendation": {"enabled": True, "required": False},
        "sentiment": {"enabled": True, "required": False}
    },
    
    # Behavior when data is insufficient
    "on_insufficient_data": "skip",  # Options: "skip", "warn", "fail"
    
    # Behavior when analysis fails
    "on_analysis_error": "continue",  # Options: "continue", "stop"
}

    warnings = []
    
    if SECURITY_CONFIG["secret_key"] == "CHANGE-THIS-IN-PRODUCTION-USE-RANDOM-256BIT-KEY":
        warnings.append("WARNING: Using default SECRET_KEY. Change this in production!")
    
    if not DATA_DIR.exists():
        warnings.append(f"WARNING: Data directory not found: {DATA_DIR}")
    
    if os.getenv("ENVIRONMENT", "development") == "production":
        if not API_CONFIG["rate_limit"]["enabled"]:
            warnings.append("WARNING: Rate limiting disabled in production!")
        if "http://localhost" in API_CONFIG["cors_origins"][0]:
            warnings.append("WARNING: localhost in CORS origins for production!")
    
    return warnings

# Run validation on import (optional)
if __name__ != "__main__":
    _warnings = validate_config()
    if _warnings:
        import logging
        logger = logging.getLogger(__name__)
        for warning in _warnings:
            logger.warning(warning)
