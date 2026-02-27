"""
Database models for authentication and data persistence.

ARCHITECTURE:
- Users: Authentication and authorization
- Companies: Multi-tenant data isolation
- Forecasts: Store prediction results
- RFM Results: Customer segmentation cache
- Sentiment: Analyzed reviews cache

WHY SQLAlchemy:
- Type safety and validation
- Relationship management
- Database agnostic (SQLite/PostgreSQL)
- Migration support via Alembic
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    ForeignKey, Text, JSON, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from passlib.context import CryptContext

Base = declarative_base()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# -------------------------------------------------
# User Management
# -------------------------------------------------
class UserRole(str, Enum):
    """User roles for authorization."""
    ADMIN = "admin"  # Full access: manage users, companies, all data
    ANALYST = "analyst"  # Read + analyze: view data, run analytics
    VIEWER = "viewer"  # Read-only: view dashboards only


class NotificationType(str, Enum):
    """Notification categories."""
    ALERT = "ALERT"
    WARNING = "WARNING"
    INFO = "INFO"


class User(Base):
    """User model for authentication and authorization.
    
    Features:
    - Email-based authentication
    - Bcrypt password hashing
    - Role-based access control (RBAC)
    - Company association for data isolation
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="users")
    
    def verify_password(self, plain_password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(plain_password, self.hashed_password)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password for storing."""
        return pwd_context.hash(password)
    
    def __repr__(self):
        return f"<User(email='{self.email}', role='{self.role}', company='{self.company.name if self.company else None}')>"


# -------------------------------------------------
# Company Management
# -------------------------------------------------
class Company(Base):
    """Company model for multi-tenant data isolation.
    
    Each company has:
    - Separate data files (sales, customers, reviews)
    - Own users with different roles
    - Isolated analytics results
    """
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)  # URL-safe name
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Data paths (relative to DATA_DIR)
    data_directory = Column(String(512), nullable=False)  # e.g., "Acme Corp"
    
    # Relationships
    users = relationship("User", back_populates="company")
    forecasts = relationship("ForecastResult", back_populates="company", cascade="all, delete-orphan")
    rfm_results = relationship("RFMResult", back_populates="company", cascade="all, delete-orphan")
    sentiment_results = relationship("SentimentResult", back_populates="company", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Company(name='{self.name}', users={len(self.users)})>"


# -------------------------------------------------
# ML Results Storage
# -------------------------------------------------
class ForecastResult(Base):
    """Store sales forecast results for caching and comparison.
    
    WHY:
    - Avoid recomputing forecasts
    - Track model performance over time
    - Enable A/B testing of models
    """
    __tablename__ = "forecast_results"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Model metadata
    model_type = Column(String(50), nullable=False)  # "Prophet", "LinearRegression"
    model_version = Column(Integer, nullable=False)
    forecast_periods = Column(Integer, nullable=False)  # Number of months forecasted
    
    # Metrics
    mae = Column(Float, nullable=True)
    rmse = Column(Float, nullable=True)
    mape = Column(Float, nullable=True)
    r2 = Column(Float, nullable=True)
    
    # Forecast data (JSON format)
    forecast_data = Column(JSON, nullable=False)  # [{"date": "2026-02", "yhat": 1000, "yhat_lower": 900, "yhat_upper": 1100}, ...]
    
    # Components (for Prophet)
    trend_data = Column(JSON, nullable=True)
    seasonality_data = Column(JSON, nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="forecasts")
    
    def __repr__(self):
        return f"<ForecastResult(company='{self.company.name}', model='{self.model_type}', periods={self.forecast_periods})>"


class RFMResult(Base):
    """Store RFM segmentation results for customers.
    
    WHY:
    - Cache expensive computations
    - Track customer segment changes over time
    - Enable customer journey analysis
    """
    __tablename__ = "rfm_results"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Customer info
    customer_id = Column(String(255), nullable=False, index=True)
    customer_name = Column(String(255), nullable=True)
    
    # RFM scores
    recency = Column(Integer, nullable=False)
    frequency = Column(Integer, nullable=False)
    monetary = Column(Float, nullable=False)
    
    # RFM ratings (1-5)
    r_score = Column(Integer, nullable=False)
    f_score = Column(Integer, nullable=False)
    m_score = Column(Integer, nullable=False)
    
    # Segment
    rfm_segment = Column(String(50), nullable=False)  # "Champions", "At Risk", etc.
    
    # Relationships
    company = relationship("Company", back_populates="rfm_results")
    
    def __repr__(self):
        return f"<RFMResult(customer='{self.customer_id}', segment='{self.rfm_segment}')>"


class SentimentResult(Base):
    """Store Customer Feedback results for reviews.
    
    WHY:
    - Avoid re-analyzing same reviews
    - Track sentiment trends over time
    - Cache expensive Arabic NLP computations
    """
    __tablename__ = "sentiment_results"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Review info
    review_id = Column(String(255), nullable=True, index=True)
    review_text = Column(Text, nullable=False)
    review_date = Column(DateTime, nullable=True)
    
    # Customer Feedback
    sentiment = Column(String(20), nullable=False)  # "Positive", "Negative", "Neutral"
    confidence = Column(Float, nullable=False)
    polarity = Column(Float, nullable=False)
    analysis_method = Column(String(50), nullable=False)  # "arabic_bert", "textblob"
    
    # Optional: Product/Rating association
    product_id = Column(String(255), nullable=True, index=True)
    rating = Column(Integer, nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="sentiment_results")
    
    def __repr__(self):
        return f"<SentimentResult(sentiment='{self.sentiment}', confidence={self.confidence:.2f}, method='{self.analysis_method}')>"


# -------------------------------------------------
# Model Monitoring
# -------------------------------------------------
class ModelPerformanceLog(Base):
    """Track model performance over time for monitoring and drift detection.
    
    WHY:
    - Detect performance degradation
    - Identify when retraining is needed
    - Compare model versions
    """
    __tablename__ = "model_performance_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    logged_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Model info
    model_type = Column(String(50), nullable=False)
    model_version = Column(Integer, nullable=False)
    
    # Performance metrics
    mae = Column(Float, nullable=False)
    rmse = Column(Float, nullable=False)
    mape = Column(Float, nullable=True)
    
    # Data characteristics (for drift detection)
    training_samples = Column(Integer, nullable=False)
    test_samples = Column(Integer, nullable=False)
    feature_stats = Column(JSON, nullable=True)  # Mean, std, etc. of features
    
    # Alert flags
    performance_degraded = Column(Boolean, default=False)
    retrain_recommended = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<ModelPerformanceLog(model='{self.model_type}', version={self.model_version}, mape={self.mape:.2f}%)>"


class Notification(Base):
    """Persisted notification records."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String(255), nullable=True, index=True)
    message = Column(Text, nullable=False)
    type = Column(SQLEnum(NotificationType), default=NotificationType.INFO, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_read = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<Notification(id={self.id}, type='{self.type}', is_read={self.is_read})>"
