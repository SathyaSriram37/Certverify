import logging
import redis.asyncio as aioredis
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine

logger = logging.getLogger("certverify.startup")


async def validate_startup() -> None:
    logger.info("Running CertVerify AI startup integrity validation...")

    if settings.SECRET_KEY.startswith("change-this"):
        logger.warning(
            "CRITICAL SECURITY WARNING: SECRET_KEY is set to default template value! Change it immediately for production."
        )

    # Test Database (Supabase PostgreSQL / asyncpg)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✓ Database connection verified successfully.")
    except Exception as exc:
        logger.warning(f"! Database connection check returned warning/error: {exc}")

    # Test Redis
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        await r.close()
        logger.info("✓ Redis broker connection verified successfully.")
    except Exception as exc:
        logger.warning(f"! Redis broker connection check returned warning/error: {exc}")

    logger.info("Startup validation sequence completed.")

