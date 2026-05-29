from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Authentication
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    
    # Profile
    full_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    middle_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    
    # Email verification
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    
    # OAuth
    oauth_provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # google, github
    oauth_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    
    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    cvs = relationship("CV", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    __table_args__ = (
        {"comment": "User accounts for authentication and profile management"},
    )


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    
    # Verification code (OTP)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    
    # Token for email verification link
    token: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    
    # Status
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    __table_args__ = (
        {"comment": "Email verification codes and tokens for user registration"},
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    
    # Token
    token: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(String(512), unique=True, nullable=True)
    
    # Device/Browser info
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 max length
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Expiration
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    refresh_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    __table_args__ = (
        {"comment": "User sessions for JWT token management"},
    )