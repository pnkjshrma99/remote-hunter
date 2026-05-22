"""Authentication service for user management, JWT tokens, and email verification."""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import httpx
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.config import get_settings
from app.models.user import User, EmailVerification, Session as UserSession
from app.schemas.auth import UserRegister

settings = get_settings()

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def _normalize_token_subject(data: dict) -> dict:
    if "sub" in data and not isinstance(data["sub"], str):
        data = data.copy()
        data["sub"] = str(data["sub"])
    return data


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = _normalize_token_subject(data.copy())
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token."""
    to_encode = _normalize_token_subject(data.copy())
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def create_user(db: OrmSession, user_in: UserRegister) -> User:
    """Create a new user."""
    hashed_password = get_password_hash(user_in.password)
    verification_token = secrets.token_urlsafe(32)
    
    user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        is_verified=False,
        verification_token=verification_token,
    )
    db.add(user)
    db.flush()
    return user


def get_user_by_email(db: OrmSession, email: str) -> Optional[User]:
    """Get a user by email address."""
    return db.scalar(select(User).where(User.email == email))


def get_user_by_id(db: OrmSession, user_id: int) -> Optional[User]:
    """Get a user by ID."""
    return db.scalar(select(User).where(User.id == user_id))


def authenticate_user(db: OrmSession, email: str, password: str) -> Optional[User]:
    """Authenticate a user with email and password."""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not user.hashed_password:
        return None  # User registered via OAuth
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_email_verification(db: OrmSession, email: str) -> EmailVerification:
    """Create an email verification record with OTP code."""
    # Generate 6-digit OTP
    code = "".join([secrets.choice(string.digits) for _ in range(6)])
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    verification = EmailVerification(
        email=email,
        code=code,
        token=token,
        expires_at=expires_at,
        is_used=False,
    )
    db.add(verification)
    db.flush()
    return verification


def verify_email_code(db: OrmSession, email: str, code: str) -> bool:
    """Verify an email verification code."""
    verification = db.scalar(
        select(EmailVerification)
        .where(EmailVerification.email == email)
        .where(EmailVerification.code == code)
        .where(EmailVerification.is_used == False)
        .where(EmailVerification.expires_at > datetime.utcnow())
        .order_by(EmailVerification.created_at.desc())
        .limit(1)
    )
    
    if not verification:
        return False
    
    # Mark as used
    verification.is_used = True
    db.flush()
    
    # Mark user as verified
    user = get_user_by_email(db, email)
    if user:
        user.is_verified = True
        user.verification_token = None
    
    return True


def verify_email_token(db: OrmSession, token: str) -> bool:
    """Verify an email verification token (from email link)."""
    verification = db.scalar(
        select(EmailVerification)
        .where(EmailVerification.token == token)
        .where(EmailVerification.is_used == False)
        .where(EmailVerification.expires_at > datetime.utcnow())
    )
    
    if not verification:
        return False
    
    # Mark as used
    verification.is_used = True
    db.flush()
    
    # Mark user as verified
    user = get_user_by_email(db, verification.email)
    if user:
        user.is_verified = True
        user.verification_token = None
    
    return True


def create_session(
    db: OrmSession,
    user_id: int,
    token: str,
    refresh_token: Optional[str] = None,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> UserSession:
    """Create a new session for a user."""
    session = UserSession(
        user_id=user_id,
        token=token,
        refresh_token=refresh_token,
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        refresh_expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        is_active=True,
    )
    db.add(session)
    db.flush()
    return session


def get_session_by_token(db: OrmSession, token: str) -> Optional[UserSession]:
    """Get a session by access token."""
    return db.scalar(
        select(UserSession)
        .where(UserSession.token == token)
        .where(UserSession.is_active == True)
        .where(UserSession.expires_at > datetime.utcnow())
    )


def get_session_by_refresh_token(db: OrmSession, refresh_token: str) -> Optional[UserSession]:
    """Get a session by refresh token."""
    return db.scalar(
        select(UserSession)
        .where(UserSession.refresh_token == refresh_token)
        .where(UserSession.is_active == True)
        .where(UserSession.refresh_expires_at > datetime.utcnow())
    )


def revoke_session(db: OrmSession, token: str) -> bool:
    """Revoke a session by access or refresh token."""
    session = get_session_by_token(db, token)
    if not session:
        session = get_session_by_refresh_token(db, token)
    if session:
        session.is_active = False
        db.flush()
        return True
    return False


def revoke_all_user_sessions(db: OrmSession, user_id: int) -> int:
    """Revoke all sessions for a user."""
    sessions = db.scalars(select(UserSession).where(UserSession.user_id == user_id))
    count = 0
    for session in sessions:
        session.is_active = False
        count += 1
    db.flush()
    return count


def update_last_login(db: OrmSession, user: User) -> None:
    """Update user's last login timestamp."""
    user.last_login_at = datetime.utcnow()
    db.flush()


def create_or_update_oauth_user(
    db: OrmSession,
    email: str,
    oauth_provider: str,
    oauth_id: str,
    full_name: Optional[str] = None,
) -> User:
    """Create or update a user via OAuth."""
    user = get_user_by_email(db, email)

    if user:
        # Update OAuth info
        user.oauth_provider = oauth_provider
        user.oauth_id = oauth_id
        if full_name and not user.full_name:
            user.full_name = full_name
        user.is_verified = True  # OAuth providers verify email
        db.flush()
    else:
        # Create new user
        user = User(
            email=email,
            full_name=full_name,
            oauth_provider=oauth_provider,
            oauth_id=oauth_id,
            is_verified=True,  # OAuth providers verify email
        )
        db.add(user)
        db.flush()

    return user


async def validate_google_token(access_token: str) -> Optional[dict]:
    """Validate Google OAuth access token and return user info."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json()
            return None
    except Exception:
        return None


async def validate_github_token(access_token: str) -> Optional[dict]:
    """Validate GitHub OAuth access token and return user info."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
            if response.status_code == 200:
                user_data = response.json()
                # Get user email (may need separate call for private emails)
                email_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0,
                )
                if email_response.status_code == 200:
                    emails = email_response.json()
                    # Find primary email
                    primary_email = next(
                        (e["email"] for e in emails if e["primary"] and e["verified"]),
                        None
                    )
                    if primary_email:
                        user_data["email"] = primary_email
                return user_data
            return None
    except Exception:
        return None


async def exchange_github_code_for_token(code: str) -> Optional[str]:
    """Exchange GitHub OAuth code for access token."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": settings.github_oauth_client_id,
                    "client_secret": settings.github_oauth_client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"},
                timeout=10.0,
            )
            if response.status_code == 200:
                token_data = response.json()
                return token_data.get("access_token")
            return None
    except Exception:
        return None