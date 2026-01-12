"""
Constants for battery simulation - chemistry-specific voltage limits, thermal thresholds.
"""
from typing import Optional

from .schemas import BatteryChemistry


# Voltage tolerance for safety checks (to avoid false positives from solver overshoot)
# PyBaMM simulations can slightly exceed voltage limits during transients
VOLTAGE_SAFETY_TOLERANCE = 0.05  # 50mV tolerance


# Default thermal safety thresholds (can be overridden via custom_parameters)
DEFAULT_THERMAL_THRESHOLDS = {
    "max_temp_warning_celsius": 45.0,  # Warning threshold
    "max_temp_critical_celsius": 60.0,  # Critical/shutdown threshold
    "min_temp_warning_celsius": 0.0,  # Cold warning
    "min_temp_critical_celsius": -20.0,  # Too cold for operation
}


# Chemistry-aware voltage limits (safe defaults per chemistry)
# These can be overridden via custom_parameters
CHEMISTRY_VOLTAGE_LIMITS = {
    BatteryChemistry.LFP: {
        "lower_voltage_cutoff": 2.5,
        "upper_voltage_cutoff": 3.65,
        "nominal_voltage": 3.2,
    },
    BatteryChemistry.NMC: {
        "lower_voltage_cutoff": 2.5,
        "upper_voltage_cutoff": 4.2,
        "nominal_voltage": 3.7,
    },
    BatteryChemistry.NCA: {
        "lower_voltage_cutoff": 2.5,
        "upper_voltage_cutoff": 4.2,
        "nominal_voltage": 3.6,
    },
    BatteryChemistry.LCO: {
        "lower_voltage_cutoff": 3.0,
        "upper_voltage_cutoff": 4.2,
        "nominal_voltage": 3.7,
    },
    BatteryChemistry.CUSTOM: {
        "lower_voltage_cutoff": 2.5,
        "upper_voltage_cutoff": 4.2,
        "nominal_voltage": 3.7,
    },
}


# Default thermal parameters for lumped thermal model
# These may be missing from some PyBAMM parameter sets
LUMPED_THERMAL_DEFAULTS = {
    # Current collector geometry
    "Negative current collector thickness [m]": 12e-6,
    "Positive current collector thickness [m]": 16e-6,
    # Current collector thermal properties
    "Negative current collector density [kg.m-3]": 8960,  # Copper
    "Positive current collector density [kg.m-3]": 2700,  # Aluminum
    "Negative current collector specific heat capacity [J.kg-1.K-1]": 385,
    "Positive current collector specific heat capacity [J.kg-1.K-1]": 897,
    "Negative current collector thermal conductivity [W.m-1.K-1]": 401,
    "Positive current collector thermal conductivity [W.m-1.K-1]": 237,
    # Current collector electrical conductivity
    "Negative current collector conductivity [S.m-1]": 5.96e7,  # Copper
    "Positive current collector conductivity [S.m-1]": 3.55e7,  # Aluminum
    # Electrode thermal properties (graphite anode, typical cathode)
    "Negative electrode density [kg.m-3]": 1657,  # Graphite composite
    "Positive electrode density [kg.m-3]": 3262,  # LFP/NMC composite
    "Negative electrode specific heat capacity [J.kg-1.K-1]": 700,
    "Positive electrode specific heat capacity [J.kg-1.K-1]": 700,
    "Negative electrode thermal conductivity [W.m-1.K-1]": 1.7,
    "Positive electrode thermal conductivity [W.m-1.K-1]": 2.1,
    # Separator thermal properties
    "Separator density [kg.m-3]": 397,  # Polyethylene
    "Separator specific heat capacity [J.kg-1.K-1]": 700,
    "Separator thermal conductivity [W.m-1.K-1]": 0.16,
    # Heat transfer
    "Total heat transfer coefficient [W.m-2.K-1]": 10,
    "Cell cooling surface area [m2]": 0.00531,  # Typical 18650 cell
    "Cell volume [m3]": 1.6e-5,  # Typical 18650 cell
}


# Reserved keys in custom_parameters that are handled specially
RESERVED_PARAMETER_KEYS = {
    "protocol_type",
    "protocol_steps",
    "lower_voltage_cutoff",
    "upper_voltage_cutoff",
    "nominal_voltage",
    "c_rates",
    "pulse_duration_seconds",
    "rest_duration_minutes",
    "soc_points",
    "thermal_mode",
    "external_cooling_temperature_celsius",
    "heat_transfer_coefficient",
    "max_temp_warning_celsius",
    "max_temp_critical_celsius",
    "min_temp_warning_celsius",
    "min_temp_critical_celsius",
}


def get_voltage_limits(chemistry: BatteryChemistry, custom_parameters: Optional[dict] = None) -> dict:
    """Get voltage limits for a chemistry, with custom parameter overrides"""
    limits = CHEMISTRY_VOLTAGE_LIMITS.get(
        chemistry, CHEMISTRY_VOLTAGE_LIMITS[BatteryChemistry.CUSTOM]
    ).copy()
    
    if custom_parameters:
        if "lower_voltage_cutoff" in custom_parameters:
            limits["lower_voltage_cutoff"] = float(custom_parameters["lower_voltage_cutoff"])
        if "upper_voltage_cutoff" in custom_parameters:
            limits["upper_voltage_cutoff"] = float(custom_parameters["upper_voltage_cutoff"])
        if "nominal_voltage" in custom_parameters:
            limits["nominal_voltage"] = float(custom_parameters["nominal_voltage"])
    
    return limits


def get_thermal_thresholds(custom_parameters: Optional[dict] = None) -> dict:
    """Get thermal safety thresholds with custom parameter overrides"""
    thresholds = DEFAULT_THERMAL_THRESHOLDS.copy()
    if custom_parameters:
        for key in DEFAULT_THERMAL_THRESHOLDS.keys():
            if key in custom_parameters:
                thresholds[key] = float(custom_parameters[key])
    return thresholds
