import logging
from typing import Optional, Any
from datetime import datetime
from sqlalchemy.orm.attributes import flag_modified

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

    def _clean_price(self, value: Any) -> Optional[float]:
        """Helper to clean price strings like '$100,000' -> 100000.0"""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            # Remove currency symbols and commas
            clean_str = str(value).replace("$", "").replace(",", "").strip()
            if not clean_str:
                return None
            return float(clean_str)
        except (ValueError, TypeError):
            return None

    def _map_db_to_response(self, row: AnalysisResult) -> PropertyResponse:
        """Helper to map a DB row to the Pydantic response model with robust fallback logic."""
        source = row.csv_source_data or {}
        result = row.result_data or {}
        parcels = result.get("parcels", {})
        
        # Helper to try multiple keys (Handling Aliases)
        def get_val(keys, default=None):
            if isinstance(keys, str):
                keys = [keys]
            for k in keys:
                if source.get(k):
                    return source[k]
            return default

        # Clean Price
        raw_price = get_val(["Price", "sell_price", "ListPrice", "SellPrice"])
        price = self._clean_price(raw_price)

        # Clean Acreage
        raw_acres = get_val(["Acres", "Acreage"]) or parcels.get("acreage")
        try:
            acreage = float(raw_acres) if raw_acres else None
        except:
            acreage = None

        return PropertyResponse(
            property_id=str(row.parcel_gid),
            gid=row.parcel_gid,
            status=get_val("Status", "activelisting"),
            
            # Location
            situs_addr=get_val(["StreetAddress", "Address", "SitusAddress"]) or parcels.get("situs_addr"),
            city=get_val(["City", "SitusCity"]) or parcels.get("city"),
            county=get_val("County") or parcels.get("county"),
            state=get_val("State"),
            zip=get_val(["Zip", "ZipCode"]),
            latitude=get_val(["PropertyLatitude", "Latitude"]) or parcels.get("centroid_y"),
            longitude=get_val(["PropertyLongitude", "Longitude"]) or parcels.get("centroid_x"),
            
            # Details
            acreage=acreage,
            sell_price=price,
            price_per_acre=self._clean_price(get_val(["PPA", "PricePerAcre"])),
            
            seller_name=get_val(["AgentName", "Agent", "Seller"]),
            seller_email=get_val(["AgentEmail", "Email"]),
            seller_phone=get_val(["AgentPhone", "Phone"]),
            seller_office=get_val(["AgentOffice", "Office"]),
            owner_name=get_val(["PartyOwner1NameFull", "OwnerName"]) or parcels.get("owner_name"),
            
            property_type=get_val(["Type", "PropertyType"]),
            beds=get_val("Beds"),
            baths=get_val("Baths"),
            built_in=get_val(["BuiltIn", "YearBuilt"]),
            lot_size=get_val("LotSize"),
            days_on_market=get_val(["DaysOnMarket", "DOM"]),
            description=get_val("Description"),
            
            # Data & Meta
            images=get_val("images", {}),
            analysis=result,
            source_data=source,
            created_at=row.created_at,
            updated_at=row.updated_at
        )

    async def create_property(self, db: AsyncSession, data: PropertyCreate) -> str:
        """Orchestrates search -> analyze -> save."""
        # 1. Identify GID
        if data.gid:
            gid = data.gid
        elif data.latitude and data.longitude:
            search_results = await self.parcel_search.get_by_coordinates(
                db=db, latitude=data.latitude, longitude=data.longitude
            )
            if not search_results:
                raise ValueError("Parcel not found for provided coordinates.")
            gid = search_results[0].gid
        elif data.prop_id or data.county:
            search_results = await self.parcel_search.get_by_filters(
                db=db, prop_id=data.prop_id, county=data.county
            )
            if not search_results:
                raise ValueError("Parcel not found for provided prop_id or county.")
            gid = search_results[0].gid
        else:
            raise ValueError("Must provide either gid, coordinates, or prop_id/county.")
        
        # 2. Get Analysis (Run if missing, or use provided)
        if data.analysis:
            analyze_result_data = data.analysis
        else:
            # Force analysis if it doesn't exist, but don't overwrite if valid
            analyze_result_data = await self.analysis_service.get_analysis(gid=gid, db=db)
            
        # 3. Prepare Source Data (CSV fields)
        source_data_dict = data.model_dump(exclude_none=True, by_alias=True)
        source_data_dict.pop('analysis', None)
        source_data_dict.pop('user_name', None)
        
        # 4. Upsert into AnalysisResult
        query = select(AnalysisResult).where(AnalysisResult.parcel_gid == gid)
        result = await db.execute(query)
        existing_record = result.scalar_one_or_none()
        
        if existing_record:
            # Update existing record
            existing_source = existing_record.csv_source_data or {}
            existing_source.update(source_data_dict) # Merge new data
            
            existing_record.csv_source_data = existing_source
            if analyze_result_data:
                 existing_record.result_data = analyze_result_data
            existing_record.updated_at = datetime.utcnow()
            
            flag_modified(existing_record, "csv_source_data")
            flag_modified(existing_record, "result_data")
        else:
            # Create new record
            new_record = AnalysisResult(
                parcel_gid=gid,
                csv_source_data=source_data_dict,
                result_data=analyze_result_data or {},
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
        query = select(AnalysisResult)
        
        # Total Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()
        
        # Ordering
        if desc_order:
            query = query.order_by(desc(AnalysisResult.updated_at))
        else:
            query = query.order_by(AnalysisResult.updated_at)
        
        # Pagination
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
        
        # JSONB Filters
        if status:
            query = query.where(func.lower(AnalysisResult.csv_source_data['Status'].astext) == status.lower())
        
        # Cast JSONB text to Float for numeric comparison
        if min_price is not None:
            # We check "Price" first. You might need to check "ListPrice" if data varies heavily.
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
             
        # Execute
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
            
            # Use same field mapping as before, but ensure we map to the canonical keys
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
            
            updates_dict = updates.model_dump(exclude_none=True)
            
            # Merging Logic
            if 'source_data' in updates_dict and isinstance(updates_dict['source_data'], dict):
                current_source.update(updates_dict['source_data'])
            
            for field, value in updates_dict.items():
                if field == 'source_data': continue
                elif field == 'analysis' and isinstance(value, dict):
                    current_result = dict(row.result_data or {})
                    current_result.update(value)
                    row.result_data = current_result
                    flag_modified(row, "result_data")
                elif field in field_mapping:
                    source_key = field_mapping[field]
                    current_source[source_key] = value
            
            row.csv_source_data = current_source
            row.updated_at = datetime.utcnow()
            flag_modified(row, "csv_source_data")
            
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
        
        # Fix: Ensure strict text comparison or fallback
        active_query = select(func.count(AnalysisResult.id)).where(
            func.lower(AnalysisResult.csv_source_data['Status'].astext).in_(['active', 'activelisting'])
        )
        active = (await db.execute(active_query)).scalar_one()
        
        # Fix: Coalesce nulls to 0.0
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