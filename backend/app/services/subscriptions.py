"""Subscription service for SaaS tier management."""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.subscription import UserSubscription


def get_or_create_subscription(db: Session, user_email: str) -> UserSubscription:
    """
    Get existing subscription or create a new free tier subscription.
    """
    subscription = db.scalar(
        select(UserSubscription).where(UserSubscription.user_email == user_email)
    )
    
    if not subscription:
        subscription = UserSubscription(
            user_email=user_email,
            tier="free",
            is_active=True,
        )
        db.add(subscription)
        db.flush()
    
    return subscription


def upgrade_subscription(
    db: Session,
    user_email: str,
    tier: str,
) -> UserSubscription:
    """
    Upgrade a user's subscription tier.
    """
    subscription = get_or_create_subscription(db, user_email)
    
    subscription.tier = tier
    subscription.is_active = True
    subscription.subscribed_at = datetime.utcnow()
    
    # Set expiration based on tier (simplified - in production would use payment processing)
    if tier == "premium":
        subscription.expires_at = datetime.utcnow() + timedelta(days=30)
    elif tier == "enterprise":
        subscription.expires_at = datetime.utcnow() + timedelta(days=365)
    else:
        subscription.expires_at = None
    
    db.flush()
    return subscription


def cancel_subscription(db: Session, user_email: str) -> UserSubscription:
    """
    Cancel a user's subscription (downgrade to free).
    """
    subscription = get_or_create_subscription(db, user_email)
    
    subscription.tier = "free"
    subscription.is_active = True
    subscription.expires_at = None
    
    db.flush()
    return subscription


def check_subscription_status(db: Session, user_email: str) -> dict:
    """
    Check if a user's subscription is active and what features they have access to.
    """
    subscription = get_or_create_subscription(db, user_email)
    
    is_active = True
    if subscription.expires_at and subscription.expires_at < datetime.utcnow():
        is_active = False
    
    # Define feature access by tier
    features = {
        "free": {
            "max_saved_searches": 3,
            "email_alerts": False,
            "analytics_dashboard": False,
            "advanced_filters": False,
            "all_sources": False,
        },
        "premium": {
            "max_saved_searches": 50,
            "email_alerts": True,
            "analytics_dashboard": True,
            "advanced_filters": True,
            "all_sources": True,
        },
        "enterprise": {
            "max_saved_searches": -1,  # unlimited
            "email_alerts": True,
            "analytics_dashboard": True,
            "advanced_filters": True,
            "all_sources": True,
            "api_access": True,
            "custom_integrations": True,
        },
    }
    
    tier_features = features.get(subscription.tier, features["free"])
    
    return {
        "user_email": user_email,
        "tier": subscription.tier,
        "is_active": is_active,
        "subscribed_at": subscription.subscribed_at.isoformat() if subscription.subscribed_at else None,
        "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
        "features": tier_features,
    }


def can_access_feature(db: Session, user_email: str, feature: str) -> bool:
    """
    Check if a user can access a specific feature based on their subscription tier.
    """
    status = check_subscription_status(db, user_email)
    return status["features"].get(feature, False)
