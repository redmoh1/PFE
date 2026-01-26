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
    "access_token_expire_minutes": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
}

# Validation Helper
def validate_config():
    """Validate critical configuration values."""
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
