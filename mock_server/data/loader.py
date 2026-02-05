"""
Data Loader Module
==================
Loads and serves example JSON data from the CKW specification.
"""

import json
from pathlib import Path
from functools import lru_cache
from typing import Any


# Base path to the data directory
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "e-ckw-public-data-1.0.23-raml" / "examples"


@lru_cache(maxsize=10)
def load_json_file(filename: str) -> dict[str, Any] | list[Any]:
    """
    Load a JSON file from the examples directory.
    Uses LRU cache to avoid repeated disk reads.
    
    Args:
        filename: Name of the JSON file to load
        
    Returns:
        Parsed JSON data as dict or list
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
    """
    file_path = DATA_DIR / filename
    
    if not file_path.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_energy_prices() -> dict[str, Any]:
    """
    Load energy prices data.
    
    Returns:
        Energy prices data with publication timestamp and prices array
    """
    return load_json_file("example_energyprices.json")


def get_plant_status() -> dict[str, Any]:
    """
    Load power plant status data.
    
    Returns:
        Plant status data with telemetry readings
    """
    return load_json_file("example_lutersarni_live.json")


def get_control_signals() -> list[dict[str, Any]]:
    """
    Load TRA control signals data.
    
    Returns:
        List of control signal objects
    """
    return load_json_file("example_trasignale.json")


def clear_cache():
    """Clear the LRU cache for data files."""
    load_json_file.cache_clear()
