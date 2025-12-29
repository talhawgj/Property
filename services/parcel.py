from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from geoalchemy2.shape import from_shape
from geoalchemy2.functions import ST_Contains
from shapely.geometry import Point
import logging
from fastapi import HTTPException
from sqlalchemy.orm import aliased
from schemas import Parcel
from models import ParcelResponse
from config import config
logger = logging.getLogger(__name__)


class ParcelSearch:
    async def get_by_filters(self, db: AsyncSession, prop_id: Optional[str] = None, county: Optional[str] = None) -> List[ParcelResponse]:
        """
        Fetch parcels based on prop_id (or geo_id) and county.

        Args:
            db: Database session
            prop_id: Property ID or geo ID to search for
            county: County name to filter by

        Returns:
            List of matching parcels

        Raises:
            HTTPException: If there's an error during the search
        """
        try:
            logger.info(
                f"Starting filter search - prop_id: {prop_id}, county: {county}")

            if not prop_id and not county:
                logger.warning("No search parameters provided")
                raise HTTPException(
                    status_code=400, detail="At least one search parameter (prop_id or county) is required")

            query = select(Parcel)

            if prop_id:
                query = query.filter(
                    or_(Parcel.prop_id == prop_id, Parcel.geo_id == prop_id))
                logger.debug(f"Added prop_id filter: {prop_id}")

            if county:
                query = query.filter(func.lower(
                    Parcel.county) == func.lower(county))
                logger.debug(f"Added county filter: {county}")

            result = await db.execute(query)
            parcels = result.scalars().all()

            logger.info(
                f"Filter search completed. Found {len(parcels)} parcels")
            responses = []
            for parcel in parcels:
                parcel_dict = parcel.__dict__.copy() if hasattr(parcel, '__dict__') else dict(parcel)
                # Ensure legal_area is included as acreage
                parcel_dict['acreage'] = parcel.legal_area if hasattr(parcel, 'legal_area') else None
                parcel_dict['image_url'] = f"{config.IMG_URL}{parcel.gid}/aerial_{parcel.gid}.png"
                responses.append(ParcelResponse.model_validate(parcel_dict))
            return responses

        except Exception as e:
            logger.error(f"Error in get_by_filters: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Error searching parcels: {str(e)}")

    async def get_by_coordinates(self, db: AsyncSession, latitude: float, longitude: float) -> List[ParcelResponse]:
        """
        Fetch parcels that contain the given coordinates (latitude, longitude).

        Args:
            db: Database session
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees

        Returns:
            List of matching parcels

        Raises:
            HTTPException: If coordinates are invalid or there's an error during the search
        """
        try:
            logger.info(
                f"Starting coordinate search - lat: {latitude}, lon: {longitude}")

            # Validate coordinates
            if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                logger.warning(
                    f"Invalid coordinates provided: lat={latitude}, lon={longitude}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid coordinates. Latitude must be between -90 and 90, longitude between -180 and 180"
                )

            point = from_shape(Point(longitude, latitude), srid=4326)
            logger.debug(f"Created point geometry: {point}")

            query = select(Parcel).where(
                ST_Contains(Parcel.geom, point)).limit(100)
            result = await db.execute(query)
            parcels = result.scalars().all()

            logger.info(
                f"Coordinate search completed. Found {len(parcels)} parcels")
            responses = []
            for parcel in parcels:
                parcel_dict = parcel.__dict__.copy() if hasattr(parcel, '__dict__') else dict(parcel)
                parcel_dict['image_url'] = f"{config.IMG_URL}{parcel.gid}/aerial_{parcel.gid}.png"
                responses.append(ParcelResponse.model_validate(parcel_dict))
            return responses

        except Exception as e:
            logger.error(
                f"Error in get_by_coordinates: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Error searching parcels by coordinates: {str(e)}")

    async def get_by_owner_name(self, db: AsyncSession, owner_name: str, county: Optional[str] = None) -> List[ParcelResponse]:
        """
        Fetch parcels by legal owner name (case-insensitive, partial match) and optional county.

        Args:
            db: Database session
            owner_name: Name of the legal owner to search for
            county: Optional county name to filter by

        Returns:
            List of matching parcels

        Raises:
            HTTPException: If owner name is invalid or there's an error during the search
        """
        try:
            logger.info(
                f"Starting owner name search - owner: {owner_name}, county: {county}")

            if not owner_name or len(owner_name.strip()) < 2:
                logger.warning(f"Invalid owner name provided: {owner_name}")
                raise HTTPException(
                    status_code=400,
                    detail="Owner name must be at least 2 characters long"
                )

            query = select(Parcel).where(func.lower(
                Parcel.owner_name).like(f"%{owner_name.lower()}%"))
            logger.debug(f"Initial query with owner name filter: {owner_name}")

            if county:
                query = query.where(func.lower(
                    Parcel.county) == func.lower(county))
                logger.debug(f"Added county filter: {county}")

            query = query.limit(100)
            result = await db.execute(query)
            parcels = result.scalars().all()

            logger.info(
                f"Owner name search completed. Found {len(parcels)} parcels")
            responses = []
            for parcel in parcels:
                parcel_dict = parcel.__dict__.copy() if hasattr(parcel, '__dict__') else dict(parcel)
                # Use legal_area for acreage, matching prop_id/county search
                parcel_dict['acreage'] = parcel.legal_area if hasattr(parcel, 'legal_area') else None
                parcel_dict['image_url'] = f"{config.IMG_URL}{parcel.gid}/aerial_{parcel.gid}.png"
                responses.append(ParcelResponse.model_validate(parcel_dict))
            return responses

        except Exception as e:
            logger.error(
                f"Error in get_by_owner_name: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Error searching parcels by owner name: {str(e)}")

    async def check_adjacency(self, db: AsyncSession, gids: List[int]) -> dict:
        if not gids or len(gids) < 2:
            raise HTTPException(
                status_code=400, detail="At least two GIDs are required")

        try:
            Parcel1 = aliased(Parcel)
            Parcel2 = aliased(Parcel)

            query = select(Parcel1.gid, Parcel2.gid).where(
                Parcel1.gid < Parcel2.gid,
                Parcel1.gid.in_(gids),
                Parcel2.gid.in_(gids),
                func.ST_Touches(Parcel1.geom, Parcel2.geom)
            )

            result = await db.execute(query)
            adjacent_pairs = result.fetchall()

            return {
                "are_adjacent": len(adjacent_pairs) > 0,
                "adjacent_pairs": [(r[0], r[1]) for r in adjacent_pairs]
            }

        except Exception as e:
            logger.error(f"Error in check_adjacency: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, detail="Internal server error")
    