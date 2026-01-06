import logging
from typing import Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, cast, Float, desc, or_
from schemas import AnalysisResult  
from .parcel import ParcelSearch
from .parcel_analysis import AnalysisService
from models import PropertyCreate, PropertyUpdate, PropertyResponse, PropertyStatsResponse, PropertySearchResponse

logger = logging.getLogger(__name__)

class PropertyCatalogueService:
    def __init__(self):
        self.parcel_search = ParcelSearch()
        self.analysis_service = AnalysisService()

    def _map_db_to_response(self, row: AnalysisResult) -> PropertyResponse:
        """Helper to map a DB row to the Pydantic response model."""
        source = row.csv_source_data or {}
        result = row.result_data or {}
        parcels = result.get("parcels", {})
        
        def get_val(key, default=None):
            return source.get(key, default)

        # Extract values with fallbacks between source and result data
        return PropertyResponse(
            property_id=str(row.parcel_gid),
            gid=row.parcel_gid,
            status=get_val("Status", "activelisting"),
            situs_addr=get_val("StreetAddress") or parcels.get("situs_addr"),
            city=get_val("City") or parcels.get("city"),
            county=get_val("County") or parcels.get("county"),
            latitude=get_val("PropertyLatitude") or parcels.get("centroid_y"),
            longitude=get_val("PropertyLongitude") or parcels.get("centroid_x"),
            acreage=get_val("Acres") or parcels.get("acreage"),
            sell_price=get_val("Price"),
            price_per_acre=get_val("PPA"),
            seller_name=get_val("AgentName"),
            seller_email=get_val("AgentEmail"),
            seller_phone=get_val("AgentPhone"),
            seller_office=get_val("AgentOffice"),
            owner_name=get_val("PartyOwner1NameFull") or parcels.get("owner_name"),
            state=get_val("State"),
            zip=get_val("Zip"),
            property_type=get_val("Type"),
            beds=get_val("Beds"),
            baths=get_val("Baths"),
            built_in=get_val("BuiltIn"),
            lot_size=get_val("LotSize"),
            days_on_market=get_val("DaysOnMarket"),
            description=get_val("Description"),
            images=get_val("images", {}),
            analysis=result,
            source_data=source,
            created_at=row.created_at,
            updated_at=row.updated_at
        )

    async def create_property(self, db: AsyncSession, data: PropertyCreate) -> str:
        """Orchestrates search -> analyze -> save."""
        # 1. Search for Parcel
        search_results = []
        if data.gid:
            search_results = await self.parcel_search.get_by_filters(db=db, limit=1)
            
        if not search_results and data.latitude:
            search_results = await self.parcel_search.get_by_coordinates(
                db=db, latitude=data.latitude, longitude=data.longitude
            )

        if not search_results:
            raise ValueError("Parcel not found for provided GID or coordinates.")
        
        official_parcel = search_results[0]
        gid = official_parcel.gid
        analyze_result_data = await self.analysis_service.get_analysis(
            gid=gid, db=db
        )
        source_data_dict = data.model_dump(exclude_none=True, by_alias=True)
        query = select(AnalysisResult).where(AnalysisResult.parcel_gid == gid)
        result = await db.execute(query)
        existing_record = result.scalar_one_or_none()
        if existing_record:
            existing_record.csv_source_data = source_data_dict
            existing_record.result_data = analyze_result_data
            existing_record.updated_at = datetime.now()
        else:
            new_record = AnalysisResult(
                parcel_gid=gid,
                csv_source_data=source_data_dict,
                result_data=analyze_result_data,
                processing_mode="single"
            )
            db.add(new_record)
        
        await db.commit()
        return str(gid)

    async def list_properties(
        self, 
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        desc_order: bool = True
    ) -> PropertySearchResponse:
        """List all properties with optional pagination and ordering."""
        query = select(AnalysisResult)
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()
        
        # Apply ordering
        if desc_order:
            query = query.order_by(desc(AnalysisResult.updated_at))
        else:
            query = query.order_by(AnalysisResult.updated_at)
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        rows = (await db.execute(query)).scalars().all()

        return PropertySearchResponse(
            properties=[self._map_db_to_response(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
            has_more=(total > offset + limit)
        )

    async def search_properties(
        self, 
        db: AsyncSession, 
        status: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_acres: Optional[float] = None,
        max_acres: Optional[float] = None,
        county: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> PropertySearchResponse:
        
        query = select(AnalysisResult)
        if status:
            query = query.where(func.lower(AnalysisResult.csv_source_data['Status'].astext) == status.lower())
        if min_price is not None:
            query = query.where(cast(AnalysisResult.csv_source_data['Price'].astext, Float) >= min_price)
        if max_price is not None:
            query = query.where(cast(AnalysisResult.csv_source_data['Price'].astext, Float) <= max_price)
        if county:
            query = query.where(or_(
                func.lower(AnalysisResult.csv_source_data['County'].astext) == county.lower(),
                func.lower(AnalysisResult.result_data['parcels']['county'].astext) == county.lower()
            ))
        if min_acres is not None:
             query = query.where(cast(AnalysisResult.result_data['parcels']['acreage'].astext, Float) >= min_acres)
        if max_acres is not None:
             query = query.where(cast(AnalysisResult.result_data['parcels']['acreage'].astext, Float) <= max_acres)
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()
        query = query.limit(limit).offset(offset).order_by(desc(AnalysisResult.updated_at))
        rows = (await db.execute(query)).scalars().all()

        return PropertySearchResponse(
            properties=[self._map_db_to_response(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
            has_more=(total > offset + limit)
        )
    async def get_property(self, db: AsyncSession, property_id: str) -> Optional[PropertyResponse]:
        try:
            gid = int(property_id)
            query = select(AnalysisResult).where(AnalysisResult.parcel_gid == gid)
            row = (await db.execute(query)).scalar_one_or_none()
            return self._map_db_to_response(row) if row else None
        except ValueError:
            return None

    async def update_property(self, db: AsyncSession, property_id: str, updates: PropertyUpdate) -> Optional[PropertyResponse]:
        try:
            gid = int(property_id)
            query = select(AnalysisResult).where(AnalysisResult.parcel_gid == gid)
            row = (await db.execute(query)).scalar_one_or_none()
            
            if not row:
                return None
            
            # Get current source data
            current_source = dict(row.csv_source_data or {})
            
            # Map frontend field names to source_data keys
            field_mapping = {
                'status': 'Status',
                'situs_addr': 'StreetAddress',
                'city': 'City',
                'state': 'State',
                'zip_code': 'Zip',
                'county': 'County',
                'latitude': 'PropertyLatitude',
                'longitude': 'PropertyLongitude',
                'acreage': 'Acres',
                'sell_price': 'Price',
                'price_per_acre': 'PPA',
                'seller_name': 'AgentName',
                'seller_email': 'AgentEmail',
                'seller_phone': 'AgentPhone',
                'seller_office': 'AgentOffice',
                'owner_name': 'PartyOwner1NameFull',
                'property_type': 'Type',
                'beds': 'Beds',
                'baths': 'Baths',
                'built_in': 'BuiltIn',
                'lot_size': 'LotSize',
                'days_on_market': 'DaysOnMarket',
                'description': 'Description',
                'images': 'images',
            }
            
            # Apply updates from PropertyUpdate model
            updates_dict = updates.model_dump(exclude_none=True)
            logger.info(f"[UPDATE] Property {property_id} received updates: {updates_dict}")
            
            for field, value in updates_dict.items():
                if field == 'source_data' and isinstance(value, dict):
                    # Merge source_data updates directly
                    current_source.update(value)
                elif field == 'analysis' and isinstance(value, dict):
                    # Update result_data for analysis changes
                    current_result = dict(row.result_data or {})
                    current_result.update(value)
                    row.result_data = current_result
                elif field in field_mapping:
                    source_key = field_mapping[field]
                    current_source[source_key] = value
                    logger.info(f"[UPDATE] Set {source_key} = {value}")
            
            row.csv_source_data = current_source
            row.updated_at = datetime.utcnow()
            
            logger.info(f"[UPDATE] Final source_data keys: {list(current_source.keys())}")
            
            await db.commit()
            await db.refresh(row)
            return self._map_db_to_response(row)
        except ValueError as e:
            logger.error(f"[UPDATE] ValueError: {e}")
            return None
        except Exception as e:
            logger.error(f"[UPDATE] Exception: {e}", exc_info=True)
            raise
    async def delete_property(self, db: AsyncSession, property_id: str) -> bool:
        try:
            gid = int(property_id)
            query = delete(AnalysisResult).where(AnalysisResult.parcel_gid == gid)
            result = await db.execute(query)
            await db.commit()
            return result.rowcount > 0
        except ValueError:
            return False
    async def get_statistics(self, db: AsyncSession) -> PropertyStatsResponse:
        total = (await db.execute(select(func.count(AnalysisResult.id)))).scalar_one()
        
        active_query = select(func.count(AnalysisResult.id)).where(
            func.lower(AnalysisResult.csv_source_data['Status'].astext).in_(['active', 'activelisting'])
        )
        active = (await db.execute(active_query)).scalar_one()
        acres_query = select(func.sum(cast(AnalysisResult.result_data['parcels']['acreage'].astext, Float)))
        total_acres = (await db.execute(acres_query)).scalar_one() or 0.0
        price_query = select(func.avg(cast(AnalysisResult.csv_source_data['Price'].astext, Float)))
        avg_price = (await db.execute(price_query)).scalar_one() or 0.0
        return PropertyStatsResponse(
            total_properties=total,
            active_properties=active,
            total_acres=float(total_acres),
            average_price=float(avg_price)
        )
        