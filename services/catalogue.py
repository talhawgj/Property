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
        
        def get_val(key, default=None):
            return source.get(key, default)

        return PropertyResponse(
            property_id=str(row.parcel_gid),
            gid=row.parcel_gid,
            status=get_val("Status", "activelisting"),
            situs_addr=get_val("StreetAddress") or result.get("parcels", {}).get("situs_addr"),
            city=get_val("City") or result.get("parcels", {}).get("city"),
            county=get_val("County") or result.get("parcels", {}).get("county"),
            latitude=get_val("PropertyLatitude") or result.get("parcels", {}).get("centroid_y"),
            longitude=get_val("PropertyLongitude") or result.get("parcels", {}).get("centroid_x"),
            acreage=get_val("Acres") or result.get("parcels", {}).get("acreage"),
            sell_price=get_val("Price"),
            price_per_acre=get_val("PPA"),
            seller_name=get_val("AgentName"),
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
            current_source = dict(row.csv_source_data or {})
            if updates.status: current_source['Status'] = updates.status
            if updates.sell_price: current_source['Price'] = updates.sell_price
            if updates.description: current_source['Description'] = updates.description
            if updates.images: current_source['images'] = updates.images
            if updates.extra_data: current_source.update(updates.extra_data)
            row.csv_source_data = current_source
            row.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(row)
            return self._map_db_to_response(row)
        except ValueError:
            return None
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
        