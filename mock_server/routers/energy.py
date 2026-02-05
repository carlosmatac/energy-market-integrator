"""
Energy Prices Router
====================
Endpoints for dynamic energy pricing data (quarter-hourly intervals).
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from mock_server.auth.oauth2 import get_current_client
from mock_server.data.loader import get_energy_prices


router = APIRouter()


class PriceValue(BaseModel):
    """Single price value with unit."""
    unit: str
    value: float


class PriceSlot(BaseModel):
    """Price data for a 15-minute time slot."""
    start_timestamp: str
    end_timestamp: str
    grid: list[PriceValue]
    electricity: list[PriceValue]
    integrated: list[PriceValue]
    grid_usage: list[PriceValue]


class EnergyPricesResponse(BaseModel):
    """Full energy prices response."""
    publication_timestamp: str
    prices: list[PriceSlot]


@router.get(
    "/prices",
    response_model=EnergyPricesResponse,
    summary="Get Dynamic Energy Prices",
    description="""
    Returns dynamic energy prices at 15-minute (quarter-hourly) intervals.
    
    The response includes four types of tariffs:
    - **grid**: Grid infrastructure costs
    - **electricity**: Energy commodity costs  
    - **integrated**: Combined grid + electricity costs
    - **grid_usage**: Grid usage charges
    
    All prices are in CHF per kWh.
    """,
)
async def get_prices(
    current_client: Annotated[str, Depends(get_current_client)],
    tariff_type: Annotated[
        str | None,
        Query(
            description="Filter by tariff type: grid, electricity, integrated, grid_usage",
            pattern="^(grid|electricity|integrated|grid_usage)$",
        )
    ] = None,
    tariff_name: Annotated[
        str,
        Query(
            description="Tariff plan name",
            pattern="^(home_dynamic|business_dynamic)$",
        )
    ] = "home_dynamic",
    start_timestamp: Annotated[
        str | None,
        Query(description="Start time in ISO 8601 format")
    ] = None,
    end_timestamp: Annotated[
        str | None,
        Query(description="End time in ISO 8601 format")
    ] = None,
) -> EnergyPricesResponse:
    """
    Get dynamic energy prices.
    
    Requires Bearer token authentication.
    """
    try:
        data = get_energy_prices()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # If tariff_type filter is specified, we could filter here
    # For the mock, we return all data as-is
    # In a real implementation, you would filter the prices array
    
    return EnergyPricesResponse(**data)


@router.get(
    "/prices/latest",
    summary="Get Latest Energy Prices",
    description="Returns only the most recent price slot.",
)
async def get_latest_prices(
    current_client: Annotated[str, Depends(get_current_client)],
) -> PriceSlot:
    """
    Get the latest energy prices (most recent time slot).
    """
    try:
        data = get_energy_prices()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    prices = data.get("prices", [])
    
    if not prices:
        raise HTTPException(status_code=404, detail="No price data available")
    
    # Return the last price slot (most recent)
    latest = prices[-1]
    
    return PriceSlot(**latest)
