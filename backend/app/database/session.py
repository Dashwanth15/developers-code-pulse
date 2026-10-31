import asyncio
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.metrics import DB_CONNECTION_STATUS, REDIS_CONNECTION_STATUS

logger = structlog.get_logger(__name__)
settings = get_settings()

engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global engine
    if engine is None:
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=1800,  # Recycle connections after 30m to avoid stale firewall drops
            pool_pre_ping=True,  # Test connection liveness before checking out from pool
        )
    return engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global async_session_factory
    if async_session_factory is None:
        async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_engine() -> None:
    """Closes the async database engine cleanly."""
    global engine, async_session_factory
    if engine is not None:
        await engine.dispose()
        engine = None
        async_session_factory = None
        logger.info("database_engine_closed")


async def check_db_connectivity() -> tuple[bool, str | None]:
    """
    Validates PostgreSQL connectivity by executing 'SELECT 1'.
    Returns (True, None) on success or (False, error_message) on failure.
    Updates Prometheus DB_CONNECTION_STATUS gauge.
    """

    async def _ping() -> tuple[bool, str | None]:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            val = result.scalar()
            if val == 1:
                DB_CONNECTION_STATUS.set(1)
                return True, None
            DB_CONNECTION_STATUS.set(0)
            return False, f"Unexpected query response: {val}"

    try:
        return await asyncio.wait_for(_ping(), timeout=3.0)
    except TimeoutError:
        logger.warning("db_connectivity_check_timed_out")
        DB_CONNECTION_STATUS.set(0)
        return False, "Database connection timed out after 3.0s"
    except Exception as exc:
        logger.error("db_connectivity_check_failed", error=str(exc))
        DB_CONNECTION_STATUS.set(0)
        return False, str(exc)


async def check_redis_connectivity() -> tuple[bool, str | None]:
    """
    Validates Redis connectivity via a PING command.
    Returns (True, None) on success or (False, error_message) on failure.
    Updates Prometheus REDIS_CONNECTION_STATUS gauge.
    """
    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            socket_timeout=3.0,
            socket_connect_timeout=3.0,
        )
        res = await client.ping()
        await client.aclose()
        if res:
            REDIS_CONNECTION_STATUS.set(1)
            return True, None
        REDIS_CONNECTION_STATUS.set(0)
        return False, "Redis ping returned falsy"
    except Exception as exc:
        logger.error("redis_connectivity_check_failed", error=str(exc))
        REDIS_CONNECTION_STATUS.set(0)
        return False, str(exc)
