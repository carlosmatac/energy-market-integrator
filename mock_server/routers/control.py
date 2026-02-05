"""
Control Signals Router
======================
Endpoints for TRA (Tonfrequenz-Rundsteuer-Anlage) demand-side control signals.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel

from mock_server.auth.oauth2 import get_current_client
from mock_server.data.loader import get_control_signals


router = APIRouter()


class ControlSignal(BaseModel):
    """TRA control signal model."""
    name: str
    description: str
    date: str
    start: str
    end: str
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "name": "000R",
                "description": "Boiler 4 h",
                "date": "2025-07-08",
                "start": "2025-07-08T03:25:00+02:00",
                "end": "2025-07-08T06:56:00+02:00"
            }
        }


def normalize_signal(signal: dict) -> dict:
    """
    Normalize signal field names to lowercase.
    
    The original API uses PascalCase, we convert to snake_case/lowercase.
    """
    return {
        "name": signal.get("Name", ""),
        "description": signal.get("Description", ""),
        "date": signal.get("Date", ""),
        "start": signal.get("Start", ""),
        "end": signal.get("End", ""),
    }


@router.get(
    "/signals/{signal_date}",
    response_model=list[ControlSignal],
    summary="Get Control Signals by Date",
    description="""
    Returns TRA (Tonfrequenz-Rundsteuer-Anlage) control signals for a specific date.
    
    **What are TRA signals?**
    
    TRA is a ripple control system used by energy utilities to remotely switch 
    electrical loads on and off. Common uses include:
    
    - Controlling water heaters (boilers) during off-peak hours
    - Managing heat pumps for demand-side flexibility
    - Switching public lighting
    
    Each signal includes:
    - **name**: Signal identifier (e.g., "000R")
    - **description**: Human-readable description (e.g., "Boiler 4 h")
    - **start/end**: Activation window timestamps
    
    **Path Parameters:**
    - Use a specific date in `YYYY-MM-DD` format
    - Use `last` or `latest` to get the most recent signals
    """,
)
async def get_signals_by_date(
    current_client: Annotated[str, Depends(get_current_client)],
    signal_date: Annotated[
        str,
        Path(
            description="Date in YYYY-MM-DD format, or 'last'/'latest' for most recent",
            examples=["2025-07-08", "last", "latest"],
        )
    ],
) -> list[ControlSignal]:
    """
    Get control signals for a specific date.
    
    Requires Bearer token authentication.
    """
    try:
        signals = get_control_signals()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    if not signals:
        return []
    
    # Handle 'last' or 'latest' keywords
    if signal_date.lower() in ("last", "latest"):
        # Return all signals from the mock data (they're all from the same date)
        normalized = [normalize_signal(s) for s in signals]
        return [ControlSignal(**s) for s in normalized]
    
    # Validate date format
    try:
        requested_date = date.fromisoformat(signal_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {signal_date}. Use YYYY-MM-DD or 'last'/'latest'."
        )
    
    # Filter signals by date
    filtered = []
    for signal in signals:
        signal_date_str = signal.get("Date", "")
        if signal_date_str:
            try:
                if date.fromisoformat(signal_date_str) == requested_date:
                    filtered.append(signal)
            except ValueError:
                continue
    
    normalized = [normalize_signal(s) for s in filtered]
    return [ControlSignal(**s) for s in normalized]


@router.get(
    "/signals",
    response_model=list[ControlSignal],
    summary="Get All Control Signals",
    description="Returns all available control signals (for demo purposes).",
)
async def get_all_signals(
    current_client: Annotated[str, Depends(get_current_client)],
) -> list[ControlSignal]:
    """
    Get all available control signals.
    
    In a real API, this would require date range parameters.
    For the mock, it returns all sample data.
    """
    try:
        signals = get_control_signals()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    normalized = [normalize_signal(s) for s in signals]
    return [ControlSignal(**s) for s in normalized]
