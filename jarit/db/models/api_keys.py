from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, text, Boolean
from sqlalchemy.orm import relationship
from jarit.db.database import Base


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    service_name = Column(String, nullable=False)
    api_key = Column(String, nullable=False)
    base_url = Column(String, nullable=True)
    is_active = Column(Boolean, server_default="TRUE", nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    user = relationship("User", back_populates="api_keys")
