"""
Pandas Processor Module
=======================
Transforms raw API JSON data into structured Pandas DataFrames.
Uses json_normalize to flatten nested JSON structures.
"""

import logging
from datetime import datetime
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class PandasProcessor:
    """
    Transforms raw API JSON data into Pandas DataFrames.
    
    Each method handles a specific data type and returns a DataFrame
    ready for insertion into PostgreSQL.
    """
    
    @staticmethod
    def transform_energy_prices(data: dict[str, Any]) -> pd.DataFrame:
        """
        Transform energy prices JSON into a flat DataFrame.
        
        The input has nested structure like:
        {
            "publication_timestamp": "...",
            "prices": [
                {
                    "start_timestamp": "...",
                    "grid": [{"unit": "...", "value": ...}],
                    "electricity": [...],
                    ...
                }
            ]
        }
        
        We flatten this to one row per price slot per tariff type.
        
        Args:
            data: Raw JSON from energy prices endpoint
            
        Returns:
            DataFrame with columns: publication_timestamp, start_timestamp,
            end_timestamp, tariff_type, tariff_name, unit, value
        """
        publication_timestamp = data.get("publication_timestamp")
        prices = data.get("prices", [])
        
        if not prices:
            logger.warning("No price data to transform")
            return pd.DataFrame()
        
        rows = []
        tariff_types = ["grid", "electricity", "integrated", "grid_usage"]
        
        for price_slot in prices:
            start_ts = price_slot.get("start_timestamp")
            end_ts = price_slot.get("end_timestamp")
            
            for tariff_type in tariff_types:
                tariff_data = price_slot.get(tariff_type, [])
                
                for item in tariff_data:
                    rows.append({
                        "publication_timestamp": publication_timestamp,
                        "start_timestamp": start_ts,
                        "end_timestamp": end_ts,
                        "tariff_type": tariff_type,
                        "tariff_name": "home_dynamic",  # Default
                        "unit": item.get("unit", "CHF_kWh"),
                        "value": item.get("value"),
                    })
        
        df = pd.DataFrame(rows)
        
        # Convert timestamp columns
        for col in ["publication_timestamp", "start_timestamp", "end_timestamp"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])
        
        logger.info(f"Transformed {len(df)} energy price records")
        return df
    
    @staticmethod
    def transform_plant_status(data: dict[str, Any]) -> pd.DataFrame:
        """
        Transform plant status JSON into a DataFrame.
        
        Args:
            data: Raw JSON from plant status endpoint
            
        Returns:
            DataFrame with columns: plant_id, timestamp, operational_status,
            voltage_kv, active_power_mw, reactive_power_mvar, wind_speed_kmh
        """
        if not data:
            logger.warning("No plant data to transform")
            return pd.DataFrame()
        
        # Use json_normalize for demonstration (even though it's flat)
        df = pd.json_normalize(data)
        
        # Rename columns to match database schema
        column_mapping = {
            "timestamp": "timestamp",
            "plant_id": "plant_id",
            "operational_status": "operational_status",
            "voltage_kv": "voltage_kv",
            "active_power_mw": "active_power_mw",
            "reactive_power_mvar": "reactive_power_mvar",
            "wind_speed_kmh": "wind_speed_kmh",
        }
        
        # Only keep columns that exist
        df = df[[c for c in column_mapping.keys() if c in df.columns]]
        
        # Convert timestamp
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        logger.info(f"Transformed {len(df)} plant status record(s)")
        return df
    
    @staticmethod
    def transform_control_signals(data: list[dict[str, Any]]) -> pd.DataFrame:
        """
        Transform control signals JSON into a DataFrame.
        
        Args:
            data: Raw JSON list from control signals endpoint
            
        Returns:
            DataFrame with columns: signal_name, description, signal_date,
            start_timestamp, end_timestamp
        """
        if not data:
            logger.warning("No signal data to transform")
            return pd.DataFrame()
        
        # Use json_normalize for the list
        df = pd.json_normalize(data)
        
        # Rename columns to match database schema
        column_mapping = {
            "name": "signal_name",
            "description": "description",
            "date": "signal_date",
            "start": "start_timestamp",
            "end": "end_timestamp",
        }
        
        df = df.rename(columns=column_mapping)
        
        # Convert date and timestamp columns
        if "signal_date" in df.columns:
            df["signal_date"] = pd.to_datetime(df["signal_date"]).dt.date
        
        for col in ["start_timestamp", "end_timestamp"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])
        
        logger.info(f"Transformed {len(df)} control signal record(s)")
        return df
    
    @staticmethod
    def transform_health_metrics(metrics: dict[str, Any]) -> pd.DataFrame:
        """
        Transform health metrics into a DataFrame.
        
        Args:
            metrics: Health metrics dict from extractor
            
        Returns:
            DataFrame with columns: endpoint, status_code, response_time_ms,
            success, error_message
        """
        df = pd.DataFrame([metrics])
        
        # Add timestamp
        df["checked_at"] = datetime.now()
        
        return df
