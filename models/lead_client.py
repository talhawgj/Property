from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime
class LeadClientBase(SQLModel):
    brokerage: str
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    county: str = Field(index=True, unique=True)
    master_phone: str
class LeadClient(LeadClientBase, table=True):
    __tablename__ = "lead_clients"
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    updated_at: datetime = Field(default_factory=datetime.now)
class LeadClientCreate(LeadClientBase):
    pass