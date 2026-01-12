"""
Result extraction and processing for PyBAMM simulations.
"""
import logging
from typing import Optional

import numpy as np

from .constants import VOLTAGE_SAFETY_TOLERANCE

logger = logging.getLogger(__name__)


def identify_step_boundaries(solution) -> list:
    """
    Identify step boundaries from solution based on current sign changes and rest periods.
    
    Args:
        solution: PyBAMM solution object
        
    Returns:
        List of (start_idx, end_idx) tuples for each step
    """
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


def extract_step_metrics(solution, step_indices: list) -> list:
    """
    Extract per-step metrics from a PyBaMM solution.
    
    Args:
        solution: PyBAMM solution object
        step_indices: List of (start_idx, end_idx) tuples
        
    Returns:
        List of step metric dictionaries
    """
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
            dt = np.diff(step_time)
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


def extract_simulation_results(
    solution,
    parameter_values,
    chemistry_value: str,
    protocol_type_value: str,
    voltage_limits: dict,
    thermal_thresholds: dict,
    thermal_mode_value: str,
    c_rate: float,
    temperature_celsius: float,
    cycles: int
) -> dict:
    """
    Extract comprehensive results from a PyBAMM solution.
    
    Args:
        solution: PyBAMM solution object
        parameter_values: PyBAMM ParameterValues used
        chemistry_value: Chemistry string value
        protocol_type_value: Protocol type string value
        voltage_limits: Dict with voltage cutoffs
        thermal_thresholds: Dict with thermal limits
        thermal_mode_value: Thermal mode string value
        c_rate: C-rate used
        temperature_celsius: Temperature used
        cycles: Number of cycles
        
    Returns:
        Comprehensive results dictionary
        
    Raises:
        ValueError: If solution data is missing or invalid
    """
    logger.info(f"Extracting results: chemistry={chemistry_value}, protocol={protocol_type_value}")
    logger.debug(f"Extraction params: c_rate={c_rate}, temp={temperature_celsius}C, cycles={cycles}")
    
    # Extract base time series with error handling
    try:
        time = solution["Time [s]"].entries.tolist()
        voltage = solution["Voltage [V]"].entries.tolist()
        current = solution["Current [A]"].entries.tolist()
        logger.info(f"Extracted {len(time)} data points from solution")
    except KeyError as e:
        logger.error(f"Missing required solution variable: {e}")
        raise ValueError(f"Solution missing required variable: {e}")
    except Exception as e:
        logger.error(f"Failed to extract base time series: {type(e).__name__}: {e}")
        raise
    
    if len(time) == 0:
        logger.error("Solution contains no data points")
        raise ValueError("Solution contains no data points")
    
    # Identify step boundaries and extract per-step metrics
    try:
        step_boundaries = identify_step_boundaries(solution)
        step_metrics = extract_step_metrics(solution, step_boundaries)
        logger.info(f"Identified {len(step_boundaries)} steps in simulation")
    except Exception as e:
        logger.warning(f"Failed to extract step metrics: {e}. Using fallback.")
        step_boundaries = [(0, len(time))]
        step_metrics = []
    
    # Build results with step segmentation
    results = {
        "time_seconds": time,
        "voltage_v": voltage,
        "current_a": current,
        "protocol": {
            "protocol_type": protocol_type_value,
            "voltage_limits": voltage_limits,
            "cycles": cycles,
        },
        "step_boundaries": [{"start_index": s, "end_index": e} for s, e in step_boundaries],
        "step_metrics": step_metrics,
        "summary": {
            "max_voltage": float(np.max(voltage)),
            "min_voltage": float(np.min(voltage)),
            "total_time_hours": float(time[-1] / 3600) if time else 0,
            "chemistry": chemistry_value,
            "c_rate": c_rate,
            "temperature_celsius": temperature_celsius,
            "cycles": cycles,
            "protocol_type": protocol_type_value,
            "num_steps": len(step_metrics),
        }
    }
    
    # Add capacity if available
    _add_capacity_results(solution, results)
    
    # Add State of Charge (SOC)
    _add_soc_results(solution, parameter_values, results)
    
    # Add cell temperature
    _add_temperature_results(solution, results, thermal_thresholds, thermal_mode_value)
    
    # Add heat generation (if available)
    _add_heat_generation_results(solution, results)
    
    # Add power
    _add_power_results(voltage, current, results)
    
    # Add electrode potentials
    _add_electrode_potential_results(solution, results)
    
    # Calculate total energy metrics from step data
    total_ah = sum(s.get("delivered_ah", 0) for s in step_metrics)
    total_wh = sum(s.get("delivered_wh", 0) for s in step_metrics)
    results["summary"]["total_delivered_ah"] = total_ah
    results["summary"]["total_delivered_wh"] = total_wh
    
    # Add safety flags and events
    _add_safety_events(results, thermal_thresholds, voltage_limits)
    
    return results


def _add_capacity_results(solution, results: dict):
    """Add discharge capacity to results"""
    try:
        capacity = solution["Discharge capacity [A.h]"].entries.tolist()
        results["discharge_capacity_ah"] = capacity
        results["summary"]["total_capacity_ah"] = float(np.max(capacity)) if capacity else 0
    except Exception:
        pass


def _add_soc_results(solution, parameter_values, results: dict):
    """Add State of Charge (SOC) to results"""
    try:
        soc = None
        for soc_var in ["State of Charge", "x_100", "Throughput capacity [A.h]"]:
            try:
                soc = solution[soc_var].entries.tolist()
                break
            except KeyError:
                continue
        
        if soc is None and "discharge_capacity_ah" in results:
            # Calculate SOC from discharge capacity if available
            nominal_capacity = parameter_values["Nominal cell capacity [A.h]"]
            soc = [1.0 - (c / nominal_capacity) for c in results["discharge_capacity_ah"]]
        
        if soc:
            results["soc"] = soc
            results["summary"]["initial_soc"] = float(soc[0]) if soc else None
            results["summary"]["final_soc"] = float(soc[-1]) if soc else None
    except Exception as e:
        logger.debug(f"Could not extract SOC: {e}")


def _add_temperature_results(solution, results: dict, thermal_thresholds: dict, thermal_mode_value: str):
    """Add cell temperature results and thermal analysis"""
    try:
        # Try multiple temperature variable names in order of preference
        # - "X-averaged cell temperature [K]" is used by lumped thermal models (scalar value)
        # - "Cell temperature [K]" is the broadcasted version or used by full thermal models
        temperature = None
        temp_var_names = [
            "X-averaged cell temperature [K]",  # Lumped thermal model scalar
            "Cell temperature [K]",              # Full thermal / broadcasted
            "Volume-averaged cell temperature [K]",  # Alternative naming
        ]
        
        for var_name in temp_var_names:
            try:
                temperature = solution[var_name].entries
                logger.debug(f"Successfully extracted temperature from '{var_name}'")
                break
            except KeyError:
                continue
        
        if temperature is None:
            raise KeyError("No temperature variable found in solution")
        
        temp_celsius_arr = temperature - 273.15
        results["temperature_celsius"] = temp_celsius_arr.tolist()
        results["summary"]["max_temperature_celsius"] = float(np.max(temp_celsius_arr))
        results["summary"]["min_temperature_celsius"] = float(np.min(temp_celsius_arr))
        results["summary"]["avg_temperature_celsius"] = float(np.mean(temp_celsius_arr))
        
        # Add thermal mode info to results
        results["summary"]["thermal_mode"] = thermal_mode_value
        
        # Calculate time-above-threshold metrics
        time_arr = np.array(results["time_seconds"])
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
        results["summary"]["thermal_mode"] = thermal_mode_value


def _add_heat_generation_results(solution, results: dict):
    """Add heat generation data if available"""
    try:
        heat_gen = solution["Total heating [W.m-3]"].entries.tolist()
        results["heat_generation_w_m3"] = heat_gen
        results["summary"]["max_heat_generation_w_m3"] = float(np.max(heat_gen))
        results["summary"]["avg_heat_generation_w_m3"] = float(np.mean(heat_gen))
    except Exception as e:
        logger.debug(f"Could not extract heat generation: {e}")


def _add_power_results(voltage: list, current: list, results: dict):
    """Add power (V * I) calculations"""
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


def _add_electrode_potential_results(solution, results: dict):
    """Add terminal voltage and electrode potentials if available"""
    try:
        pos_potential = solution["Positive electrode potential [V]"].entries.tolist()
        neg_potential = solution["Negative electrode potential [V]"].entries.tolist()
        results["positive_electrode_potential_v"] = pos_potential
        results["negative_electrode_potential_v"] = neg_potential
    except Exception as e:
        logger.debug(f"Could not extract electrode potentials: {e}")


def _add_safety_events(results: dict, thermal_thresholds: dict, voltage_limits: dict):
    """Add safety flags and events to results"""
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
    # Apply tolerance to avoid false positives from solver overshoot during transients
    upper_limit_with_tolerance = voltage_limits["upper_voltage_cutoff"] + VOLTAGE_SAFETY_TOLERANCE
    lower_limit_with_tolerance = voltage_limits["lower_voltage_cutoff"] - VOLTAGE_SAFETY_TOLERANCE
    
    voltage_violation = False
    if max_v is not None and max_v > upper_limit_with_tolerance:
        voltage_violation = True
        safety_events.append({
            "type": "overvoltage",
            "message": f"Overvoltage detected: {max_v:.3f}V > {voltage_limits['upper_voltage_cutoff']}V (tolerance: {VOLTAGE_SAFETY_TOLERANCE}V)",
            "severity": "critical"
        })
    if min_v is not None and min_v < lower_limit_with_tolerance:
        voltage_violation = True
        safety_events.append({
            "type": "undervoltage",
            "message": f"Undervoltage detected: {min_v:.3f}V < {voltage_limits['lower_voltage_cutoff']}V (tolerance: {VOLTAGE_SAFETY_TOLERANCE}V)",
            "severity": "critical"
        })
    
    results["summary"]["max_temp_exceeded"] = max_temp_exceeded
    results["summary"]["voltage_violation"] = voltage_violation
    results["summary"]["safety_events"] = safety_events
    results["summary"]["thermal_thresholds"] = thermal_thresholds
