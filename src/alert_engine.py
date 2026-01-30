"""
Alert Engine Module Wrapper
Provides clean import path for the backend API.
"""

# Re-export from the numbered module
from __future__ import annotations
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and re-export the main function
try:
    from importlib import import_module
    _module = import_module("08_alert_engine")
    run_alert_engine = _module.run_alert_engine
    AlertEngine = _module.AlertEngine
    BusinessAlert = _module.BusinessAlert
except ImportError as e:
    # Fallback stub
    def run_alert_engine(company_name: str):
        return {
            "company": company_name,
            "total_alerts": 0,
            "alerts": [],
            "error": f"Module import failed: {e}"
        }
