from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db import get_session
from models import LeadClient, LeadClientCreate
router = APIRouter(prefix="/lead-clients", tags=["Lead Clients"])

@router.get("/", response_model=List[LeadClient])
async def list_lead_clients(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(LeadClient))
    return result.scalars().all()

@router.post("/", response_model=LeadClient)
async def create_lead_client(client: LeadClientCreate, db: AsyncSession = Depends(get_session)):
    # Check if county already exists
    existing = await db.execute(select(LeadClient).where(LeadClient.county == client.county))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"County {client.county} already has a master number.")
    lead_client = LeadClient.model_validate(client)
    db.add(lead_client)
    await db.commit()
    await db.refresh(lead_client)
    return lead_client

@router.put("/{client_id}", response_model=LeadClient)
async def update_lead_client(client_id: int, updates: LeadClient, db: AsyncSession = Depends(get_session)):
    client = await db.get(LeadClient, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    client.brokerage = updates.brokerage
    client.contact_person = updates.contact_person
    client.contact_phone = updates.contact_phone
    client.contact_email = updates.contact_email
    client.county = updates.county
    client.master_phone = updates.master_phone
    
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client

@router.delete("/{client_id}")
async def delete_lead_client(client_id: int, db: AsyncSession = Depends(get_session)):
    client = await db.get(LeadClient, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    await db.delete(client)
    await db.commit()
    return {"message": "Deleted successfully"}