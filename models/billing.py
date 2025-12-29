from pydantic import BaseModel, EmailStr
class PropertyInfo(BaseModel):
    propertyId: str
    county: str

class CheckoutIn(BaseModel):
    email: EmailStr
    properties: list[PropertyInfo]
    userId: str | None = None
    customerId: str | None = None
    allowPromoCodes: bool = True
    

class PortalIn(BaseModel):
    customerId: str