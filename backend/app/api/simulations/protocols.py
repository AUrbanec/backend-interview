"""
Experiment protocol building logic for PyBAMM simulations.
Implements standard battery test protocols per PyBAMM Experiment API.
"""
import logging
from typing import Optional

from .schemas import ProtocolType

logger = logging.getLogger(__name__)


def build_experiment_steps(
    protocol_type: ProtocolType,
    c_rate: float,
    cycles: int,
    voltage_limits: dict,
    custom_parameters: Optional[dict] = None
) -> list:
    """
    Build PyBaMM experiment steps based on protocol type.
    
    PyBAMM Experiment API uses string-based step definitions.
    Reference: https://docs.pybamm.org/en/stable/source/api/experiment/index.html
    
    Args:
        protocol_type: Type of test protocol to build
        c_rate: C-rate for charge/discharge operations
        cycles: Number of cycles to repeat
        voltage_limits: Dict with lower_voltage_cutoff, upper_voltage_cutoff
        custom_parameters: Optional protocol-specific parameters
        
    Returns:
        List of experiment step tuples for PyBaMM Experiment
        
    Raises:
        ValueError: If voltage limits are missing or invalid
    """
    logger.debug(f"Building experiment steps: protocol={protocol_type.value}, c_rate={c_rate}, cycles={cycles}")
    logger.debug(f"Voltage limits: {voltage_limits}")
    
    # Validate voltage limits
    if "lower_voltage_cutoff" not in voltage_limits or "upper_voltage_cutoff" not in voltage_limits:
        raise ValueError(f"Missing voltage limits: {voltage_limits}")
    
    lower_v = voltage_limits["lower_voltage_cutoff"]
    upper_v = voltage_limits["upper_voltage_cutoff"]
    
    if lower_v >= upper_v:
        raise ValueError(f"Invalid voltage limits: lower ({lower_v}V) >= upper ({upper_v}V)")
    
    logger.info(f"Building {protocol_type.value} protocol: {lower_v}V - {upper_v}V, {c_rate}C, {cycles} cycles")
    
    try:
        if protocol_type == ProtocolType.CAPACITY_CHECK:
            steps = _build_capacity_check_steps(c_rate, cycles, lower_v, upper_v)
            logger.info(f"Built CAPACITY_CHECK protocol with {len(steps)} step groups")
            return steps
        
        elif protocol_type == ProtocolType.RATE_CAPABILITY:
            steps = _build_rate_capability_steps(c_rate, cycles, lower_v, upper_v, custom_parameters)
            logger.info(f"Built RATE_CAPABILITY protocol with {len(steps)} step groups")
            return steps
        
        elif protocol_type == ProtocolType.HPPC:
            steps = _build_hppc_steps(c_rate, cycles, lower_v, upper_v, custom_parameters)
            logger.info(f"Built HPPC protocol with {len(steps)} step groups")
            return steps
        
        elif protocol_type == ProtocolType.DRIVE_CYCLE:
            steps = _build_drive_cycle_steps(c_rate, cycles, lower_v, upper_v, custom_parameters)
            logger.info(f"Built DRIVE_CYCLE protocol with {len(steps)} step groups")
            return steps
        
        elif protocol_type == ProtocolType.CUSTOM:
            if custom_parameters and "protocol_steps" in custom_parameters:
                steps = custom_parameters["protocol_steps"] * cycles
                logger.info(f"Built CUSTOM protocol with {len(steps)} user-defined step groups")
                return steps
            # Fall back to standard cycle
            logger.warning("CUSTOM protocol requested but no protocol_steps provided, using STANDARD_CYCLE")
            steps = _build_standard_cycle_steps(c_rate, cycles, lower_v, upper_v)
            return steps
        
        # Default: STANDARD_CYCLE - CCCV charge + CC discharge
        steps = _build_standard_cycle_steps(c_rate, cycles, lower_v, upper_v)
        logger.info(f"Built STANDARD_CYCLE protocol with {len(steps)} step groups")
        return steps
        
    except Exception as e:
        logger.error(f"Failed to build experiment steps for {protocol_type.value}: {type(e).__name__}: {str(e)}")
        raise


def _build_standard_cycle_steps(c_rate: float, cycles: int, lower_v: float, upper_v: float) -> list:
    """Standard CCCV charge + CC discharge cycle"""
    return [
        (
            f"Discharge at {c_rate}C until {lower_v}V",
            "Rest for 10 minutes",
            f"Charge at {c_rate / 2}C until {upper_v}V",
            f"Hold at {upper_v}V until C/50",
            "Rest for 10 minutes",
        )
    ] * cycles


def _build_capacity_check_steps(c_rate: float, cycles: int, lower_v: float, upper_v: float) -> list:
    """CCCV charge + C/20 discharge for baseline capacity & OCV"""
    return [
        (
            f"Charge at {c_rate}C until {upper_v}V",
            f"Hold at {upper_v}V until C/50",
            "Rest for 30 minutes",
            f"Discharge at C/20 until {lower_v}V",
            "Rest for 30 minutes",
        )
    ] * cycles


def _build_rate_capability_steps(
    c_rate: float,
    cycles: int,
    lower_v: float,
    upper_v: float,
    custom_parameters: Optional[dict]
) -> list:
    """Repeated discharges at different C-rates with rests"""
    c_rates = [0.5, 1.0, 2.0, 3.0]
    if custom_parameters and "c_rates" in custom_parameters:
        c_rates = custom_parameters["c_rates"]
    
    steps = []
    for rate in c_rates:
        steps.append((
            f"Charge at {c_rate}C until {upper_v}V",
            f"Hold at {upper_v}V until C/50",
            "Rest for 30 minutes",
            f"Discharge at {rate}C until {lower_v}V",
            "Rest for 30 minutes",
        ))
    return steps * cycles


def _build_hppc_steps(
    c_rate: float,
    cycles: int,
    lower_v: float,
    upper_v: float,
    custom_parameters: Optional[dict]
) -> list:
    """
    Hybrid Pulse Power Characterization - pulses at different SOC points.
    Standard test per USABC/FreedomCAR protocols.
    """
    pulse_duration = 10
    rest_duration = 5
    soc_points = [0.9, 0.7, 0.5, 0.3, 0.1]
    
    if custom_parameters:
        pulse_duration = custom_parameters.get("pulse_duration_seconds", pulse_duration)
        rest_duration = custom_parameters.get("rest_duration_minutes", rest_duration)
        soc_points = custom_parameters.get("soc_points", soc_points)
    
    steps = []
    # Start with full charge
    steps.append((
        f"Charge at {c_rate}C until {upper_v}V",
        f"Hold at {upper_v}V until C/50",
        f"Rest for {rest_duration} minutes",
    ))
    
    # For each SOC point, discharge to that SOC and do pulse test
    for i, soc in enumerate(soc_points):
        # Discharge pulse (high rate)
        steps.append((
            f"Discharge at 2C for {pulse_duration} seconds",
            f"Rest for {rest_duration} minutes",
            f"Charge at 2C for {pulse_duration} seconds",
            f"Rest for {rest_duration} minutes",
        ))
        # Discharge to next SOC point if not last
        if i < len(soc_points) - 1:
            next_soc = soc_points[i + 1]
            discharge_fraction = soc - next_soc
            # Approximate time to discharge this fraction at 1C
            discharge_time_hours = discharge_fraction
            steps.append((
                f"Discharge at 1C for {int(discharge_time_hours * 3600)} seconds",
                f"Rest for {rest_duration} minutes",
            ))
    
    return steps * cycles


def _build_drive_cycle_steps(
    c_rate: float,
    cycles: int,
    lower_v: float,
    upper_v: float,
    custom_parameters: Optional[dict]
) -> list:
    """
    Time-varying current profile (simplified WLTP-like pulses).
    Use custom protocol_steps if provided for actual drive cycle data.
    """
    if custom_parameters and "protocol_steps" in custom_parameters:
        return custom_parameters["protocol_steps"] * cycles
    
    # Default drive cycle pattern (simplified)
    return [
        (
            f"Discharge at 0.5C for 60 seconds",
            f"Discharge at 2C for 10 seconds",
            f"Rest for 5 seconds",
            f"Discharge at 1C for 30 seconds",
            f"Discharge at 3C for 5 seconds",
            f"Rest for 10 seconds",
            f"Discharge at 0.2C for 120 seconds",
        )
    ] * cycles


def estimate_step_count(
    protocol: ProtocolType,
    cycles: int,
    custom_parameters: Optional[dict] = None
) -> int:
    """Estimate the number of experiment steps for progress reporting"""
    if protocol == ProtocolType.CAPACITY_CHECK:
        steps_per_cycle = 5  # charge, hold, rest, discharge, rest
    elif protocol == ProtocolType.RATE_CAPABILITY:
        c_rates = [0.5, 1.0, 2.0, 3.0]
        if custom_parameters and "c_rates" in custom_parameters:
            c_rates = custom_parameters["c_rates"]
        steps_per_cycle = len(c_rates) * 5
    elif protocol == ProtocolType.HPPC:
        soc_points = [0.9, 0.7, 0.5, 0.3, 0.1]
        if custom_parameters and "soc_points" in custom_parameters:
            soc_points = custom_parameters["soc_points"]
        steps_per_cycle = 3 + len(soc_points) * 4 + (len(soc_points) - 1) * 2
    elif protocol == ProtocolType.DRIVE_CYCLE:
        steps_per_cycle = 7  # default drive cycle pattern
    else:
        steps_per_cycle = 5  # standard cycle
    
    return steps_per_cycle * cycles
