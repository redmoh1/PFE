"""
Analytics Persistence Layer - Database-backed storage for analytics results.

This module provides a bridge between CSV-based analytics scripts and 
SQLAlchemy models for reliable persistence in containerized environments.

PROBLEM SOLVED:
- CSV files and in-memory storage are lost on container restarts
- Analytics results need to survive server restarts in Render/Docker

ARCHITECTURE:
- Each analytics type has save/get/delete functions
- Uses existing SQLAlchemy models (ForecastResult, RFMResult, SentimentResult)
- Provides fallback to CSV if database is unavailable
- Multi-tenant support via company_id

USAGE:
    from analytics_persistence import (
        save_forecast_results,
        get_forecast_results,
        save_rfm_results,
        get_rfm_results,
        save_sentiment_results,
        get_sentiment_results,
        save_recommendation_results,
        get_recommendation_results,
    )
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import sys

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import desc, Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON

# Ensure backend directory is in path for imports
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database.connection import SessionLocal, engine
from database.models import (
    Base,
    ForecastResult,
    RFMResult,
    SentimentResult,
    ModelPerformanceLog,
    Company,
)

logger = logging.getLogger(__name__)

# Ensure tables exist
Base.metadata.create_all(bind=engine)


def get_or_create_company(db: Session, company_id: str) -> Optional[int]:
    """Get or create a company by name/slug, return its database ID."""
    if not company_id:
        # Default to company ID 1 (Acme Corp) for backward compatibility
        return 1
    
    # Try to find existing company
    company = db.query(Company).filter(
        (Company.name == company_id) | (Company.slug == company_id)
    ).first()
    
    if company:
        return company.id
    
    # Create new company if not found
    try:
        new_company = Company(
            name=company_id,
            slug=company_id.lower().replace(" ", "-"),
            data_directory=company_id,
        )
        db.add(new_company)
        db.commit()
        db.refresh(new_company)
        logger.info(f"Created new company: {company_id} (ID: {new_company.id})")
        return new_company.id
    except Exception as e:
        logger.warning(f"Could not create company {company_id}: {e}")
        db.rollback()
        return 1  # Fallback to default company


# =============================================================================
# FORECAST PERSISTENCE
# =============================================================================

def save_forecast_results(
    forecast_data: List[Dict[str, Any]],
    company_id: str = "Acme Corp",
    model_type: str = "LinearRegression",
    model_version: int = 1,
    forecast_periods: int = 12,
    metrics: Optional[Dict[str, float]] = None,
    trend_data: Optional[List[Dict]] = None,
    seasonality_data: Optional[List[Dict]] = None,
) -> bool:
    """
    Save forecast results to database.
    
    Args:
        forecast_data: List of forecast records [{"date": "2026-02", "yhat": 1000, ...}, ...]
        company_id: Company identifier
        model_type: "LinearRegression", "Prophet", etc.
        model_version: Version number
        forecast_periods: Number of months forecasted
        metrics: Optional dict with mae, rmse, mape, r2
        trend_data: Optional trend component data (for Prophet)
        seasonality_data: Optional seasonality component data (for Prophet)
    
    Returns:
        True if saved successfully, False otherwise
    """
    db = SessionLocal()
    try:
        company_db_id = get_or_create_company(db, company_id)
        
        # Delete existing forecasts for this company/model combination
        db.query(ForecastResult).filter(
            ForecastResult.company_id == company_db_id,
            ForecastResult.model_type == model_type,
        ).delete()
        
        # Create new forecast result
        forecast = ForecastResult(
            company_id=company_db_id,
            model_type=model_type,
            model_version=model_version,
            forecast_periods=forecast_periods,
            mae=metrics.get("mae") if metrics else None,
            rmse=metrics.get("rmse") if metrics else None,
            mape=metrics.get("mape") if metrics else None,
            r2=metrics.get("r2") if metrics else None,
            forecast_data=forecast_data,
            trend_data=trend_data,
            seasonality_data=seasonality_data,
        )
        
        db.add(forecast)
        db.commit()
        logger.info(f"Saved forecast ({model_type}) to database: {len(forecast_data)} records")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save forecast to database: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def get_forecast_results(
    company_id: str = "Acme Corp",
    model_type: Optional[str] = None,
) -> Optional[pd.DataFrame]:
    """
    Get forecast results from database.
    
    Args:
        company_id: Company identifier
        model_type: Optional filter by model type
    
    Returns:
        DataFrame with forecast data or None if not found
    """
    db = SessionLocal()
    try:
        company_db_id = get_or_create_company(db, company_id)
        
        query = db.query(ForecastResult).filter(
            ForecastResult.company_id == company_db_id
        )
        
        if model_type:
            query = query.filter(ForecastResult.model_type == model_type)
        
        # Get latest forecast
        forecast = query.order_by(desc(ForecastResult.created_at)).first()
        
        if not forecast or not forecast.forecast_data:
            logger.info(f"No forecast found in database for company {company_id}")
            return None
        
        # Convert JSON data to DataFrame
        df = pd.DataFrame(forecast.forecast_data)

        # Normalize column names to match the CSV loader and API merge logic.
        # Historical note: some writers store OrderDate/ForecastedSales directly.
        date_candidates = ["MonthStart", "date", "ds", "OrderDate", "Date"]
        date_col = next((c for c in date_candidates if c in df.columns), None)
        if date_col and date_col != "MonthStart":
            df = df.rename(columns={date_col: "MonthStart"})

        forecast_candidates = ["ForecastedSales", "yhat", "forecast", "predicted"]
        forecast_col = next((c for c in forecast_candidates if c in df.columns), None)
        if forecast_col and forecast_col != "ForecastedSales":
            df = df.rename(columns={forecast_col: "ForecastedSales"})

        if "MonthStart" in df.columns:
            df["MonthStart"] = pd.to_datetime(df["MonthStart"], errors="coerce")
        
        logger.info(f"Loaded forecast from database: {len(df)} records")
        return df
        
    except Exception as e:
        logger.error(f"Failed to get forecast from database: {e}")
        return None
    finally:
        db.close()


def delete_forecast_results(company_id: str = "Acme Corp") -> int:
    """Delete all forecast results for a company. Returns count of deleted records."""
    db = SessionLocal()
    try:
        company_db_id = get_or_create_company(db, company_id)
        count = db.query(ForecastResult).filter(
            ForecastResult.company_id == company_db_id
        ).delete()
        db.commit()
        logger.info(f"Deleted {count} forecast records for company {company_id}")
        return count
    except Exception as e:
        logger.error(f"Failed to delete forecasts: {e}")
        db.rollback()
        return 0
    finally:
        db.close()


# =============================================================================
# RFM SEGMENTATION PERSISTENCE
# =============================================================================

def save_rfm_results(
    rfm_data: pd.DataFrame,
    company_id: str = "Acme Corp",
) -> bool:
    """
    Save RFM segmentation results to database.
    
    Args:
        rfm_data: DataFrame with columns: CustomerID, Recency, Frequency, Monetary, 
                  R_Score, F_Score, M_Score, Segment
        company_id: Company identifier
    
    Returns:
        True if saved successfully, False otherwise
    """
    db = SessionLocal()
    try:
        company_db_id = get_or_create_company(db, company_id)
        
        # Delete existing RFM results for this company
        db.query(RFMResult).filter(
            RFMResult.company_id == company_db_id
        ).delete()
        db.commit()
        
        # Normalize column names
        df = rfm_data.copy()
        col_map = {
            "CustomerID": "customer_id", "Customer_ID": "customer_id", "customer_id": "customer_id",
            "CustomerName": "customer_name", "Customer_Name": "customer_name",
            "Recency": "recency", "recency": "recency",
            "Frequency": "frequency", "frequency": "frequency",
            "Monetary": "monetary", "monetary": "monetary",
            "R_Score": "r_score", "R": "r_score", "r_score": "r_score",
            "F_Score": "f_score", "F": "f_score", "f_score": "f_score",
            "M_Score": "m_score", "M": "m_score", "m_score": "m_score",
            "Segment": "rfm_segment", "RFM_Segment": "rfm_segment", "segment": "rfm_segment",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        
        # Insert records
        records_added = 0
        for _, row in df.iterrows():
            try:
                rfm = RFMResult(
                    company_id=company_db_id,
                    customer_id=str(row.get("customer_id", "")),
                    customer_name=str(row.get("customer_name", "")) if "customer_name" in row else None,
                    recency=int(row.get("recency", 0)),
                    frequency=int(row.get("frequency", 0)),
                    monetary=float(row.get("monetary", 0)),
                    r_score=int(row.get("r_score", 0)),
                    f_score=int(row.get("f_score", 0)),
                    m_score=int(row.get("m_score", 0)),
                    rfm_segment=str(row.get("rfm_segment", "Unknown")),
                )
                db.add(rfm)
                records_added += 1
            except Exception as e:
                logger.warning(f"Skipped RFM record: {e}")
        
        db.commit()
        logger.info(f"Saved {records_added} RFM records to database for company {company_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save RFM results to database: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def get_rfm_results(company_id: str = "Acme Corp") -> Optional[pd.DataFrame]:
    """
    Get RFM segmentation results from database.
    
    Returns:
        DataFrame with RFM data or None if not found
    """
    db = SessionLocal()
    try:
        company_db_id = get_or_create_company(db, company_id)
        
        results = db.query(RFMResult).filter(
            RFMResult.company_id == company_db_id
        ).all()
        
        if not results:
            logger.info(f"No RFM results found in database for company {company_id}")
            return None
        
        # Convert to DataFrame
        data = []
        for r in results:
            data.append({
                "CustomerID": r.customer_id,
                "CustomerName": r.customer_name,
                "Recency": r.recency,
                "Frequency": r.frequency,
                "Monetary": r.monetary,
                "R_Score": r.r_score,
                "F_Score": r.f_score,
                "M_Score": r.m_score,
                "Segment": r.rfm_segment,
            })
        
        df = pd.DataFrame(data)
        logger.info(f"Loaded {len(df)} RFM records from database")
        return df
        
    except Exception as e:
        logger.error(f"Failed to get RFM results from database: {e}")
        return None
    finally:
        db.close()


def delete_rfm_results(company_id: str = "Acme Corp") -> int:
    """Delete all RFM results for a company. Returns count of deleted records."""
    db = SessionLocal()
    try:
        company_db_id = get_or_create_company(db, company_id)
        count = db.query(RFMResult).filter(
            RFMResult.company_id == company_db_id
        ).delete()
        db.commit()
        logger.info(f"Deleted {count} RFM records for company {company_id}")
        return count
    except Exception as e:
        logger.error(f"Failed to delete RFM results: {e}")
        db.rollback()
        return 0
    finally:
        db.close()


# =============================================================================
# SENTIMENT ANALYSIS PERSISTENCE
# =============================================================================

def save_sentiment_results(
    sentiment_data: pd.DataFrame,
    company_id: str = "Acme Corp",
    analysis_method: str = "textblob",
) -> bool:
    """
    Save sentiment analysis results to database.
    
    Args:
        sentiment_data: DataFrame with columns: ReviewText, Sentiment/SentimentLabel, 
                        Confidence/Polarity, ProductID (optional), Rating (optional)
        company_id: Company identifier
        analysis_method: "textblob", "arabic_bert", etc.
    
    Returns:
        True if saved successfully, False otherwise
    """
    db = SessionLocal()
    try:
        company_db_id = get_or_create_company(db, company_id)
        
        # Delete existing sentiment results for this company
        db.query(SentimentResult).filter(
            SentimentResult.company_id == company_db_id
        ).delete()
        db.commit()
        
        # Normalize column names
        df = sentiment_data.copy()
        
        # Find review text column
        text_col = None
        for col in ["ReviewText", "review_text", "CleanedText", "text", "Text", "comment"]:
            if col in df.columns:
                text_col = col
                break
        
        # Find sentiment column
        sentiment_col = None
        for col in ["SentimentLabel", "Sentiment", "Label", "sentiment_label", "sentiment"]:
            if col in df.columns:
                sentiment_col = col
                break
        
        # Find confidence/polarity column
        confidence_col = None
        for col in ["Confidence", "confidence", "score"]:
            if col in df.columns:
                confidence_col = col
                break
        
        polarity_col = None
        for col in ["Polarity", "polarity"]:
            if col in df.columns:
                polarity_col = col
                break
        
        if not text_col or not sentiment_col:
            logger.error(f"Missing required columns. Found: {df.columns.tolist()}")
            return False
        
        # Insert records
        records_added = 0
        for idx, row in df.iterrows():
            try:
                sentiment = SentimentResult(
                    company_id=company_db_id,
                    review_id=str(row.get("ReviewID", row.get("review_id", idx))),
                    review_text=str(row[text_col])[:5000],  # Limit length
                    sentiment=str(row[sentiment_col]),
                    confidence=float(row.get(confidence_col, 0.0)) if confidence_col else 0.0,
                    polarity=float(row.get(polarity_col, 0.0)) if polarity_col else 0.0,
                    analysis_method=analysis_method,
                    product_id=str(row.get("ProductID", row.get("product_id", ""))) or None,
                    rating=int(row.get("Rating", row.get("rating", 0))) if pd.notna(row.get("Rating", row.get("rating"))) else None,
                    review_date=pd.to_datetime(row.get("ReviewDate", row.get("review_date")), errors="coerce") if "ReviewDate" in row or "review_date" in row else None,
                )
                db.add(sentiment)
                records_added += 1
            except Exception as e:
                logger.warning(f"Skipped sentiment record {idx}: {e}")
        
        db.commit()
        logger.info(f"Saved {records_added} sentiment records to database for company {company_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save sentiment results to database: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def get_sentiment_results(company_id: str = "Acme Corp") -> Optional[pd.DataFrame]:
    """
    Get sentiment analysis results from database.
    
    Returns:
        DataFrame with sentiment data or None if not found
    """
    db = SessionLocal()
    try:
        company_db_id = get_or_create_company(db, company_id)
        
        results = db.query(SentimentResult).filter(
            SentimentResult.company_id == company_db_id
        ).all()
        
        if not results:
            logger.info(f"No sentiment results found in database for company {company_id}")
            return None
        
        # Convert to DataFrame
        data = []
        for r in results:
            data.append({
                "ReviewID": r.review_id,
                "ReviewText": r.review_text,
                "SentimentLabel": r.sentiment,
                "Confidence": r.confidence,
                "Polarity": r.polarity,
                "ProductID": r.product_id,
                "Rating": r.rating,
                "AnalysisMethod": r.analysis_method,
            })
        
        df = pd.DataFrame(data)
        logger.info(f"Loaded {len(df)} sentiment records from database")
        return df
        
    except Exception as e:
        logger.error(f"Failed to get sentiment results from database: {e}")
        return None
    finally:
        db.close()


def delete_sentiment_results(company_id: str = "Acme Corp") -> int:
    """Delete all sentiment results for a company. Returns count of deleted records."""
    db = SessionLocal()
    try:
        company_db_id = get_or_create_company(db, company_id)
        count = db.query(SentimentResult).filter(
            SentimentResult.company_id == company_db_id
        ).delete()
        db.commit()
        logger.info(f"Deleted {count} sentiment records for company {company_id}")
        return count
    except Exception as e:
        logger.error(f"Failed to delete sentiment results: {e}")
        db.rollback()
        return 0
    finally:
        db.close()


# =============================================================================
# RECOMMENDATIONS PERSISTENCE
# Note: Using a new model since original models.py doesn't have one
# =============================================================================

class RecommendationResult(Base):
    """Store product recommendation/association rules."""
    __tablename__ = "recommendation_results"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    rule_id = Column(String(50), nullable=True)
    if_product = Column(String(255), nullable=False)
    then_product = Column(String(255), nullable=False)
    support = Column(Float, nullable=True)
    confidence = Column(Float, nullable=False)
    lift = Column(Float, nullable=True)


# Create the table
Base.metadata.create_all(bind=engine)


def save_recommendation_results(
    recommendation_data: pd.DataFrame,
    company_id: str = "Acme Corp",
) -> bool:
    """
    Save recommendation/association rules to database.
    
    Args:
        recommendation_data: DataFrame with columns: IF, THEN, Confidence, Lift, Support
        company_id: Company identifier
    
    Returns:
        True if saved successfully, False otherwise
    """
    db = SessionLocal()
    try:
        company_db_id = get_or_create_company(db, company_id)
        
        # Delete existing recommendations for this company
        db.query(RecommendationResult).filter(
            RecommendationResult.company_id == company_db_id
        ).delete()
        db.commit()
        
        # Normalize column names
        df = recommendation_data.copy()
        
        # Find IF column
        if_col = None
        for col in ["IF (Buy)", "IF", "Antecedent", "if_product", "antecedents"]:
            if col in df.columns:
                if_col = col
                break
        
        # Find THEN column
        then_col = None
        for col in ["THEN (Recommend)", "THEN", "Consequent", "then_product", "consequents"]:
            if col in df.columns:
                then_col = col
                break
        
        if not if_col or not then_col:
            logger.error(f"Missing required IF/THEN columns. Found: {df.columns.tolist()}")
            return False
        
        # Insert records
        records_added = 0
        for idx, row in df.iterrows():
            try:
                rec = RecommendationResult(
                    company_id=company_db_id,
                    rule_id=str(row.get("RuleID", row.get("rule_id", idx))),
                    if_product=str(row[if_col]),
                    then_product=str(row[then_col]),
                    support=float(row.get("Support", row.get("support", 0.0))) if pd.notna(row.get("Support", row.get("support"))) else None,
                    confidence=float(row.get("Confidence", row.get("confidence", 0.0))),
                    lift=float(row.get("Lift", row.get("lift", 0.0))) if pd.notna(row.get("Lift", row.get("lift"))) else None,
                )
                db.add(rec)
                records_added += 1
            except Exception as e:
                logger.warning(f"Skipped recommendation record {idx}: {e}")
        
        db.commit()
        logger.info(f"Saved {records_added} recommendation records to database for company {company_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save recommendation results to database: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def get_recommendation_results(company_id: str = "Acme Corp") -> Optional[pd.DataFrame]:
    """
    Get recommendation/association rules from database.
    
    Returns:
        DataFrame with recommendation data or None if not found
    """
    db = SessionLocal()
    try:
        company_db_id = get_or_create_company(db, company_id)
        
        results = db.query(RecommendationResult).filter(
            RecommendationResult.company_id == company_db_id
        ).order_by(desc(RecommendationResult.lift)).all()
        
        if not results:
            logger.info(f"No recommendation results found in database for company {company_id}")
            return None
        
        # Convert to DataFrame
        data = []
        for r in results:
            data.append({
                "RuleID": r.rule_id,
                "IF (Buy)": r.if_product,
                "THEN (Recommend)": r.then_product,
                "Support": r.support,
                "Confidence": r.confidence,
                "Lift": r.lift,
            })
        
        df = pd.DataFrame(data)
        logger.info(f"Loaded {len(df)} recommendation records from database")
        return df
        
    except Exception as e:
        logger.error(f"Failed to get recommendation results from database: {e}")
        return None
    finally:
        db.close()


def delete_recommendation_results(company_id: str = "Acme Corp") -> int:
    """Delete all recommendation results for a company. Returns count of deleted records."""
    db = SessionLocal()
    try:
        company_db_id = get_or_create_company(db, company_id)
        count = db.query(RecommendationResult).filter(
            RecommendationResult.company_id == company_db_id
        ).delete()
        db.commit()
        logger.info(f"Deleted {count} recommendation records for company {company_id}")
        return count
    except Exception as e:
        logger.error(f"Failed to delete recommendation results: {e}")
        db.rollback()
        return 0
    finally:
        db.close()


# =============================================================================
# BULK OPERATIONS
# =============================================================================

def delete_all_analytics_for_company(company_id: str = "Acme Corp") -> Dict[str, int]:
    """Delete all analytics results for a company. Used during cascade delete."""
    return {
        "forecasts": delete_forecast_results(company_id),
        "rfm": delete_rfm_results(company_id),
        "sentiment": delete_sentiment_results(company_id),
        "recommendations": delete_recommendation_results(company_id),
    }


def sync_csv_to_database(company_id: str = "Acme Corp", data_dir: Path = None) -> Dict[str, bool]:
    """
    One-time sync of existing CSV files to database.
    Call this during startup to migrate existing data.
    
    Returns:
        Dict with sync status for each analytics type
    """
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / "data"
    
    status = {}
    
    # Sync RFM
    rfm_path = data_dir / "rfm_table.csv"
    if rfm_path.exists():
        try:
            df = pd.read_csv(rfm_path)
            if not df.empty:
                status["rfm"] = save_rfm_results(df, company_id)
            else:
                status["rfm"] = False
        except Exception as e:
            logger.warning(f"Failed to sync RFM: {e}")
            status["rfm"] = False
    else:
        status["rfm"] = False
    
    # Sync Sentiment
    sentiment_path = data_dir / "sentiment_results.csv"
    if sentiment_path.exists():
        try:
            df = pd.read_csv(sentiment_path)
            if not df.empty:
                status["sentiment"] = save_sentiment_results(df, company_id)
            else:
                status["sentiment"] = False
        except Exception as e:
            logger.warning(f"Failed to sync sentiment: {e}")
            status["sentiment"] = False
    else:
        status["sentiment"] = False
    
    # Sync Recommendations
    recs_path = data_dir / "product_recommendations.csv"
    if recs_path.exists():
        try:
            df = pd.read_csv(recs_path)
            if not df.empty:
                status["recommendations"] = save_recommendation_results(df, company_id)
            else:
                status["recommendations"] = False
        except Exception as e:
            logger.warning(f"Failed to sync recommendations: {e}")
            status["recommendations"] = False
    else:
        status["recommendations"] = False
    
    # Sync Forecast
    forecast_path = data_dir / "sales_forecast.csv"
    if forecast_path.exists():
        try:
            df = pd.read_csv(forecast_path)
            if not df.empty:
                # Convert to list of dicts for JSON storage
                forecast_data = df.to_dict(orient="records")
                status["forecast"] = save_forecast_results(
                    forecast_data, 
                    company_id, 
                    model_type="LinearRegression"
                )
            else:
                status["forecast"] = False
        except Exception as e:
            logger.warning(f"Failed to sync forecast: {e}")
            status["forecast"] = False
    else:
        status["forecast"] = False
    
    logger.info(f"CSV to Database sync complete: {status}")
    return status
