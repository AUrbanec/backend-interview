"""
Presets module - comprehensive PyBAMM model configurations and parameter presets.

This module provides:
- schemas: Pydantic models for preset API
- pybamm_options: All available PyBAMM model options per documentation
- parameter_sets: Available parameter sets for different chemistries
- routes: FastAPI route handlers for presets
"""
from .routes import router
from .schemas import (
    BatteryChemistry,
    PresetCreate,
    PresetUpdate,
    PresetResponse,
)
from .pybamm_options import (
    PYBAMM_MODEL_OPTIONS,
    LITHIUM_ION_MODELS,
    LEAD_ACID_MODELS,
    EQUIVALENT_CIRCUIT_MODELS,
    get_model_options_schema,
)

__all__ = [
    "router",
    "BatteryChemistry",
    "PresetCreate",
    "PresetUpdate",
    "PresetResponse",
    "PYBAMM_MODEL_OPTIONS",
    "LITHIUM_ION_MODELS",
    "LEAD_ACID_MODELS",
    "EQUIVALENT_CIRCUIT_MODELS",
    "get_model_options_schema",
]
