from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
import datetime
from app.db import Base

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    local_path = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    files = relationship("CodeFile", back_populates="repository", cascade="all, delete-orphan")

class CodeFile(Base):
    __tablename__ = "code_files"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    file_path = Column(String, nullable=False)
    language = Column(String, nullable=True)
    raw_content = Column(Text, nullable=True)
    ast_metadata_json = Column(Text, nullable=True) 
    last_indexed_at = Column(DateTime, default=datetime.datetime.utcnow)

    repository = relationship("Repository", back_populates="files")
