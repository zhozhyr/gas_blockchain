from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@db:5432/gas_db"
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class BlockReference(Base):
    __tablename__ = "blocks"
    id = Column(Integer, primary_key=True, index=True)
    block_hash = Column(String, unique=True, nullable=False)
    timestamp = Column(DateTime, default=func.now())


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db

