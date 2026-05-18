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
    # New SaaS roles (preferred)
    SUPER_ADMIN = "super_admin"        # System-wide access across all companies
    COMPANY_ADMIN = "company_admin"    # Full access within one company
    BRANCH_ADMIN = "branch_admin"      # Full access within one branch
    EMPLOYEE = "employee"              # Limited access within branch
    VIEWER = "viewer"                  # Read-only within company/branch scope

    # Legacy roles (kept for backward compatibility with existing tokens/data)
    ADMIN = "admin"
    BRANCH_MANAGER = "branch_manager"
    ANALYST = "analyst"


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
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_email_verified = Column(Boolean, default=True, nullable=False)
    email_verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="users")
    branch = relationship("Branch", back_populates="users", foreign_keys=[branch_id])
    verification_otps = relationship("EmailVerificationOTP", back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    
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
    branches = relationship("Branch", back_populates="company", cascade="all, delete-orphan")
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
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True, index=True)
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
    branch = relationship("Branch")
    
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
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True, index=True)
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
    branch = relationship("Branch")
    
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
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True, index=True)
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
    branch = relationship("Branch")
    
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
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True, index=True)
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
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True, index=True)
    product_name = Column(String(255), nullable=True, index=True)
    message = Column(Text, nullable=False)
    type = Column(SQLEnum(NotificationType), default=NotificationType.INFO, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_read = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<Notification(id={self.id}, type='{self.type}', is_read={self.is_read})>"


class Branch(Base):
    """Branch model for per-company branch management."""
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    city = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    company = relationship("Company", back_populates="branches")
    users = relationship("User", back_populates="branch", foreign_keys=[User.branch_id])
    manager = relationship("User", foreign_keys=[manager_id], lazy="joined")

    def __repr__(self):
        return f"<Branch(id={self.id}, name='{self.name}', city='{self.city}', is_active={self.is_active})>"


class EmailVerificationOTP(Base):
    """One-time verification code for activating newly registered accounts."""

    __tablename__ = "email_verification_otps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    otp_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=5, nullable=False)
    used = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="verification_otps")

    def __repr__(self):
        return f"<EmailVerificationOTP(user_id={self.user_id}, expires_at='{self.expires_at}', used={self.used})>"


class PasswordResetToken(Base):
    """Password reset token record with one-time-use semantics."""

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="password_reset_tokens")

    def __repr__(self):
        return f"<PasswordResetToken(user_id={self.user_id}, expires_at='{self.expires_at}', used={self.used})>"


class UploadMappingProfile(Base):
    """Saved per-tenant column mappings for future uploads."""

    __tablename__ = "upload_mapping_profiles"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(String(255), nullable=False, index=True)
    branch_id = Column(String(255), nullable=True, index=True)
    user_id = Column(String(255), nullable=True, index=True)
    dataset_type = Column(String(50), nullable=False, index=True)
    source_signature = Column(String(64), nullable=False, index=True)
    source_columns = Column(JSON, nullable=False)
    field_mapping = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<UploadMappingProfile(company_id='{self.company_id}', dataset_type='{self.dataset_type}')>"


class PendingDatasetUpload(Base):
    """Staged CSV upload awaiting manual column mapping confirmation."""

    __tablename__ = "pending_dataset_uploads"

    id = Column(String(64), primary_key=True, index=True)
    company_id = Column(String(255), nullable=False, index=True)
    branch_id = Column(String(255), nullable=True, index=True)
    user_id = Column(String(255), nullable=True, index=True)
    dataset_type = Column(String(50), nullable=False, index=True)
    original_file_name = Column(String(255), nullable=False)
    staged_file_path = Column(String(1024), nullable=False)
    column_signature = Column(String(64), nullable=False, index=True)
    extracted_columns = Column(JSON, nullable=False)
    preview_rows = Column(JSON, nullable=False)
    row_count = Column(Integer, nullable=False)
    replace_dataset_id = Column(Integer, nullable=True, index=True)
    status = Column(String(32), nullable=False, default="pending", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)

    def __repr__(self):
        return f"<PendingDatasetUpload(id='{self.id}', dataset_type='{self.dataset_type}', status='{self.status}')>"
