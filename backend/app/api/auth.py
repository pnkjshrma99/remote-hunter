"""Authentication API endpoints for user registration, login, and session management."""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    TokenRefresh,
    EmailVerificationRequest,
    GoogleOAuthRequest,
    GitHubOAuthRequest,
)
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    create_email_verification,
    verify_email_code,
    create_or_update_oauth_user,
    create_session,
    get_session_by_token,
    get_user_by_email,
    revoke_session,
    update_last_login,
    decode_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.models.user import User

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[int]:
    """Get current user ID from JWT token in Authorization header."""
    if not credentials:
        return None
    
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        return None
    
    sub = payload.get("sub")
    if sub is None:
        return None
    return int(sub)


@router.post("/register", response_model=UserResponse)
def register(user_in: UserRegister, request: Request, db: Session = Depends(get_db)):
    """
    Register a new user account.
    
    - **email**: User's email address
    - **password**: User's password (min 8 characters)
    - **full_name**: Optional full name
    """
    # Check if user already exists
    existing_user = get_user_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )
    
    # Create user
    user = create_user(db, user_in)
    
    # Create email verification
    verification = create_email_verification(db, user.email)
    
    # TODO: Send verification email with code
    # For now, we'll auto-verify in development
    if settings.debug:
        user.is_verified = True
    
    update_last_login(db, user)
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/login", response_model=TokenResponse)
def login(user_in: UserLogin, request: Request, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT tokens.
    
    - **email**: User's email address
    - **password**: User's password
    """
    user = authenticate_user(db, user_in.email, user_in.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    
    # Create session
    create_session(
        db=db,
        user_id=user.id,
        token=access_token,
        refresh_token=refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    
    update_last_login(db, user)
    db.commit()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(token_in: TokenRefresh, request: Request, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.
    
    - **refresh_token**: Valid refresh token
    """
    payload = decode_token(token_in.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    user_id = int(payload.get("sub"))
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
        )
    
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
        )
    
    # Create new tokens
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    
    # Revoke old session and create new one
    revoke_session(db, token_in.refresh_token)
    create_session(
        db=db,
        user_id=user.id,
        token=access_token,
        refresh_token=refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
def logout(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Logout user by revoking their session.
    """
    if credentials:
        revoke_session(db, credentials.credentials)
    db.commit()
    
    return {"status": "success", "message": "Logged out successfully"}


@router.post("/verify-email")
def verify_email(
    verification_in: EmailVerificationRequest,
    db: Session = Depends(get_db),
):
    """
    Verify user's email address with OTP code.
    
    - **email**: User's email address
    - **code**: 6-digit verification code
    """
    success = verify_email_code(db, verification_in.email, verification_in.code)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code",
        )
    db.commit()
    
    return {"status": "success", "message": "Email verified successfully"}


@router.post("/resend-verification")
def resend_verification(
    email: str,
    db: Session = Depends(get_db),
):
    """
    Resend email verification code.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Don't reveal if user exists
        return {"status": "success", "message": "If the email exists, a verification code has been sent"}
    
    if user.is_verified:
        return {"status": "success", "message": "Email is already verified"}
    
    # Create new verification
    create_email_verification(db, email)
    db.commit()
    
    return {"status": "success", "message": "Verification code sent to email"}


@router.post("/google", response_model=TokenResponse)
async def google_oauth(
    oauth_in: GoogleOAuthRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Login/Register using Google OAuth.

    - **access_token**: Google OAuth access token
    """
    from app.services.auth import validate_google_token

    # Validate token with Google
    user_info = await validate_google_token(oauth_in.access_token)
    if not user_info or not user_info.get("email"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google OAuth token",
        )

    email = user_info["email"]
    oauth_id = user_info.get("sub")
    full_name = user_info.get("name")

    # Create or update user
    user = create_or_update_oauth_user(
        db=db,
        email=email,
        oauth_provider="google",
        oauth_id=oauth_id,
        full_name=full_name,
    )

    # Create tokens
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )

    # Create session
    create_session(
        db=db,
        user_id=user.id,
        token=access_token,
        refresh_token=refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    update_last_login(db, user)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/github", response_model=TokenResponse)
async def github_oauth(
    oauth_in: GitHubOAuthRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Login/Register using GitHub OAuth.

    - **access_token**: GitHub OAuth access token (optional if using code)
    - **code**: GitHub OAuth authorization code (optional if using access_token)
    """
    from app.services.auth import validate_github_token, exchange_github_code_for_token

    # If code is provided, exchange it for access token
    if oauth_in.code:
        access_token = await exchange_github_code_for_token(oauth_in.code)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to exchange GitHub OAuth code for access token",
            )
    elif oauth_in.access_token:
        access_token = oauth_in.access_token
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either access_token or code must be provided",
        )

    # Validate token with GitHub
    user_info = await validate_github_token(access_token)
    if not user_info or not user_info.get("email"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub OAuth token or no verified email found",
        )

    email = user_info["email"]
    oauth_id = str(user_info.get("id"))
    full_name = user_info.get("name") or user_info.get("login")

    # Create or update user
    user = create_or_update_oauth_user(
        db=db,
        email=email,
        oauth_provider="github",
        oauth_id=oauth_id,
        full_name=full_name,
    )

    # Create tokens
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )

    # Create session
    create_session(
        db=db,
        user_id=user.id,
        token=access_token,
        refresh_token=refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    update_last_login(db, user)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
def get_current_user(
    user_id: Optional[int] = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Get current authenticated user information.
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    user = db.get(User, int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return user


@router.get("/status")
def auth_status(
    user_id: Optional[int] = Depends(get_current_user_id),
):
    """
    Check authentication status.
    """
    return {
        "is_authenticated": user_id is not None,
        "user_id": user_id,
    }