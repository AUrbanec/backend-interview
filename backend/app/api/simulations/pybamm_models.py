"""
PyBAMM model configuration and loading.

Implements model selection based on chemistry and options per PyBAMM documentation.
Reference: https://docs.pybamm.org/en/stable/source/api/models/lithium_ion/index.html
"""
import logging

import pybamm

from .schemas import BatteryChemistry, ThermalMode
from .constants import LUMPED_THERMAL_DEFAULTS

logger = logging.getLogger(__name__)


# Chemistry to PyBAMM parameter set mapping
# Reference: https://docs.pybamm.org/en/stable/source/api/parameters/parameter_sets.html
CHEMISTRY_PARAMETER_SETS = {
    BatteryChemistry.LFP: "Prada2013",
    BatteryChemistry.NMC: "Chen2020",
    BatteryChemistry.NCA: "NCA_Kim2011",
    BatteryChemistry.LCO: "Marquis2019",
    BatteryChemistry.CUSTOM: "Chen2020",  # Default fallback
}


def get_pybamm_model(
    chemistry: BatteryChemistry,
    thermal_mode: ThermalMode = ThermalMode.ISOTHERMAL
):
    """
    Get the appropriate PyBaMM model for the chemistry and thermal mode.
    
    Uses the DFN (Doyle-Fuller-Newman) model as the default full-order model.
    DFN is the most comprehensive physics-based model in PyBAMM.
    
    Args:
        chemistry: Battery chemistry type
        thermal_mode: Thermal model to use (isothermal or lumped)
    
    Returns:
        tuple: (model, parameter_values)
        
    Raises:
        ValueError: If chemistry or thermal mode is invalid
        RuntimeError: If PyBaMM model loading fails
        
    Reference:
        https://docs.pybamm.org/en/stable/source/api/models/lithium_ion/dfn.html
    """
    logger.info(f"Loading PyBaMM model: chemistry={chemistry.value}, thermal_mode={thermal_mode.value}")
    
    # Build model options based on thermal mode
    options = {"thermal": thermal_mode.value}
    logger.debug(f"Model options: {options}")
    
    # Create DFN model with options
    try:
        model = pybamm.lithium_ion.DFN(options=options)
        logger.debug(f"DFN model created successfully")
    except Exception as e:
        logger.error(f"Failed to create DFN model: {type(e).__name__}: {e}")
        raise RuntimeError(f"Failed to create PyBaMM DFN model: {e}")
    
    # Get parameter set for chemistry
    param_set_name = CHEMISTRY_PARAMETER_SETS.get(chemistry, CHEMISTRY_PARAMETER_SETS[BatteryChemistry.CUSTOM])
    logger.info(f"Loading parameter set: {param_set_name}")
    
    try:
        parameter_values = pybamm.ParameterValues(param_set_name)
        logger.debug(f"Parameter set loaded: {param_set_name}")
    except Exception as e:
        logger.error(f"Failed to load parameter set '{param_set_name}': {type(e).__name__}: {e}")
        raise RuntimeError(f"Failed to load parameter set '{param_set_name}': {e}")
    
    # For lumped thermal model, ensure required thermal parameters exist
    if thermal_mode == ThermalMode.LUMPED:
        logger.debug("Adding missing thermal parameters for lumped model")
        _add_missing_thermal_parameters(parameter_values)
    
    logger.info(f"Model loaded successfully: DFN with {param_set_name}")
    return model, parameter_values


def _add_missing_thermal_parameters(parameter_values):
    """
    Add missing thermal parameters required for lumped thermal model.
    
    The lumped model computes effective volumetric heat capacity from all components:
    ρ_eff = Σ(ρ_k * c_p,k * L_k) for k in {cn, n, s, p, cp}
    """
    for param_name, default_value in LUMPED_THERMAL_DEFAULTS.items():
        try:
            # Check if parameter exists
            _ = parameter_values[param_name]
        except KeyError:
            # Parameter doesn't exist, add it
            parameter_values.update({param_name: default_value}, check_already_exists=False)
            logger.debug(f"Added missing thermal parameter: {param_name} = {default_value}")


def apply_simulation_parameters(
    parameter_values,
    c_rate: float,
    temperature_celsius: float,
    thermal_mode: ThermalMode,
    custom_parameters: dict = None
):
    """
    Apply simulation-specific parameters to the PyBAMM parameter values.
    
    Args:
        parameter_values: PyBAMM ParameterValues object to modify
        c_rate: C-rate for the simulation
        temperature_celsius: Operating temperature in Celsius
        thermal_mode: Thermal model being used
        custom_parameters: Optional additional custom parameters
        
    Returns:
        Modified parameter_values (also modifies in place)
        
    Raises:
        ValueError: If parameters are invalid
        KeyError: If required parameter is missing
    """
    logger.info(f"Applying simulation parameters: c_rate={c_rate}, temp={temperature_celsius}C, thermal={thermal_mode.value}")
    
    # Validate inputs
    if c_rate <= 0:
        raise ValueError(f"C-rate must be positive, got {c_rate}")
    if c_rate > 10:
        logger.warning(f"High C-rate: {c_rate}C - may cause numerical instability or unrealistic results")
    if temperature_celsius < -30 or temperature_celsius > 80:
        logger.warning(f"Unusual temperature: {temperature_celsius}C - outside typical operating range (-30 to 80°C)")
    
    # Apply C-rate
    try:
        nominal_capacity = parameter_values["Nominal cell capacity [A.h]"]
        current_a = nominal_capacity * c_rate
        parameter_values.update({"Current function [A]": current_a})
        logger.debug(f"Set current: {current_a:.3f}A (nominal capacity: {nominal_capacity:.3f}Ah, C-rate: {c_rate})")
    except KeyError as e:
        logger.error(f"Missing nominal capacity parameter: {e}")
        raise
    
    # Apply temperature
    temperature_kelvin = temperature_celsius + 273.15
    parameter_values.update({
        "Ambient temperature [K]": temperature_kelvin,
        "Initial temperature [K]": temperature_kelvin,
    })
    logger.debug(f"Set temperature: {temperature_kelvin:.2f}K ({temperature_celsius}C)")
    
    # Apply thermal boundary conditions if in lumped thermal mode
    if thermal_mode == ThermalMode.LUMPED and custom_parameters:
        logger.debug("Applying thermal custom parameters")
        _apply_thermal_custom_parameters(parameter_values, custom_parameters)
    
    # Apply other custom parameters (excluding reserved keys)
    if custom_parameters:
        logger.debug(f"Applying {len(custom_parameters)} custom parameters")
        _apply_custom_parameters(parameter_values, custom_parameters)
    
    logger.info("Simulation parameters applied successfully")
    return parameter_values


def _apply_thermal_custom_parameters(parameter_values, custom_parameters: dict):
    """Apply thermal-specific custom parameters"""
    # External cooling temperature (defaults to ambient)
    if "external_cooling_temperature_celsius" in custom_parameters:
        ext_temp_k = float(custom_parameters["external_cooling_temperature_celsius"]) + 273.15
        parameter_values.update({"Ambient temperature [K]": ext_temp_k})
        logger.info(f"Set external cooling temperature: {custom_parameters['external_cooling_temperature_celsius']}°C")
    
    # Heat transfer coefficient / cooling strength
    if "heat_transfer_coefficient" in custom_parameters:
        htc = float(custom_parameters["heat_transfer_coefficient"])
        parameter_values.update(
            {"Total heat transfer coefficient [W.m-2.K-1]": htc},
            check_already_exists=False
        )
        logger.info(f"Set heat transfer coefficient: {htc} W/m²K")


def _apply_custom_parameters(parameter_values, custom_parameters: dict):
    """Apply general custom parameters, excluding reserved keys"""
    from .constants import RESERVED_PARAMETER_KEYS
    
    for key, value in custom_parameters.items():
        if key not in RESERVED_PARAMETER_KEYS:
            try:
                parameter_values.update({key: value})
            except Exception as e:
                logger.warning(f"Failed to apply custom parameter {key}: {e}")
