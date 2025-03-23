from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/gas_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Определяем таблицу через ORM
class BlockReference(Base):
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True, index=True)
    block_hash = Column(String, unique=True, nullable=False)
    timestamp = Column(DateTime, default=func.now())

# Функция для работы с сессией БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

