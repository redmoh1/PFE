"""
Authentication API routes.

ENDPOINTS:
- POST /api/auth/register - Register new user
- POST /api/auth/login - Login and get JWT token
- GET /api/auth/me - Get current user info
- POST /api/auth/refresh - Refresh access token
"""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from .database.connection import get_db
from .database.models import User, UserRole, Company
from .auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# -------------------------------------------------
# Request/Response Models
# -------------------------------------------------
class UserRegister(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str
    full_name: str
    company_id: int
    role: UserRole = UserRole.VIEWER


class UserResponse(BaseModel):
    """User response model (without password)."""
    id: int
    email: str
    full_name: str
    role: str
    company_id: int
    company_name: Optional[str] = None
    is_active: bool
    created_at: str
    last_login: Optional[str] = None
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str


# -------------------------------------------------
# Authentication Endpoints
# -------------------------------------------------
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """Register a new user.
    
    **Requirements:**
    - Unique email address
    - Valid company_id
    - Password minimum 8 characters
    
    **Returns:**
    - User object (without password)
    """
    # Validate password strength
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Verify company exists
    company = db.query(Company).filter(Company.id == user_data.company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {user_data.company_id} not found"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role=user_data.role,
        company_id=user_data.company_id,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role.value,
        company_id=new_user.company_id,
        company_name=company.name,
        is_active=new_user.is_active,
        created_at=new_user.created_at.isoformat(),
        last_login=new_user.last_login.isoformat() if new_user.last_login else None,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login and receive JWT access token.
    
    **Returns:**
    - JWT access token (valid for 24 hours by default)
    - User information
    """
    user = authenticate_user(db, login_data.email, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "role": user.role.value,
            "company_id": user.company_id,
        },
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            company_id=user.company_id,
            company_name=user.company.name,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None,
        )
    )


@router.post("/login/form", response_model=TokenResponse)
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login endpoint compatible with OAuth2PasswordRequestForm.
    
    Used by FastAPI's automatic Swagger UI authentication.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "role": user.role.value,
            "company_id": user.company_id,
        },
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            company_id=user.company_id,
            company_name=user.company.name,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None,
        )
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user's information.
    
    **Requires:**
    - Valid JWT token in Authorization header
    
    **Returns:**
    - User profile information
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        company_id=current_user.company_id,
        company_name=current_user.company.name,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat(),
        last_login=current_user.last_login.isoformat() if current_user.last_login else None,
    )


@router.get("/verify")
def verify_token(current_user: User = Depends(get_current_user)):
    """Verify if a token is valid.
    
    Returns:
        {"valid": True, "email": "user@example.com"}
    """
    return {
        "valid": True,
        "email": current_user.email,
        "role": current_user.role.value,
        "company_id": current_user.company_id,
    }
