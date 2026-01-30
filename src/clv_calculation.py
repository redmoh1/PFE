"""
CLV Calculation Module Wrapper
Provides clean import path for the backend API.
"""

# Re-export from the numbered module
from __future__ import annotations
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and re-export the main functions
try:
    from importlib import import_module
    _module = import_module("09_clv_calculation")
    run_clv_analysis = _module.run_clv_analysis
    calculate_historical_clv = _module.calculate_historical_clv
    calculate_average_clv = _module.calculate_average_clv
    calculate_predictive_clv = _module.calculate_predictive_clv
    assign_clv_segments = _module.assign_clv_segments
    generate_clv_insights = _module.generate_clv_insights
except ImportError as e:
    # Fallback stub
    def run_clv_analysis(company_name: str):
        return {
            "company": company_name,
            "insights": {"summary": {}, "segments": {}, "recommendations": []},
            "top_customers": [],
            "error": f"Module import failed: {e}"
        }
