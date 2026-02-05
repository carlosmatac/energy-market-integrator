"""
Health Checker Module
=====================
Monitors API health and logs metrics to database.
"""

import logging
from typing import Any

from etl_client.loaders import PostgresLoader
from etl_client.transformers import PandasProcessor

logger = logging.getLogger(__name__)


class HealthChecker:
    """
    Monitors and logs API health metrics.
    
    Collects health data from extractors and persists to database
    for Grafana visualization.
    """
    
    def __init__(self, loader: PostgresLoader):
        self.loader = loader
        self.processor = PandasProcessor()
        self._metrics_buffer: list[dict[str, Any]] = []
    
    def record_metric(self, metrics: dict[str, Any]):
        """
        Record a health metric.
        
        Args:
            metrics: Health metrics dict from extractor
        """
        self._metrics_buffer.append(metrics)
        
        # Log summary
        status = "✓" if metrics.get("success") else "✗"
        endpoint = metrics.get("endpoint", "unknown")
        time_ms = metrics.get("response_time_ms", "?")
        code = metrics.get("status_code", "?")
        
        logger.debug(f"{status} {endpoint}: {code} in {time_ms}ms")
    
    async def flush_metrics(self) -> int:
        """
        Flush buffered metrics to database.
        
        Returns:
            Number of metrics persisted
        """
        if not self._metrics_buffer:
            return 0
        
        total_inserted = 0
        
        for metrics in self._metrics_buffer:
            df = self.processor.transform_health_metrics(metrics)
            inserted = await self.loader.load_health_metrics(df)
            total_inserted += inserted
        
        logger.info(f"Flushed {total_inserted} health metrics to database")
        self._metrics_buffer.clear()
        
        return total_inserted
    
    def get_summary(self) -> dict[str, Any]:
        """
        Get summary of buffered metrics.
        
        Returns:
            Summary dict with counts and success rate
        """
        if not self._metrics_buffer:
            return {"total": 0, "success": 0, "failed": 0, "success_rate": 0}
        
        total = len(self._metrics_buffer)
        success = sum(1 for m in self._metrics_buffer if m.get("success"))
        failed = total - success
        
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": round(100 * success / total, 2) if total > 0 else 0,
        }
