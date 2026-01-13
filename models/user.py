from sqlmodel import SQLModel, Field, Column
from sqlalchemy import String, DateTime
from datetime import datetime
from typing import Optional

class User(SQLModel, table=True):
    """
    User model for authentication and authorization.
    Stores user credentials and metadata.
    """
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(sa_column=Column(String, unique=True, index=True, nullable=False))
    hashed_password: str = Field(sa_column=Column(String, nullable=False))
    full_name: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, is_active={self.is_active})>"
