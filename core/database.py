import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Index
from core.config import settings

# Parche para Railway / Producción: SQLAlchemy async exige dialecto asyncpg explícito
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(db_url, echo=False)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    country = Column(String, index=True)
    category = Column(String, index=True)
    event_date = Column(DateTime)
    drive_url = Column(String)
    summary = Column(Text)
    impact_level = Column(Integer)
    created_at = Column(DateTime)
    
    # Robustness & Queue Tracking
    source_type = Column(String, default="manual")  # drive, manual, api
    hash = Column(String, unique=True, index=True)
    status = Column(String, default="pending", index=True) # pending | processed | failed
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    priority = Column(Integer, default=3, index=True) # 1: Alto, 2: Medio, 3: Normal
    video_url = Column(String, nullable=True)
    
    # 📢 Tracking de Distribución Automática
    published = Column(Boolean, default=False)
    published_at = Column(DateTime, nullable=True)
    distributed_to_discord = Column(Boolean, default=False)
    distributed_to_web = Column(Boolean, default=False)
    distributed_to_newsletter = Column(Boolean, default=False)
    distribution_timestamp = Column(DateTime, nullable=True)

    events = relationship("Event", back_populates="document")

# Índices explícitos
Index('idx_document_country', Document.country)
Index('idx_document_event_date', Document.event_date)

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    country = Column(String, index=True)
    type = Column(String, index=True)
    description = Column(Text)
    document_id = Column(Integer, ForeignKey("documents.id"))
    economic_impact_score = Column(Float)
    military_impact_score = Column(Float)
    created_at = Column(DateTime)
    
    # Nuevos campos sugeridos
    confidence_score = Column(Float)
    document = relationship("Document", back_populates="events")

class MarketData(Base):
    __tablename__ = "market_data"
    id = Column(Integer, primary_key=True, index=True)
    market_name = Column(String, index=True)
    probability = Column(Float)
    volume = Column(Float)
    timestamp = Column(DateTime)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    preferences = Column(Text)
    created_at = Column(DateTime)

async def get_db():
    async with SessionLocal() as session:
        yield session

async def check_db_connection():
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"DB Check Failed: {e}")
        return False
