"""
Energy Trading ETL Client - Main Entry Point
=============================================
Orchestrates the complete ETL pipeline:
1. Extract data from Mock API (with OAuth2)
2. Transform using Pandas
3. Load into PostgreSQL
4. Log health metrics
"""

import asyncio
import logging
import sys
from datetime import datetime

from etl_client.config import get_settings
from etl_client.auth import TokenManager
from etl_client.extractors import PricesExtractor, PlantExtractor, SignalsExtractor
from etl_client.transformers import PandasProcessor
from etl_client.loaders import PostgresLoader
from etl_client.health import HealthChecker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class ETLPipeline:
    """
    Main ETL Pipeline orchestrator.
    
    Coordinates extraction, transformation, and loading of all data sources.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.token_manager = TokenManager()
        self.processor = PandasProcessor()
        self.loader = PostgresLoader()
        self.health_checker = HealthChecker(self.loader)
        
        # Initialize extractors with shared token manager
        self.extractors = {
            "prices": PricesExtractor(self.token_manager),
            "plant": PlantExtractor(self.token_manager),
            "signals": SignalsExtractor(self.token_manager),
        }
    
    async def close(self):
        """Clean up resources."""
        await self.token_manager.close()
        for extractor in self.extractors.values():
            await extractor.close()
    
    async def run_etl_cycle(self) -> dict:
        """
        Run a complete ETL cycle for all data sources.
        
        Returns:
            Summary dict with counts and status
        """
        logger.info("=" * 60)
        logger.info(f"Starting ETL cycle at {datetime.now().isoformat()}")
        logger.info("=" * 60)
        
        results = {
            "prices": {"extracted": False, "loaded": 0},
            "plant": {"extracted": False, "loaded": 0},
            "signals": {"extracted": False, "loaded": 0},
        }
        
        # 1. Extract and load Energy Prices
        try:
            data, health = await self.extractors["prices"].extract_with_retry()
            self.health_checker.record_metric(health)
            
            if data:
                df = self.processor.transform_energy_prices(data)
                loaded = await self.loader.load_energy_prices(df)
                results["prices"] = {"extracted": True, "loaded": loaded}
        except Exception as e:
            logger.error(f"Prices ETL failed: {e}")
        
        # 2. Extract and load Plant Status
        try:
            data, health = await self.extractors["plant"].extract_with_retry()
            self.health_checker.record_metric(health)
            
            if data:
                df = self.processor.transform_plant_status(data)
                loaded = await self.loader.load_plant_status(df)
                results["plant"] = {"extracted": True, "loaded": loaded}
        except Exception as e:
            logger.error(f"Plant ETL failed: {e}")
        
        # 3. Extract and load Control Signals
        try:
            data, health = await self.extractors["signals"].extract_with_retry()
            self.health_checker.record_metric(health)
            
            if data:
                df = self.processor.transform_control_signals(data)
                loaded = await self.loader.load_control_signals(df)
                results["signals"] = {"extracted": True, "loaded": loaded}
        except Exception as e:
            logger.error(f"Signals ETL failed: {e}")
        
        # 4. Flush health metrics
        await self.health_checker.flush_metrics()
        
        # Summary
        health_summary = self.health_checker.get_summary()
        logger.info("-" * 60)
        logger.info("ETL Cycle Complete:")
        logger.info(f"  Prices:  {results['prices']['loaded']} records loaded")
        logger.info(f"  Plant:   {results['plant']['loaded']} records loaded")
        logger.info(f"  Signals: {results['signals']['loaded']} records loaded")
        logger.info("-" * 60)
        
        return results


async def run_once():
    """Run a single ETL cycle."""
    pipeline = ETLPipeline()
    
    try:
        # Test database connection first
        logger.info("Testing database connection...")
        if not await pipeline.loader.test_connection():
            logger.error("Database connection failed! Is PostgreSQL running?")
            return False
        logger.info("Database connection OK")
        
        # Run ETL
        await pipeline.run_etl_cycle()
        return True
        
    finally:
        await pipeline.close()


async def run_scheduled():
    """Run ETL on a schedule."""
    settings = get_settings()
    pipeline = ETLPipeline()
    
    try:
        # Test database connection first
        logger.info("Testing database connection...")
        if not await pipeline.loader.test_connection():
            logger.error("Database connection failed! Is PostgreSQL running?")
            return
        logger.info("Database connection OK")
        
        logger.info(
            f"Starting scheduled ETL (interval: {settings.etl_poll_interval_seconds}s)"
        )
        
        while True:
            await pipeline.run_etl_cycle()
            logger.info(
                f"Next cycle in {settings.etl_poll_interval_seconds} seconds..."
            )
            await asyncio.sleep(settings.etl_poll_interval_seconds)
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await pipeline.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Energy Trading ETL Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single ETL cycle and exit",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Override polling interval in seconds",
    )
    
    args = parser.parse_args()
    
    # Override interval if specified
    if args.interval:
        import os
        os.environ["ETL_POLL_INTERVAL_SECONDS"] = str(args.interval)
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║     ⚡ Energy Trading Connectivity Monitor - ETL Client   ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  Extracting:  Energy Prices, Plant Status, Signals        ║
    ║  Target:      PostgreSQL (localhost:5432)                 ║
    ║  API Source:  http://localhost:8000                       ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    if args.once:
        asyncio.run(run_once())
    else:
        asyncio.run(run_scheduled())


if __name__ == "__main__":
    main()
