"""
PostgreSQL Loader Module
========================
Loads transformed DataFrames into PostgreSQL tables.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import pandas as pd
import psycopg
from psycopg.rows import dict_row

from etl_client.config import get_settings

logger = logging.getLogger(__name__)


class PostgresLoader:
    """
    Loads Pandas DataFrames into PostgreSQL tables.
    
    Handles connection management, upserts, and error handling.
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[psycopg.AsyncConnection, None]:
        """Get an async database connection."""
        conn = await psycopg.AsyncConnection.connect(
            self.settings.database_url,
            row_factory=dict_row,
        )
        try:
            yield conn
        finally:
            await conn.close()
    
    async def load_energy_prices(self, df: pd.DataFrame) -> int:
        """
        Load energy prices DataFrame into the database.
        
        Uses ON CONFLICT to handle duplicates (upsert).
        
        Args:
            df: DataFrame with energy price data
            
        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("Empty DataFrame, nothing to load")
            return 0
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                inserted = 0
                
                for _, row in df.iterrows():
                    try:
                        await cur.execute(
                            """
                            INSERT INTO energy_prices 
                                (publication_timestamp, start_timestamp, end_timestamp,
                                 tariff_type, tariff_name, unit, value)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (start_timestamp, end_timestamp, tariff_type, tariff_name)
                            DO UPDATE SET
                                publication_timestamp = EXCLUDED.publication_timestamp,
                                value = EXCLUDED.value,
                                ingested_at = NOW()
                            """,
                            (
                                row["publication_timestamp"],
                                row["start_timestamp"],
                                row["end_timestamp"],
                                row["tariff_type"],
                                row["tariff_name"],
                                row["unit"],
                                row["value"],
                            ),
                        )
                        inserted += 1
                    except Exception as e:
                        logger.error(f"Error inserting price row: {e}")
                
                await conn.commit()
                logger.info(f"Loaded {inserted} energy price records")
                return inserted
    
    async def load_plant_status(self, df: pd.DataFrame) -> int:
        """
        Load plant status DataFrame into the database.
        
        Args:
            df: DataFrame with plant status data
            
        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("Empty DataFrame, nothing to load")
            return 0
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                inserted = 0
                
                for _, row in df.iterrows():
                    try:
                        await cur.execute(
                            """
                            INSERT INTO plant_status 
                                (plant_id, timestamp, operational_status,
                                 voltage_kv, active_power_mw, reactive_power_mvar,
                                 wind_speed_kmh)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                row.get("plant_id", "lutersarni"),
                                row["timestamp"],
                                row["operational_status"],
                                row.get("voltage_kv"),
                                row.get("active_power_mw"),
                                row.get("reactive_power_mvar"),
                                row.get("wind_speed_kmh"),
                            ),
                        )
                        inserted += 1
                    except Exception as e:
                        logger.error(f"Error inserting plant status: {e}")
                
                await conn.commit()
                logger.info(f"Loaded {inserted} plant status record(s)")
                return inserted
    
    async def load_control_signals(self, df: pd.DataFrame) -> int:
        """
        Load control signals DataFrame into the database.
        
        Uses ON CONFLICT to handle duplicates.
        
        Args:
            df: DataFrame with control signal data
            
        Returns:
            Number of rows inserted
        """
        if df.empty:
            logger.warning("Empty DataFrame, nothing to load")
            return 0
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                inserted = 0
                
                for _, row in df.iterrows():
                    try:
                        await cur.execute(
                            """
                            INSERT INTO control_signals 
                                (signal_name, description, signal_date,
                                 start_timestamp, end_timestamp)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (signal_name, signal_date, start_timestamp)
                            DO NOTHING
                            """,
                            (
                                row["signal_name"],
                                row.get("description"),
                                row["signal_date"],
                                row["start_timestamp"],
                                row["end_timestamp"],
                            ),
                        )
                        inserted += 1
                    except Exception as e:
                        logger.error(f"Error inserting control signal: {e}")
                
                await conn.commit()
                logger.info(f"Loaded {inserted} control signal record(s)")
                return inserted
    
    async def load_health_metrics(self, df: pd.DataFrame) -> int:
        """
        Load health metrics DataFrame into the database.
        
        Args:
            df: DataFrame with health metrics
            
        Returns:
            Number of rows inserted
        """
        if df.empty:
            return 0
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                inserted = 0
                
                for _, row in df.iterrows():
                    try:
                        await cur.execute(
                            """
                            INSERT INTO api_health_logs 
                                (endpoint, status_code, response_time_ms,
                                 success, error_message, checked_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                row["endpoint"],
                                row.get("status_code"),
                                row.get("response_time_ms"),
                                row["success"],
                                row.get("error_message"),
                                row.get("checked_at"),
                            ),
                        )
                        inserted += 1
                    except Exception as e:
                        logger.error(f"Error inserting health metrics: {e}")
                
                await conn.commit()
                return inserted
    
    async def test_connection(self) -> bool:
        """Test database connectivity."""
        try:
            async with self.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    result = await cur.fetchone()
                    return result is not None
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
