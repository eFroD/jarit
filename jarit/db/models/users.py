from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from enum import Enum
from sqlalchemy.sql import func
from jarit.db.database import Base
from sqlalchemy.orm import relationship


class UserRole(Enum):
    ADMIN = "ADMIN"
    USER = "USER"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(
        SQLEnum(UserRole, name="user_role_enum"), default=UserRole.USER, nullable=False
    )
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    api_keys = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )
