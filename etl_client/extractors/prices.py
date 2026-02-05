"""
Prices Extractor Module
=======================
Extracts dynamic energy prices from the API.
"""

from etl_client.extractors.base import BaseExtractor


class PricesExtractor(BaseExtractor):
    """Extractor for dynamic energy prices endpoint."""
    
    @property
    def endpoint(self) -> str:
        return "/api/v1/energy/prices"
    
    @property
    def name(self) -> str:
        return "Energy Prices"
