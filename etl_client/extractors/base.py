"""
Base Extractor Module
=====================
Abstract base class for all API data extractors.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from etl_client.auth import TokenManager
from etl_client.config import get_settings

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """
    Abstract base class for API data extraction.
    
    Provides common functionality:
    - HTTP client management
    - Token-based authentication
    - Retry logic with exponential backoff
    - Health metrics logging
    """
    
    def __init__(self, token_manager: TokenManager):
        self.settings = get_settings()
        self.token_manager = token_manager
        self._client: httpx.AsyncClient | None = None
    
    @property
    @abstractmethod
    def endpoint(self) -> str:
        """API endpoint path (e.g., '/api/v1/energy/prices')."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for logging."""
        pass
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.settings.api_base_url,
                timeout=30.0,
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def extract(self) -> tuple[dict[str, Any] | list[Any], dict[str, Any]]:
        """
        Extract data from the API endpoint.
        
        Returns:
            Tuple of (data, health_metrics)
            - data: Raw JSON response from API
            - health_metrics: Dict with endpoint, status_code, response_time_ms, success, error
        """
        client = await self._get_client()
        headers = await self.token_manager.get_auth_headers()
        
        start_time = time.time()
        health_metrics = {
            "endpoint": self.endpoint,
            "status_code": None,
            "response_time_ms": None,
            "success": False,
            "error_message": None,
        }
        
        try:
            logger.debug(f"Extracting data from {self.name}...")
            
            response = await self._make_request(client, headers)
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            health_metrics["status_code"] = response.status_code
            health_metrics["response_time_ms"] = elapsed_ms
            
            response.raise_for_status()
            
            data = response.json()
            health_metrics["success"] = True
            
            logger.info(
                f"✓ {self.name}: {response.status_code} in {elapsed_ms}ms"
            )
            
            return data, health_metrics
            
        except httpx.HTTPStatusError as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            health_metrics["status_code"] = e.response.status_code
            health_metrics["response_time_ms"] = elapsed_ms
            health_metrics["error_message"] = str(e)
            
            logger.error(f"✗ {self.name}: HTTP {e.response.status_code} - {e}")
            
            # Invalidate token on 401
            if e.response.status_code == 401:
                self.token_manager.invalidate_token()
            
            raise
            
        except httpx.RequestError as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            health_metrics["response_time_ms"] = elapsed_ms
            health_metrics["error_message"] = str(e)
            
            logger.error(f"✗ {self.name}: Request error - {e}")
            raise
    
    async def _make_request(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
    ) -> httpx.Response:
        """
        Make the HTTP request. Override for custom request logic.
        
        Args:
            client: HTTP client
            headers: Authorization headers
            
        Returns:
            HTTP response
        """
        return await client.get(self.endpoint, headers=headers)
    
    async def extract_with_retry(
        self,
        max_retries: int | None = None,
        retry_delay: float | None = None,
    ) -> tuple[dict[str, Any] | list[Any] | None, dict[str, Any]]:
        """
        Extract data with retry logic.
        
        Args:
            max_retries: Maximum retry attempts (default from settings)
            retry_delay: Delay between retries in seconds (default from settings)
            
        Returns:
            Tuple of (data, health_metrics). Data is None if all retries fail.
        """
        import asyncio
        
        max_retries = max_retries or self.settings.etl_max_retries
        retry_delay = retry_delay or self.settings.etl_retry_delay_seconds
        
        last_health_metrics = None
        
        for attempt in range(max_retries + 1):
            try:
                return await self.extract()
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                last_health_metrics = {
                    "endpoint": self.endpoint,
                    "status_code": getattr(getattr(e, 'response', None), 'status_code', None),
                    "response_time_ms": None,
                    "success": False,
                    "error_message": str(e),
                }
                
                if attempt < max_retries:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {self.name} "
                        f"in {wait_time:.1f}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All retries exhausted for {self.name}")
        
        return None, last_health_metrics
