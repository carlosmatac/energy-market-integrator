"""
Plant Extractor Module
======================
Extracts power plant status from the API.
"""

from etl_client.extractors.base import BaseExtractor


class PlantExtractor(BaseExtractor):
    """Extractor for live plant status endpoint."""
    
    @property
    def endpoint(self) -> str:
        return "/api/v1/plant/live"
    
    @property
    def name(self) -> str:
        return "Plant Status"
