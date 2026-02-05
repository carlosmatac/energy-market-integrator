"""
Power Plant Router
==================
Endpoints for real-time power plant status and telemetry.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from mock_server.auth.oauth2 import get_current_client
from mock_server.data.loader import get_plant_status


router = APIRouter()


class Units(BaseModel):
    """Measurement units for plant telemetry."""
    current: str = "A"
    voltage: str = "kV"
    active_power: str = "MW"
    reactive_power: str = "Mvar"
    wind_speed: str = "km/h"


class PlantStatusResponse(BaseModel):
    """Power plant status response model."""
    timestamp: str
    plant_id: str = "lutersarni"
    operational_status: str
    voltage_kv: float
    active_power_mw: float
    reactive_power_mvar: float
    wind_speed_kmh: float
    units: Units
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "timestamp": "2025-12-03T14:40+01:00",
                "plant_id": "lutersarni",
                "operational_status": "running",
                "voltage_kv": 20.698,
                "active_power_mw": 0.08,
                "reactive_power_mvar": -0.02,
                "wind_speed_kmh": 12.96,
                "units": {
                    "current": "A",
                    "voltage": "kV",
                    "active_power": "MW",
                    "reactive_power": "Mvar",
                    "wind_speed": "km/h"
                }
            }
        }


def translate_german_to_english(data: dict) -> dict:
    """
    Translate German field names to English.
    
    The CKW API uses German field names. This function translates them
    to English for a more international API.
    """
    # Status translation
    status_map = {
        "in Betrieb": "running",
        "außer Betrieb": "stopped",
        "Wartung": "maintenance",
    }
    
    translated = {
        "timestamp": data.get("zeitstempel", ""),
        "plant_id": "lutersarni",
        "operational_status": status_map.get(
            data.get("betriebsstatus", ""),
            data.get("betriebsstatus", "unknown")
        ),
        "voltage_kv": float(data.get("spannung", 0)),
        "active_power_mw": float(data.get("wirkleistung", 0)),
        "reactive_power_mvar": float(data.get("blindleistung", 0)),
        "wind_speed_kmh": float(data.get("windgeschwindigkeit", 0)),
        "units": Units(),
    }
    
    return translated


@router.get(
    "/live",
    response_model=PlantStatusResponse,
    summary="Get Live Plant Status",
    description="""
    Returns real-time status and telemetry from the Lutersarni power plant.
    
    **Telemetry data includes:**
    - **operational_status**: Current operational state (running, stopped, maintenance)
    - **voltage_kv**: Grid voltage in kilovolts
    - **active_power_mw**: Active power generation in megawatts
    - **reactive_power_mvar**: Reactive power in megavolt-amperes reactive
    - **wind_speed_kmh**: Wind speed at the plant location
    
    This endpoint simulates SCADA-like data from a wind power plant.
    """,
)
async def get_live_status(
    current_client: Annotated[str, Depends(get_current_client)],
) -> PlantStatusResponse:
    """
    Get live power plant status.
    
    Requires Bearer token authentication.
    """
    try:
        data = get_plant_status()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Translate German fields to English
    translated = translate_german_to_english(data)
    
    return PlantStatusResponse(**translated)


@router.get(
    "/live/summary",
    summary="Get Plant Status Summary",
    description="Returns a simplified summary of plant status.",
)
async def get_status_summary(
    current_client: Annotated[str, Depends(get_current_client)],
) -> dict:
    """
    Get a simplified plant status summary.
    
    Useful for dashboard widgets that only need key metrics.
    """
    try:
        data = get_plant_status()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    translated = translate_german_to_english(data)
    
    return {
        "plant_id": translated["plant_id"],
        "status": translated["operational_status"],
        "power_mw": translated["active_power_mw"],
        "is_generating": translated["active_power_mw"] > 0,
        "timestamp": translated["timestamp"],
    }
