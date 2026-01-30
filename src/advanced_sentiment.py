"""
Advanced Sentiment Analysis Module Wrapper
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
    _module = import_module("07_advanced_sentiment")
    run_advanced_sentiment_analysis = _module.run_advanced_sentiment_analysis
    analyze_review = _module.analyze_review
    generate_aspect_insights = _module.generate_aspect_insights
    ASPECT_KEYWORDS = _module.ASPECT_KEYWORDS
except ImportError as e:
    # Fallback stub
    def run_advanced_sentiment_analysis(company_name: str):
        return {
            "company": company_name,
            "total_reviews": 0,
            "aspect_analysis": {},
            "alerts": [],
            "recommendations": [],
            "error": f"Module import failed: {e}"
        }
