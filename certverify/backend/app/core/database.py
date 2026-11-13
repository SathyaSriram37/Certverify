from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

# Async Engine (PostgreSQL via asyncpg, compatible with Supabase)
async_db_url = settings.DATABASE_URL
if async_db_url.startswith("postgresql://"):
    async_db_url = async_db_url.replace("postgresql://", "postgresql+asyncpg://")

# Remove pgbouncer query parameter if present for asyncpg compatibility
if "?pgbouncer=true" in async_db_url:
    async_db_url = async_db_url.replace("?pgbouncer=true", "")
elif "&pgbouncer=true" in async_db_url:
    async_db_url = async_db_url.replace("&pgbouncer=true", "")

connect_args = {}
if "6543" in async_db_url or "pooler" in async_db_url or "supabase" in async_db_url:
    connect_args["statement_cache_size"] = 0
    connect_args["prepared_statement_cache_size"] = 0

engine = create_async_engine(
    async_db_url,
    echo=False,
    future=True,
    pool_pre_ping=False,
    pool_recycle=300,
    pool_timeout=15,
    pool_size=15,
    max_overflow=25,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync Engine (for Celery workers and synchronous tasks)
sync_db_url = settings.DATABASE_SYNC_URL or settings.DATABASE_URL
if "+asyncpg" in sync_db_url:
    sync_db_url = sync_db_url.replace("postgresql+asyncpg://", "postgresql://")

sync_engine = create_engine(
    sync_db_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
