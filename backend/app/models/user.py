from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

class User(SQLModel, table=True):
    id: str = Field(primary_key=True)  # Clerk user ID
    email: str = Field(unique=True, index=True)
    name: Optional[str] = None
    credits: int = Field(default=3)  # Start with 3 free credits
    total_credits_used: int = Field(default=0)
    
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

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    subscription: Optional["Subscription"] = Relationship(back_populates="user")
    checks: List["Check"] = Relationship(back_populates="user")

class Subscription(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = Field(foreign_key="user.id", unique=True)
    plan: str = Field(index=True)  # 'starter' or 'pro'
    status: str = Field(default="active")  # 'active', 'cancelled', 'past_due'
    credits_per_month: int
    credits_remaining: int
    current_period_start: datetime
    current_period_end: datetime
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    revenue_cat_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="subscription")