from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.exceptions import (
    DuplicateResourceError, AuthenticationError, DatabaseError, exception_to_http_exception
)
from app.models.user import User
from app.schemas.schemas import UserCreate, UserOut, Token
from app.api.deps import get_current_user
from pydantic import BaseModel, EmailStr, Field, field_validator

router = APIRouter(prefix="/auth", tags=["auth"])

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user with validated credentials.
    
    Raises:
        HTTPException: For duplicate email or validation errors
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_in.email).first()
        if existing_user:
            raise exception_to_http_exception(
                DuplicateResourceError("User", f"email {user_in.email}")
            )
        
        # Create new user
        hashed_password = get_password_hash(user_in.password)
        user = User(
            email=user_in.email,
            password_hash=hashed_password,
            name=user_in.name,
            role=user_in.role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise exception_to_http_exception(
            DatabaseError(f"Failed to register user: {str(e)}")
        )

@router.post("/login", response_model=Token)
def login(
    login_data: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login endpoint supporting JSON payload.
    Authenticates user with email and password.
    
    Raises:
        HTTPException: For invalid credentials
    """
    try:
        email = login_data.email
        password = login_data.password

        user = db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.password_hash):
            raise exception_to_http_exception(
                AuthenticationError("Invalid email or password")
            )
            
        access_token = create_access_token(subject=user.email)
        return {"access_token": access_token, "token_type": "bearer"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise exception_to_http_exception(
            DatabaseError(f"Login failed: {str(e)}")
        )

@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    """
    return current_user


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


@router.post("/change-password")
def change_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Allows an authenticated user to change their password.
    Verifies the current password before updating.
    """
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect."
        )
    if payload.new_password == payload.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from your current password."
        )
    current_user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Password updated successfully."}


@router.post("/refresh", response_model=Token)
def refresh_token(current_user: User = Depends(get_current_user)):
    """
    Issues a fresh JWT token for the authenticated user.
    Call this before the current token expires to stay logged in.
    """
    new_token = create_access_token(subject=current_user.email)
    return {"access_token": new_token, "token_type": "bearer"}
