from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, Relationship
from .check import _utcnow_naive


class User(SQLModel, table=True):
    id: str = Field(primary_key=True)  # Clerk user ID
    email: str = Field(unique=True, index=True)
    name: Optional[str] = None
    credits: int = Field(default=3)  # Start with 3 free credits
    total_credits_used: int = Field(default=0)
    credit_balance_pence: int = Field(
        default=0, description="Prepaid agent credit balance in integer pence (GBP)"
    )
    external_id: Optional[str] = Field(
        default=None,
        max_length=100,
        sa_column_kwargs={"unique": True, "index": True},
        description="External identity (e.g. 'skyfire:user123' or 'x402:eip155:8453:0xabc')",
    )

    # Push notification settings
    push_token: Optional[str] = None
    push_notifications_enabled: bool = Field(default=True)
    platform: Optional[str] = None  # 'ios' or 'android'
    device_id: Optional[str] = None

    # Email notification settings
    email_notifications_enabled: bool = Field(default=True)
    email_check_completion: bool = Field(default=True)
    email_check_failure: bool = Field(default=True)
    email_weekly_digest: bool = Field(default=False)
    email_marketing: bool = Field(default=False)

    created_at: datetime = Field(default_factory=_utcnow_naive)
    updated_at: datetime = Field(default_factory=_utcnow_naive)

    # Relationships
    subscription: Optional["Subscription"] = Relationship(back_populates="user")
    checks: List["Check"] = Relationship(back_populates="user")


class Subscription(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = Field(foreign_key="user.id", unique=True)
    plan: str = Field(index=True)  # 'starter' or 'professional'
    status: str = Field(default="active")  # 'active', 'cancelled', 'past_due'
    credits_per_month: int
    credits_remaining: int
    # Billing cadence: 'month' or 'year'. Console monthly (£20/mo) and annual
    # (£200/yr) both map to plan 'console' with 200 credits/month; this records
    # which cadence so the dashboard can show the right price. Existing rows
    # default to 'month' via the migration's server_default.
    billing_interval: str = Field(default="month")
    current_period_start: datetime
    current_period_end: datetime
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    revenue_cat_id: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow_naive)
    updated_at: datetime = Field(default_factory=_utcnow_naive)

    # Relationships
    user: User = Relationship(back_populates="subscription")
