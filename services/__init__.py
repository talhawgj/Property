from .water import WaterAnalysisService
from .parcel import ParcelSearch
from .gis import GISAnalysisService
from .parcel_analysis import AnalysisService
from .image import ImageService
from .batch import BatchService
from .catalogue import PropertyCatalogueService
water_service = WaterAnalysisService()
parcel_service = ParcelSearch()
gis_service = GISAnalysisService()
analysis_service = AnalysisService()
image_service = ImageService()
batch_service = BatchService()
catalogue_service = PropertyCatalogueService()

__all__ = ['water_service', 'parcel_service', 'gis_service',
           'analysis_service', 'image_service', 'batch_service', 'catalogue_service']