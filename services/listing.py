import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from schemas import PropertyListing

logger = logging.getLogger("batch_analysis")

class ListingService:
    """
    Handles saving user uploaded CSV rows into the PropertyListing table.
    """
    
    async def save_listing_from_csv(
        self, 
        session: AsyncSession, 
        gid: int, 
        row_data: Dict[str, Any], 
        analysis_summary: Dict[str, Any],
        batch_id: Optional[str] = None
    ) -> PropertyListing:
        try:
            # 1. Clean & Extract Data
            # Handle Price: "$100,000" -> 100000.0
            raw_price = row_data.get("Price") or row_data.get("sell_price") or row_data.get("ListPrice")
            price = None
            if raw_price:
                try:
                    price = float(str(raw_price).replace("$", "").replace(",", ""))
                except (ValueError, TypeError):
                    pass

            # Extract other common fields with fallback keys
            agent = row_data.get("AgentName") or row_data.get("Agent") or row_data.get("Seller")
            owner = row_data.get("PartyOwner1NameFull") or row_data.get("OwnerName")
            status = row_data.get("Status", "Active")
            address = row_data.get("StreetAddress") or row_data.get("Address") or row_data.get("SitusAddress")
            city = row_data.get("City") or row_data.get("SitusCity")
            county = row_data.get("County") or analysis_summary.get("parcels", {}).get("county")
            
            # Get acreage from analysis if not in CSV
            acreage_val = row_data.get("Acres") or analysis_summary.get("parcels", {}).get("acreage", 0)
            try:
                acreage = float(acreage_val)
            except:
                acreage = 0.0

            # 2. Check for existing listing (Upsert Logic)
            # We assume one active listing per GID per Batch, or generally one per GID
            stmt = select(PropertyListing).where(PropertyListing.gid == gid)
            result = await session.execute(stmt)
            existing = result.scalars().first()

            # Merge Analysis Images into source_data for easy frontend access
            images = {
                "aerial": analysis_summary.get("image_url"),
                "flood": analysis_summary.get("flood_image_url"),
                "contour": analysis_summary.get("contour_image_url"),
                "road": analysis_summary.get("road_frontage_image_url")
            }
            
            full_data = {
                **row_data, 
                "analysis_images": images,
                "analysis_summary": {
                    "flood_zone": analysis_summary.get("flood_hazard", {}).get("flood_zone_summary"),
                    "buildable": analysis_summary.get("buildable_area", {}).get("buildable_acres")
                }
            }

            if existing:
                existing.price = price
                existing.status = status
                existing.list_agent = agent
                existing.owner_name = owner
                existing.source_data = full_data
                existing.updated_at = datetime.utcnow()
                session.add(existing)
                return existing
            else:
                new_listing = PropertyListing(
                    gid=gid,
                    batch_id=batch_id,
                    price=price,
                    acreage=acreage,
                    county=county,
                    status=status,
                    list_agent=agent,
                    owner_name=owner,
                    street_address=address,
                    city=city,
                    source_data=full_data
                )
                session.add(new_listing)
                return new_listing

        except Exception as e:
            logger.error(f"Error saving listing for GID {gid}: {e}")
            raise e