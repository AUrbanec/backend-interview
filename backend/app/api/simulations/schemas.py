"""
Pydantic models and enums for the simulations API.
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field


class SimulationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatteryChemistry(str, Enum):
    LFP = "LFP"
    NMC = "NMC"
    NCA = "NCA"
    LCO = "LCO"
    CUSTOM = "custom"


class ProtocolType(str, Enum):
    """Standard test protocols used by cell engineers"""
    STANDARD_CYCLE = "standard_cycle"  # Default: CCCV charge + CC discharge
    CAPACITY_CHECK = "capacity_check"  # CCCV charge + C/20 discharge for baseline
    RATE_CAPABILITY = "rate_capability"  # Discharges at different C-rates with rests
    DRIVE_CYCLE = "drive_cycle"  # Time-varying current profile
    HPPC = "hppc"  # Hybrid Pulse Power Characterization
    CUSTOM = "custom"  # User-defined protocol steps


class ThermalMode(str, Enum):
    """Thermal model options for simulation"""
    ISOTHERMAL = "isothermal"  # Default: constant temperature (current behavior)
    LUMPED = "lumped"  # Lumped thermal model - single cell temperature
    # Future: DISTRIBUTED = "distributed"  # Full thermal model with spatial gradients


class SimulationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    chemistry: BatteryChemistry = BatteryChemistry.LFP
    protocol: ProtocolType = ProtocolType.STANDARD_CYCLE
    c_rate: float = Field(default=1.0, ge=0.1, le=10.0)
    temperature_celsius: float = Field(default=25.0, ge=-20.0, le=60.0)
    cycles: int = Field(default=1, ge=1, le=100)
    custom_parameters: Optional[dict] = None


class SimulationResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str]
    status: SimulationStatus
    progress: int
    chemistry: BatteryChemistry
    protocol: Optional[ProtocolType] = ProtocolType.STANDARD_CYCLE
    c_rate: float
    temperature_celsius: float
    cycles: int
    custom_parameters: Optional[dict]
    results: Optional[dict]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class CompareSimulationsRequest(BaseModel):
    """Request to compare multiple simulations"""
    simulation_ids: List[str] = Field(..., min_length=2, max_length=10)


class MultiChemistryRequest(BaseModel):
    """Request to run the same test across multiple chemistries"""
    name_prefix: str
    description: Optional[str] = None
    chemistries: List[BatteryChemistry] = Field(..., min_length=2, max_length=5)
    protocol: ProtocolType = ProtocolType.STANDARD_CYCLE
    c_rate: float = Field(default=1.0, ge=0.1, le=10.0)
    temperature_celsius: float = Field(default=25.0, ge=-20.0, le=60.0)
    cycles: int = Field(default=1, ge=1, le=100)
    custom_parameters: Optional[dict] = None
