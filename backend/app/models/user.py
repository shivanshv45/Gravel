from sqlalchemy import Column, Integer, String, DateTime
import datetime
from app.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="developer")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
