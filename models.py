from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, BLOB
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)  # Store securely hashed password
    created_at = Column(DateTime, default=datetime.now)

    # Relationship to URLs
    urls = relationship("URL", backref="user", lazy="dynamic")

class URL(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    secret_key = Column(String, unique=True, index=True)
    custom_key = Column(String(20), unique=True)
    target_url = Column(String, index=True)
    url = Column(String, index=True)
    is_active = Column(Boolean, default=True)
    clicks = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.id"))  # Foreign key to user
    
class Click(Base):
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True, index=True)
    url_id = Column(Integer, ForeignKey("urls.id"))
    timestamp = Column(DateTime, default=datetime.now)
    ip_address = Column(String)