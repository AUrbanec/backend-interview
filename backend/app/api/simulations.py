import logging
import jwt
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, List
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel, Field
import pybamm
import numpy as np

from app.supabase_client import get_supabase_client_with_token, get_supabase_admin_client, settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Thread pool for running CPU-intensive PyBaMM simulations
simulation_executor = ThreadPoolExecutor(max_workers=4)


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


def get_voltage_limits(chemistry: BatteryChemistry, custom_parameters: Optional[dict] = None) -> dict:
    """Get voltage limits for a chemistry, with custom parameter overrides"""
    limits = CHEMISTRY_VOLTAGE_LIMITS.get(chemistry, CHEMISTRY_VOLTAGE_LIMITS[BatteryChemistry.CUSTOM]).copy()
    
    if custom_parameters:
        if "lower_voltage_cutoff" in custom_parameters:
            limits["lower_voltage_cutoff"] = float(custom_parameters["lower_voltage_cutoff"])
        if "upper_voltage_cutoff" in custom_parameters:
            limits["upper_voltage_cutoff"] = float(custom_parameters["upper_voltage_cutoff"])
        if "nominal_voltage" in custom_parameters:
            limits["nominal_voltage"] = float(custom_parameters["nominal_voltage"])
    
    return limits


def build_experiment_steps(
    protocol_type: ProtocolType,
    c_rate: float,
    cycles: int,
    voltage_limits: dict,
    custom_parameters: Optional[dict] = None
) -> list:
    """Build PyBaMM experiment steps based on protocol type"""
    lower_v = voltage_limits["lower_voltage_cutoff"]
    upper_v = voltage_limits["upper_voltage_cutoff"]
    
    if protocol_type == ProtocolType.CAPACITY_CHECK:
        # CCCV charge + C/20 discharge for baseline capacity & OCV
        return [
            (
                f"Charge at {c_rate}C until {upper_v}V",
                f"Hold at {upper_v}V until C/50",
                "Rest for 30 minutes",
                f"Discharge at C/20 until {lower_v}V",
                "Rest for 30 minutes",
            )
        ] * cycles
    
    elif protocol_type == ProtocolType.RATE_CAPABILITY:
        # Repeated discharges at different C-rates with rests
        c_rates = custom_parameters.get("c_rates", [0.5, 1.0, 2.0, 3.0]) if custom_parameters else [0.5, 1.0, 2.0, 3.0]
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
    
    elif protocol_type == ProtocolType.HPPC:
        # Hybrid Pulse Power Characterization - pulses at different SOC points
        pulse_duration = custom_parameters.get("pulse_duration_seconds", 10) if custom_parameters else 10
        rest_duration = custom_parameters.get("rest_duration_minutes", 5) if custom_parameters else 5
        soc_points = custom_parameters.get("soc_points", [0.9, 0.7, 0.5, 0.3, 0.1]) if custom_parameters else [0.9, 0.7, 0.5, 0.3, 0.1]
        
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
    
    elif protocol_type == ProtocolType.DRIVE_CYCLE:
        # Time-varying current profile (simplified WLTP-like pulses)
        # Use custom protocol_steps if provided
        if custom_parameters and "protocol_steps" in custom_parameters:
            return custom_parameters["protocol_steps"] * cycles
        
        # Default drive cycle pattern
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
    
    elif protocol_type == ProtocolType.CUSTOM:
        # User-defined protocol steps
        if custom_parameters and "protocol_steps" in custom_parameters:
            return custom_parameters["protocol_steps"] * cycles
        # Fall back to standard cycle
        protocol_type = ProtocolType.STANDARD_CYCLE
    
    # Default: STANDARD_CYCLE - CCCV charge + CC discharge
    return [
        (
            f"Discharge at {c_rate}C until {lower_v}V",
            "Rest for 10 minutes",
            f"Charge at {c_rate / 2}C until {upper_v}V",
            f"Hold at {upper_v}V until C/50",
            "Rest for 10 minutes",
        )
    ] * cycles


def extract_step_metrics(solution, step_indices: list) -> list:
    """Extract per-step metrics from a PyBaMM solution"""
    time = solution["Time [s]"].entries
    voltage = solution["Voltage [V]"].entries
    current = solution["Current [A]"].entries
    
    try:
        capacity = solution["Discharge capacity [A.h]"].entries
    except KeyError:
        capacity = None
    
    step_metrics = []
    
    for i, (start_idx, end_idx) in enumerate(step_indices):
        if start_idx >= len(time) or end_idx > len(time):
            continue
            
        step_time = time[start_idx:end_idx]
        step_voltage = voltage[start_idx:end_idx]
        step_current = current[start_idx:end_idx]
        
        duration_s = float(step_time[-1] - step_time[0]) if len(step_time) > 1 else 0
        avg_current = float(np.mean(step_current)) if len(step_current) > 0 else 0
        
        # Calculate Ah delivered in this step
        if len(step_time) > 1 and len(step_current) > 1:
            dt = np.diff(step_time)
            avg_currents = (step_current[:-1] + step_current[1:]) / 2
            delivered_ah = float(np.sum(np.abs(avg_currents) * dt) / 3600)
        else:
            delivered_ah = 0
        
        # Calculate Wh delivered
        if len(step_time) > 1 and len(step_voltage) > 1:
            avg_voltages = (step_voltage[:-1] + step_voltage[1:]) / 2
            avg_currents = (step_current[:-1] + step_current[1:]) / 2
            delivered_wh = float(np.sum(np.abs(avg_currents * avg_voltages) * dt) / 3600)
        else:
            delivered_wh = 0
        
        step_metrics.append({
            "step_number": i + 1,
            "start_index": int(start_idx),
            "end_index": int(end_idx),
            "duration_seconds": duration_s,
            "average_current_a": avg_current,
            "start_voltage_v": float(step_voltage[0]) if len(step_voltage) > 0 else None,
            "end_voltage_v": float(step_voltage[-1]) if len(step_voltage) > 0 else None,
            "delivered_ah": delivered_ah,
            "delivered_wh": delivered_wh,
        })
    
    return step_metrics


def identify_step_boundaries(solution) -> list:
    """Identify step boundaries from solution based on current sign changes and rest periods"""
    time = solution["Time [s]"].entries
    current = solution["Current [A]"].entries
    
    if len(time) < 2:
        return [(0, len(time))]
    
    # Detect step changes based on significant current changes
    step_indices = []
    current_threshold = 0.01  # A - threshold for detecting rest vs active
    
    start_idx = 0
    prev_state = "rest" if abs(current[0]) < current_threshold else ("charge" if current[0] < 0 else "discharge")
    
    for i in range(1, len(current)):
        curr_val = current[i]
        if abs(curr_val) < current_threshold:
            curr_state = "rest"
        elif curr_val < 0:
            curr_state = "charge"
        else:
            curr_state = "discharge"
        
        # Check for state change or significant current magnitude change
        if curr_state != prev_state:
            step_indices.append((start_idx, i))
            start_idx = i
            prev_state = curr_state
    
    # Add final step
    if start_idx < len(current):
        step_indices.append((start_idx, len(current)))
    
    return step_indices


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


async def get_user_id(authorization: str = Header(None)) -> str:
    """Extract user ID from Authorization header"""
    logger.debug("Extracting user ID from authorization header")
    
    if not authorization:
        logger.warning("Authorization header missing")
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        token = authorization.replace("Bearer ", "").strip()
        if not token:
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
        
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


def get_pybamm_model(chemistry: BatteryChemistry, thermal_mode: ThermalMode = ThermalMode.ISOTHERMAL):
    """Get the appropriate PyBaMM model for the chemistry and thermal mode
    
    Args:
        chemistry: Battery chemistry type
        thermal_mode: Thermal model to use (isothermal or lumped)
    
    Returns:
        tuple: (model, parameter_values)
    """
    logger.info(f"Loading PyBaMM model for chemistry: {chemistry}, thermal_mode: {thermal_mode}")
    
    # Build model options based on thermal mode
    if thermal_mode == ThermalMode.LUMPED:
        options = {"thermal": "lumped"}
    else:
        options = {"thermal": "isothermal"}
    
    if chemistry == BatteryChemistry.LFP:
        model = pybamm.lithium_ion.DFN(options=options)
        parameter_values = pybamm.ParameterValues("Prada2013")
    elif chemistry == BatteryChemistry.NMC:
        model = pybamm.lithium_ion.DFN(options=options)
        parameter_values = pybamm.ParameterValues("Chen2020")
    elif chemistry == BatteryChemistry.NCA:
        model = pybamm.lithium_ion.DFN(options=options)
        parameter_values = pybamm.ParameterValues("NCA_Kim2011")
    elif chemistry == BatteryChemistry.LCO:
        model = pybamm.lithium_ion.DFN(options=options)
        parameter_values = pybamm.ParameterValues("Marquis2019")
    else:
        model = pybamm.lithium_ion.DFN(options=options)
        parameter_values = pybamm.ParameterValues("Chen2020")
    
    # For lumped thermal model, ensure required geometry/thermal parameters exist
    # The lumped model computes effective volumetric heat capacity from all components:
    # ρ_eff = Σ(ρ_k * c_p,k * L_k) for k in {cn, n, s, p, cp}
    if thermal_mode == ThermalMode.LUMPED:
        # Default thermal parameters that may be missing from some parameter sets
        thermal_defaults = {
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
        for param_name, default_value in thermal_defaults.items():
            try:
                # Check if parameter exists
                _ = parameter_values[param_name]
            except KeyError:
                # Parameter doesn't exist, add it
                parameter_values.update({param_name: default_value}, check_already_exists=False)
                logger.debug(f"Added missing thermal parameter: {param_name} = {default_value}")
    
    return model, parameter_values


def run_pybamm_simulation(
    simulation_id: str,
    chemistry: BatteryChemistry,
    protocol: ProtocolType,
    c_rate: float,
    temperature_celsius: float,
    cycles: int,
    custom_parameters: Optional[dict] = None
) -> dict:
    """Run a PyBaMM simulation synchronously (to be run in thread pool)
    
    Always uses PyBaMM Experiment for unified behavior.
    Accepts protocol type directly from database column.
    Returns step segmentation and per-step metrics.
    """
    logger.info(f"Starting PyBaMM simulation {simulation_id}")
    logger.info(f"Parameters: chemistry={chemistry}, protocol={protocol}, c_rate={c_rate}, temp={temperature_celsius}°C, cycles={cycles}")
    
    try:
        # Parse thermal mode from custom_parameters (default: isothermal for backward compatibility)
        thermal_mode = ThermalMode.ISOTHERMAL
        if custom_parameters and "thermal_mode" in custom_parameters:
            try:
                thermal_mode = ThermalMode(custom_parameters["thermal_mode"])
            except ValueError:
                logger.warning(f"Invalid thermal_mode '{custom_parameters['thermal_mode']}', using isothermal")
        
        logger.info(f"Using thermal mode: {thermal_mode.value}")
        
        # Get model and parameters with thermal mode
        model, parameter_values = get_pybamm_model(chemistry, thermal_mode)
        
        # Apply C-rate
        parameter_values.update({"Current function [A]": parameter_values["Nominal cell capacity [A.h]"] * c_rate})
        
        # Apply temperature
        parameter_values.update({"Ambient temperature [K]": temperature_celsius + 273.15})
        parameter_values.update({"Initial temperature [K]": temperature_celsius + 273.15})
        
        # Apply thermal boundary conditions if in lumped thermal mode
        if thermal_mode == ThermalMode.LUMPED and custom_parameters:
            # External cooling temperature (defaults to ambient)
            if "external_cooling_temperature_celsius" in custom_parameters:
                ext_temp_k = float(custom_parameters["external_cooling_temperature_celsius"]) + 273.15
                parameter_values.update({"Ambient temperature [K]": ext_temp_k})
                logger.info(f"Set external cooling temperature: {custom_parameters['external_cooling_temperature_celsius']}°C")
            
            # Heat transfer coefficient / cooling strength
            # Use check_already_exists=False since this parameter may not have a default value in all parameter sets
            if "heat_transfer_coefficient" in custom_parameters:
                htc = float(custom_parameters["heat_transfer_coefficient"])
                parameter_values.update(
                    {"Total heat transfer coefficient [W.m-2.K-1]": htc},
                    check_already_exists=False
                )
                logger.info(f"Set heat transfer coefficient: {htc} W/m²K")
        
        # Get thermal safety thresholds (with custom overrides)
        thermal_thresholds = DEFAULT_THERMAL_THRESHOLDS.copy()
        if custom_parameters:
            for key in DEFAULT_THERMAL_THRESHOLDS.keys():
                if key in custom_parameters:
                    thermal_thresholds[key] = float(custom_parameters[key])
        
        # Get chemistry-aware voltage limits (with custom overrides)
        voltage_limits = get_voltage_limits(chemistry, custom_parameters)
        logger.info(f"Using voltage limits: {voltage_limits}")
        
        # Use protocol directly (passed from database column)
        protocol_type = protocol
        logger.info(f"Using protocol type: {protocol_type.value}")
        
        # Apply other custom parameters (excluding protocol/voltage/thermal config keys)
        reserved_keys = {"protocol_type", "protocol_steps", "lower_voltage_cutoff", 
                        "upper_voltage_cutoff", "nominal_voltage", "c_rates",
                        "pulse_duration_seconds", "rest_duration_minutes", "soc_points",
                        "thermal_mode", "external_cooling_temperature_celsius", 
                        "heat_transfer_coefficient", "max_temp_warning_celsius",
                        "max_temp_critical_celsius", "min_temp_warning_celsius", 
                        "min_temp_critical_celsius"}
        if custom_parameters:
            for key, value in custom_parameters.items():
                if key not in reserved_keys:
                    try:
                        parameter_values.update({key: value})
                    except Exception as e:
                        logger.warning(f"Failed to apply custom parameter {key}: {e}")
        
        # Build experiment steps based on protocol type (always use Experiment)
        experiment_steps = build_experiment_steps(
            protocol_type=protocol_type,
            c_rate=c_rate,
            cycles=cycles,
            voltage_limits=voltage_limits,
            custom_parameters=custom_parameters
        )
        
        logger.info(f"Built {len(experiment_steps)} experiment step groups")
        
        # Create and run experiment
        experiment = pybamm.Experiment(experiment_steps)
        sim = pybamm.Simulation(model, parameter_values=parameter_values, experiment=experiment)
        solution = sim.solve()
        
        logger.info(f"Running simulation {simulation_id}...")
        
        # Extract results
        time = solution["Time [s]"].entries.tolist()
        voltage = solution["Voltage [V]"].entries.tolist()
        current = solution["Current [A]"].entries.tolist()
        
        # Identify step boundaries and extract per-step metrics
        step_boundaries = identify_step_boundaries(solution)
        step_metrics = extract_step_metrics(solution, step_boundaries)
        
        logger.info(f"Identified {len(step_boundaries)} steps in simulation")
        
        # Build results with step segmentation
        results = {
            "time_seconds": time,
            "voltage_v": voltage,
            "current_a": current,
            "protocol": {
                "protocol_type": protocol_type.value,
                "voltage_limits": voltage_limits,
                "cycles": cycles,
            },
            "step_boundaries": [{"start_index": s, "end_index": e} for s, e in step_boundaries],
            "step_metrics": step_metrics,
            "summary": {
                "max_voltage": float(np.max(voltage)),
                "min_voltage": float(np.min(voltage)),
                "total_time_hours": float(time[-1] / 3600) if time else 0,
                "chemistry": chemistry.value,
                "c_rate": c_rate,
                "temperature_celsius": temperature_celsius,
                "cycles": cycles,
                "protocol_type": protocol_type.value,
                "num_steps": len(step_metrics),
            }
        }
        
        # Add capacity if available
        try:
            capacity = solution["Discharge capacity [A.h]"].entries.tolist()
            results["discharge_capacity_ah"] = capacity
            results["summary"]["total_capacity_ah"] = float(np.max(capacity)) if capacity else 0
        except Exception:
            pass
        
        # Add State of Charge (SOC) - critical for battery engineers
        try:
            # Try different possible SOC variable names in PyBaMM
            soc = None
            for soc_var in ["State of Charge", "x_100", "Throughput capacity [A.h]"]:
                try:
                    soc = solution[soc_var].entries.tolist()
                    break
                except KeyError:
                    continue
            
            if soc is None:
                # Calculate SOC from discharge capacity if available
                if "discharge_capacity_ah" in results:
                    nominal_capacity = parameter_values["Nominal cell capacity [A.h]"]
                    soc = [1.0 - (c / nominal_capacity) for c in results["discharge_capacity_ah"]]
            
            if soc:
                results["soc"] = soc
                results["summary"]["initial_soc"] = float(soc[0]) if soc else None
                results["summary"]["final_soc"] = float(soc[-1]) if soc else None
        except Exception as e:
            logger.debug(f"Could not extract SOC: {e}")
        
        # Add cell temperature - important for thermal analysis
        try:
            temperature = solution["Cell temperature [K]"].entries
            temp_celsius_arr = temperature - 273.15
            results["temperature_celsius"] = temp_celsius_arr.tolist()
            results["summary"]["max_temperature_celsius"] = float(np.max(temp_celsius_arr))
            results["summary"]["min_temperature_celsius"] = float(np.min(temp_celsius_arr))
            results["summary"]["avg_temperature_celsius"] = float(np.mean(temp_celsius_arr))
            
            # Add thermal mode info to results
            results["summary"]["thermal_mode"] = thermal_mode.value
            
            # Calculate time-above-threshold metrics
            time_arr = np.array(time)
            above_warning = temp_celsius_arr > thermal_thresholds["max_temp_warning_celsius"]
            above_critical = temp_celsius_arr > thermal_thresholds["max_temp_critical_celsius"]
            below_cold_warning = temp_celsius_arr < thermal_thresholds["min_temp_warning_celsius"]
            below_cold_critical = temp_celsius_arr < thermal_thresholds["min_temp_critical_celsius"]
            
            # Calculate time spent above/below thresholds
            if len(time_arr) > 1:
                dt = np.diff(time_arr)
                time_above_warning = float(np.sum(dt[above_warning[:-1]])) if np.any(above_warning[:-1]) else 0.0
                time_above_critical = float(np.sum(dt[above_critical[:-1]])) if np.any(above_critical[:-1]) else 0.0
                time_below_cold_warning = float(np.sum(dt[below_cold_warning[:-1]])) if np.any(below_cold_warning[:-1]) else 0.0
                time_below_cold_critical = float(np.sum(dt[below_cold_critical[:-1]])) if np.any(below_cold_critical[:-1]) else 0.0
            else:
                time_above_warning = time_above_critical = time_below_cold_warning = time_below_cold_critical = 0.0
            
            results["summary"]["time_above_warning_seconds"] = time_above_warning
            results["summary"]["time_above_critical_seconds"] = time_above_critical
            results["summary"]["time_below_cold_warning_seconds"] = time_below_cold_warning
            results["summary"]["time_below_cold_critical_seconds"] = time_below_cold_critical
            
        except Exception as e:
            logger.debug(f"Could not extract cell temperature: {e}")
            # Still record thermal mode even if temp extraction fails
            results["summary"]["thermal_mode"] = thermal_mode.value
        
        # Try to extract heat generation (if available in lumped thermal mode)
        try:
            heat_gen = solution["Total heating [W.m-3]"].entries.tolist()
            results["heat_generation_w_m3"] = heat_gen
            results["summary"]["max_heat_generation_w_m3"] = float(np.max(heat_gen))
            results["summary"]["avg_heat_generation_w_m3"] = float(np.mean(heat_gen))
        except Exception as e:
            logger.debug(f"Could not extract heat generation: {e}")
        
        # Add power (V * I) - commonly needed metric
        try:
            voltage_arr = np.array(voltage)
            current_arr = np.array(current)
            power = (voltage_arr * current_arr).tolist()
            results["power_w"] = power
            results["summary"]["max_power_w"] = float(np.max(power))
            results["summary"]["min_power_w"] = float(np.min(power))
            results["summary"]["avg_power_w"] = float(np.mean(power))
        except Exception as e:
            logger.debug(f"Could not calculate power: {e}")
        
        # Add terminal voltage and electrode potentials if available
        try:
            pos_potential = solution["Positive electrode potential [V]"].entries.tolist()
            neg_potential = solution["Negative electrode potential [V]"].entries.tolist()
            results["positive_electrode_potential_v"] = pos_potential
            results["negative_electrode_potential_v"] = neg_potential
        except Exception as e:
            logger.debug(f"Could not extract electrode potentials: {e}")
        
        # Calculate total energy metrics from step data
        total_ah = sum(s.get("delivered_ah", 0) for s in step_metrics)
        total_wh = sum(s.get("delivered_wh", 0) for s in step_metrics)
        results["summary"]["total_delivered_ah"] = total_ah
        results["summary"]["total_delivered_wh"] = total_wh
        
        # Add safety flags and events
        safety_events = []
        max_temp = results["summary"].get("max_temperature_celsius")
        min_temp = results["summary"].get("min_temperature_celsius")
        max_v = results["summary"].get("max_voltage")
        min_v = results["summary"].get("min_voltage")
        
        # Temperature safety flags
        max_temp_exceeded = False
        if max_temp is not None:
            if max_temp > thermal_thresholds["max_temp_critical_celsius"]:
                max_temp_exceeded = True
                safety_events.append({
                    "type": "thermal_critical",
                    "message": f"Critical temperature exceeded: {max_temp:.1f}°C > {thermal_thresholds['max_temp_critical_celsius']}°C",
                    "severity": "critical"
                })
            elif max_temp > thermal_thresholds["max_temp_warning_celsius"]:
                safety_events.append({
                    "type": "thermal_warning",
                    "message": f"Warning temperature exceeded: {max_temp:.1f}°C > {thermal_thresholds['max_temp_warning_celsius']}°C",
                    "severity": "warning"
                })
        
        if min_temp is not None:
            if min_temp < thermal_thresholds["min_temp_critical_celsius"]:
                safety_events.append({
                    "type": "cold_critical",
                    "message": f"Critical low temperature: {min_temp:.1f}°C < {thermal_thresholds['min_temp_critical_celsius']}°C",
                    "severity": "critical"
                })
            elif min_temp < thermal_thresholds["min_temp_warning_celsius"]:
                safety_events.append({
                    "type": "cold_warning",
                    "message": f"Low temperature warning: {min_temp:.1f}°C < {thermal_thresholds['min_temp_warning_celsius']}°C",
                    "severity": "warning"
                })
        
        # Voltage safety flags
        voltage_violation = False
        if max_v is not None and max_v > voltage_limits["upper_voltage_cutoff"]:
            voltage_violation = True
            safety_events.append({
                "type": "overvoltage",
                "message": f"Overvoltage detected: {max_v:.3f}V > {voltage_limits['upper_voltage_cutoff']}V",
                "severity": "critical"
            })
        if min_v is not None and min_v < voltage_limits["lower_voltage_cutoff"]:
            voltage_violation = True
            safety_events.append({
                "type": "undervoltage",
                "message": f"Undervoltage detected: {min_v:.3f}V < {voltage_limits['lower_voltage_cutoff']}V",
                "severity": "critical"
            })
        
        results["summary"]["max_temp_exceeded"] = max_temp_exceeded
        results["summary"]["voltage_violation"] = voltage_violation
        results["summary"]["safety_events"] = safety_events
        results["summary"]["thermal_thresholds"] = thermal_thresholds
        
        logger.info(f"Simulation {simulation_id} completed successfully")
        return results
        
    except Exception as e:
        logger.error(f"Simulation {simulation_id} failed: {type(e).__name__}: {str(e)}")
        raise


def estimate_step_count(protocol: ProtocolType, cycles: int, custom_parameters: Optional[dict] = None) -> int:
    """Estimate the number of experiment steps for progress reporting"""
    if protocol == ProtocolType.CAPACITY_CHECK:
        steps_per_cycle = 5  # charge, hold, rest, discharge, rest
    elif protocol == ProtocolType.RATE_CAPABILITY:
        c_rates = custom_parameters.get("c_rates", [0.5, 1.0, 2.0, 3.0]) if custom_parameters else [0.5, 1.0, 2.0, 3.0]
        steps_per_cycle = len(c_rates) * 5
    elif protocol == ProtocolType.HPPC:
        soc_points = custom_parameters.get("soc_points", [0.9, 0.7, 0.5, 0.3, 0.1]) if custom_parameters else [0.9, 0.7, 0.5, 0.3, 0.1]
        steps_per_cycle = 3 + len(soc_points) * 4 + (len(soc_points) - 1) * 2
    elif protocol == ProtocolType.DRIVE_CYCLE:
        steps_per_cycle = 7  # default drive cycle pattern
    else:
        steps_per_cycle = 5  # standard cycle
    
    return steps_per_cycle * cycles


async def run_simulation_task(
    simulation_id: str,
    user_id: str,
    chemistry: BatteryChemistry,
    protocol: ProtocolType,
    c_rate: float,
    temperature_celsius: float,
    cycles: int,
    custom_parameters: Optional[dict] = None
):
    """Background task to run simulation and update database
    
    Progress stages:
    - 5%: Initializing model and parameters
    - 10%: Building experiment steps
    - 15-85%: Running simulation (scaled by estimated step count)
    - 90%: Processing results
    - 95%: Calculating safety metrics
    - 100%: Complete
    """
    logger.info(f"Background task started for simulation {simulation_id}")
    
    admin_client = get_supabase_admin_client()
    
    # Estimate complexity for progress reporting
    estimated_steps = estimate_step_count(protocol, cycles, custom_parameters)
    is_thermal = custom_parameters and custom_parameters.get("thermal_mode") == "lumped"
    
    # Thermal simulations are heavier - adjust expected time
    complexity_factor = 1.5 if is_thermal else 1.0
    
    logger.info(f"Simulation {simulation_id}: estimated {estimated_steps} steps, thermal={is_thermal}")
    
    try:
        # Stage 1: Initializing (5%)
        admin_client.table("simulations").update({
            "status": SimulationStatus.RUNNING.value,
            "started_at": datetime.utcnow().isoformat(),
            "progress": 5,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", simulation_id).execute()
        
        # Stage 2: Building experiment (10%)
        await asyncio.sleep(0.1)  # Allow status update to propagate
        admin_client.table("simulations").update({
            "progress": 10,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", simulation_id).execute()
        
        # Stage 3: Running simulation (15-85%)
        admin_client.table("simulations").update({
            "progress": 15,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", simulation_id).execute()
        
        # Run simulation in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            simulation_executor,
            run_pybamm_simulation,
            simulation_id,
            chemistry,
            protocol,
            c_rate,
            temperature_celsius,
            cycles,
            custom_parameters
        )
        
        # Stage 4: Processing results (90%)
        admin_client.table("simulations").update({
            "progress": 90,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", simulation_id).execute()
        
        # Stage 5: Finalizing (95%)
        admin_client.table("simulations").update({
            "progress": 95,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", simulation_id).execute()
        
        # Stage 6: Complete (100%)
        admin_client.table("simulations").update({
            "status": SimulationStatus.COMPLETED.value,
            "progress": 100,
            "results": results,
            "completed_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", simulation_id).execute()
        
        # Update usage tracking - call RPC to increment count
        admin_client.rpc("increment_simulation_count", {"uid": user_id}).execute()
        
        logger.info(f"Simulation {simulation_id} completed and saved")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Simulation {simulation_id} failed: {error_msg}")
        
        admin_client.table("simulations").update({
            "status": SimulationStatus.FAILED.value,
            "error_message": error_msg,
            "completed_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", simulation_id).execute()


@router.post("/", response_model=SimulationResponse)
async def create_simulation(
    simulation: SimulationCreate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Create and start a new battery simulation"""
    logger.info(f"POST /simulations - user_id: {user_id}, name: {simulation.name}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        # Check usage limits
        usage_response = supabase.table("usage_tracking").select("*").eq("user_id", user_id).execute()
        if usage_response.data:
            usage = usage_response.data[0]
            if usage.get("simulations_count", 0) >= usage.get("simulations_limit", 100):
                logger.warning(f"User {user_id} has exceeded simulation limit")
                raise HTTPException(status_code=429, detail="Monthly simulation limit exceeded")
        
        # Create simulation record
        response = supabase.table("simulations").insert({
            "user_id": user_id,
            "name": simulation.name,
            "description": simulation.description,
            "chemistry": simulation.chemistry.value,
            "protocol": simulation.protocol.value,
            "c_rate": simulation.c_rate,
            "temperature_celsius": simulation.temperature_celsius,
            "cycles": simulation.cycles,
            "custom_parameters": simulation.custom_parameters or {},
            "status": SimulationStatus.PENDING.value,
            "progress": 0
        }).execute()
        
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create simulation")
        
        sim_data = response.data[0]
        simulation_id = sim_data["id"]
        
        logger.info(f"Created simulation {simulation_id}, starting background task")
        
        # Start background simulation task
        background_tasks.add_task(
            run_simulation_task,
            simulation_id,
            user_id,
            simulation.chemistry,
            simulation.protocol,
            simulation.c_rate,
            simulation.temperature_celsius,
            simulation.cycles,
            simulation.custom_parameters
        )
        
        return sim_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"POST /simulations - Exception: {type(e).__name__}: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[SimulationResponse])
async def get_simulations(
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None),
    status: Optional[SimulationStatus] = None,
    limit: int = 50,
    offset: int = 0
):
    """Get all simulations for the current user"""
    logger.info(f"GET /simulations - user_id: {user_id}, status: {status}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        query = supabase.table("simulations").select("*").eq("user_id", user_id)
        
        if status:
            query = query.eq("status", status.value)
        
        response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        logger.info(f"GET /simulations - Retrieved {len(response.data)} simulations")
        return response.data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /simulations - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(
    simulation_id: str,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Get a specific simulation by ID"""
    logger.info(f"GET /simulations/{simulation_id} - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        response = supabase.table("simulations").select("*").eq("id", simulation_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /simulations/{simulation_id} - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{simulation_id}")
async def delete_simulation(
    simulation_id: str,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Delete a simulation"""
    logger.info(f"DELETE /simulations/{simulation_id} - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        response = supabase.table("simulations").delete().eq("id", simulation_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        logger.info(f"DELETE /simulations/{simulation_id} - Deleted successfully")
        return {"message": "Simulation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DELETE /simulations/{simulation_id} - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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


@router.post("/compare")
async def compare_simulations(
    request: CompareSimulationsRequest,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Compare results from multiple simulations side-by-side"""
    logger.info(f"POST /simulations/compare - user_id: {user_id}, ids: {request.simulation_ids}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        # Fetch all requested simulations
        simulations = []
        for sim_id in request.simulation_ids:
            response = supabase.table("simulations").select("*").eq("id", sim_id).eq("user_id", user_id).execute()
            if response.data:
                simulations.append(response.data[0])
        
        if len(simulations) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 valid simulations to compare")
        
        # Build comparison data
        comparison = {
            "simulations": [],
            "comparison_summary": {
                "chemistries": [],
                "c_rates": [],
                "cycles": [],
                "max_voltages": [],
                "min_voltages": [],
                "total_capacities": [],
                "total_times_hours": [],
            }
        }
        
        for sim in simulations:
            sim_data = {
                "id": sim["id"],
                "name": sim["name"],
                "chemistry": sim["chemistry"],
                "c_rate": sim["c_rate"],
                "temperature_celsius": sim["temperature_celsius"],
                "cycles": sim["cycles"],
                "status": sim["status"],
            }
            
            if sim.get("results"):
                results = sim["results"]
                summary = results.get("summary", {})
                sim_data["summary"] = summary
                sim_data["has_results"] = True
                
                # Add to comparison arrays
                comparison["comparison_summary"]["chemistries"].append(sim["chemistry"])
                comparison["comparison_summary"]["c_rates"].append(sim["c_rate"])
                comparison["comparison_summary"]["cycles"].append(sim["cycles"])
                comparison["comparison_summary"]["max_voltages"].append(summary.get("max_voltage"))
                comparison["comparison_summary"]["min_voltages"].append(summary.get("min_voltage"))
                comparison["comparison_summary"]["total_capacities"].append(summary.get("total_capacity_ah"))
                comparison["comparison_summary"]["total_times_hours"].append(summary.get("total_time_hours"))
            else:
                sim_data["has_results"] = False
            
            comparison["simulations"].append(sim_data)
        
        logger.info(f"POST /simulations/compare - Compared {len(simulations)} simulations")
        return comparison
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"POST /simulations/compare - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multi-chemistry", response_model=List[SimulationResponse])
async def create_multi_chemistry_simulations(
    request: MultiChemistryRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Create and run simulations across multiple chemistries with the same parameters"""
    logger.info(f"POST /simulations/multi-chemistry - user_id: {user_id}, chemistries: {request.chemistries}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        # Check usage limits
        usage_response = supabase.table("usage_tracking").select("*").eq("user_id", user_id).execute()
        if usage_response.data:
            usage = usage_response.data[0]
            remaining = usage.get("simulations_limit", 100) - usage.get("simulations_count", 0)
            if remaining < len(request.chemistries):
                raise HTTPException(
                    status_code=429, 
                    detail=f"Not enough simulation quota. Need {len(request.chemistries)}, have {remaining}"
                )
        
        created_simulations = []
        
        for chemistry in request.chemistries:
            sim_name = f"{request.name_prefix} - {chemistry.value}"
            
            # Create simulation record
            response = supabase.table("simulations").insert({
                "user_id": user_id,
                "name": sim_name,
                "description": request.description,
                "chemistry": chemistry.value,
                "protocol": request.protocol.value,
                "c_rate": request.c_rate,
                "temperature_celsius": request.temperature_celsius,
                "cycles": request.cycles,
                "custom_parameters": request.custom_parameters or {},
                "status": SimulationStatus.PENDING.value,
                "progress": 0
            }).execute()
            
            if response.data:
                sim_data = response.data[0]
                created_simulations.append(sim_data)
                
                # Start background simulation task
                background_tasks.add_task(
                    run_simulation_task,
                    sim_data["id"],
                    user_id,
                    chemistry,
                    request.protocol,
                    request.c_rate,
                    request.temperature_celsius,
                    request.cycles,
                    request.custom_parameters
                )
        
        logger.info(f"POST /simulations/multi-chemistry - Created {len(created_simulations)} simulations")
        return created_simulations
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"POST /simulations/multi-chemistry - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{simulation_id}/cancel")
async def cancel_simulation(
    simulation_id: str,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Cancel a running simulation"""
    logger.info(f"POST /simulations/{simulation_id}/cancel - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        # Check if simulation exists and is cancellable
        check_response = supabase.table("simulations").select("status").eq("id", simulation_id).eq("user_id", user_id).execute()
        
        if not check_response.data:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        current_status = check_response.data[0].get("status")
        if current_status not in [SimulationStatus.PENDING.value, SimulationStatus.RUNNING.value]:
            raise HTTPException(status_code=400, detail=f"Cannot cancel simulation with status: {current_status}")
        
        # Update status to cancelled
        response = supabase.table("simulations").update({
            "status": SimulationStatus.CANCELLED.value,
            "completed_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", simulation_id).eq("user_id", user_id).execute()
        
        logger.info(f"POST /simulations/{simulation_id}/cancel - Cancelled successfully")
        return {"message": "Simulation cancelled"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"POST /simulations/{simulation_id}/cancel - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
