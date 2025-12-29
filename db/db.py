from sqlmodel import SQLModel, create_engine, text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession
from config import config
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
import logging

logger = logging.getLogger(__name__)

engine = AsyncEngine(create_engine(
    url=config.DATABASE_URL,
    echo=False,  # Disable echo to reduce log spam
    pool_size=100,  # Keep 100 persistent connections in pool
    max_overflow=40,  # Allow up to 15 additional overflow connections
    pool_timeout=30,  # Fail after 30s if no connection available
    pool_recycle=1800,  # Recycle connections after 30 minutes (before PostgreSQL times out)
    pool_pre_ping=True,  # Check connection health before using
    pool_use_lifo=True,  # Use most recently returned connection first (keeps pool smaller)
    connect_args={
        "server_settings": {
            "application_name": "fastapi_gis_app",
        },
        "timeout": 10,  
        "command_timeout": 60, 
    },
))


async def init_db():
    """Import database."""
    try:
        logger.info("Starting database initialization...")
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT PostGIS_Version();"))
            print(result.scalar())
            # from models.job import BatchJob
            # await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}", exc_info=True)
        raise
async def get_session() -> AsyncSession: 
    logger.debug("Creating new database session")
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {str(e)}", exc_info=True)
            raise
        finally:
            logger.debug("Closing database session")

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def dispose_engine():
    """Dispose of the database engine and close all connections."""
    logger.info("Disposing database engine and closing connections...")
    await engine.dispose()
    logger.info("Database engine disposed successfully")

