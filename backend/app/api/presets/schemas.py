"""
Pydantic models for the presets API.
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field


class BatteryChemistry(str, Enum):
    LFP = "LFP"
    NMC = "NMC"
    NCA = "NCA"
    LCO = "LCO"
    CUSTOM = "custom"


class PresetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False
    chemistry: BatteryChemistry = BatteryChemistry.LFP
    c_rate: float = Field(default=1.0, ge=0.1, le=10.0)
    temperature_celsius: float = Field(default=25.0, ge=-20.0, le=60.0)
    cycles: int = Field(default=1, ge=1, le=100)
    custom_parameters: Optional[dict] = None


class PresetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    chemistry: Optional[BatteryChemistry] = None
    c_rate: Optional[float] = Field(default=None, ge=0.1, le=10.0)
    temperature_celsius: Optional[float] = Field(default=None, ge=-20.0, le=60.0)
    cycles: Optional[int] = Field(default=None, ge=1, le=100)
    custom_parameters: Optional[dict] = None


class PresetResponse(BaseModel):
    id: str
    user_id: Optional[str]
    name: str
    description: Optional[str]
    is_public: bool
    chemistry: BatteryChemistry
    c_rate: float
    temperature_celsius: float
    cycles: int
    custom_parameters: Optional[dict]
    created_at: datetime
    updated_at: datetime
