"""Subscription API endpoints for SaaS tier management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.subscriptions import (
    can_access_feature,
    cancel_subscription,
    check_subscription_status,
    get_or_create_subscription,
    upgrade_subscription,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/status")
def get_status(
    user_email: str = Query(..., description="User email address"),
    db: Session = Depends(get_db),
):
    """
    Get subscription status and feature access for a user.
    """
    return check_subscription_status(db, user_email)


@router.post("/upgrade")
def upgrade(
    user_email: str = Query(..., description="User email address"),
    tier: str = Query(..., description="Target tier: free, premium, enterprise"),
    db: Session = Depends(get_db),
):
    """
    Upgrade a user's subscription tier.
    """
    if tier not in ["free", "premium", "enterprise"]:
        raise HTTPException(status_code=400, detail="Invalid tier. Must be free, premium, or enterprise")
    
    subscription = upgrade_subscription(db, user_email, tier)
    return check_subscription_status(db, user_email)


@router.post("/cancel")
def cancel(
    user_email: str = Query(..., description="User email address"),
    db: Session = Depends(get_db),
):
    """
    Cancel a user's subscription (downgrade to free).
    """
    subscription = cancel_subscription(db, user_email)
    return check_subscription_status(db, user_email)


@router.get("/check-feature")
def check_feature(
    user_email: str = Query(..., description="User email address"),
    feature: str = Query(..., description="Feature to check access for"),
    db: Session = Depends(get_db),
):
    """
    Check if a user can access a specific feature.
    """
    return {
        "user_email": user_email,
        "feature": feature,
        "can_access": can_access_feature(db, user_email, feature),
    }
