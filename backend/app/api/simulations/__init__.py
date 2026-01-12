"""
Simulations module - modularized PyBAMM battery simulation API.

This module provides:
- schemas: Pydantic models and enums for API request/response
- constants: Chemistry-specific voltage limits, thermal thresholds
- protocols: Experiment protocol building logic
- pybamm_models: PyBAMM model configuration and loading
- simulation_runner: Core simulation execution
- results: Result extraction and processing
- routes: FastAPI route handlers
"""
from .routes import router
from .schemas import (
    SimulationStatus,
    BatteryChemistry,
    ProtocolType,
    ThermalMode,
    SimulationCreate,
    SimulationResponse,
    CompareSimulationsRequest,
    MultiChemistryRequest,
)

__all__ = [
    "router",
    "SimulationStatus",
    "BatteryChemistry",
    "ProtocolType",
    "ThermalMode",
    "SimulationCreate",
    "SimulationResponse",
    "CompareSimulationsRequest",
    "MultiChemistryRequest",
]
