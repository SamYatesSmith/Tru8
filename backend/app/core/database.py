from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Configure SSL for asyncpg connection
# Set DATABASE_SSL=false for Fly.io internal network (no SSL needed)
async_connect_args = {} if settings.DATABASE_SSL else {"ssl": False}

# psycopg2 uses different SSL params than asyncpg
sync_connect_args = {} if settings.DATABASE_SSL else {"sslmode": "disable"}

# Async engine and session for main app
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args=async_connect_args,
)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine and session for synchronous operations
# Strip any SSL params from URL since we handle via connect_args
sync_database_url = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)
# Remove ssl param if present in URL (psycopg2 doesn't support it in DSN)
if "?ssl=" in sync_database_url or "&ssl=" in sync_database_url:
    import re

    sync_database_url = re.sub(r"[?&]ssl=[^&]*", "", sync_database_url)
    # Clean up any doubled ? or trailing ?
    sync_database_url = sync_database_url.replace("?&", "?").rstrip("?")

sync_engine = create_engine(
    sync_database_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args=sync_connect_args,
)

sync_session = sessionmaker(sync_engine, class_=Session, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
