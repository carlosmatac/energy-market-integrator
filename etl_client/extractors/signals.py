"""
Signals Extractor Module
========================
Extracts TRA control signals from the API.
"""

from etl_client.extractors.base import BaseExtractor


class SignalsExtractor(BaseExtractor):
    """Extractor for TRA control signals endpoint."""
    
    @property
    def endpoint(self) -> str:
        return "/api/v1/control/signals/last"
    
    @property
    def name(self) -> str:
        return "Control Signals"
