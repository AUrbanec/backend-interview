"""
Experiment builder for PyBAMM simulations.
Converts ExperimentDefinition to PyBAMM Experiment steps.
Handles string-based, programmatic, and drive cycle steps.
"""
import logging
from typing import List, Union, Any, Optional

import numpy as np
import pybamm

from .schemas import (
    ExperimentStep,
    ExperimentCycle,
    ExperimentDefinition,
    StepType,
    ExperimentMode,
)

logger = logging.getLogger(__name__)


def build_pybamm_step(step: ExperimentStep, default_period: Optional[str] = None) -> Union[str, Any]:
    """
    Convert a single ExperimentStep to PyBAMM format.
    
    Args:
        step: ExperimentStep object to convert
        default_period: Default sampling period to use if step doesn't specify one
        
    Returns:
        Either a string instruction or a pybamm.step object
        
    Raises:
        ValueError: If step type is unknown or step is invalid
    """
    logger.debug(f"Building PyBAMM step: type={step.step_type}, value={step.value}")
    
    # Handle string-based steps - direct PyBAMM instruction
    if step.step_type == StepType.STRING:
        if not step.step_string:
            raise ValueError("STRING step type requires step_string to be set")
        logger.debug(f"Using string step: {step.step_string}")
        return step.step_string
    
    # Handle rest steps
    if step.step_type == StepType.REST:
        if not step.duration:
            raise ValueError("REST step type requires duration to be set")
        rest_string = f"Rest for {step.duration}"
        logger.debug(f"Using rest step: {rest_string}")
        return rest_string
    
    # Build kwargs for programmatic steps
    kwargs = {}
    if step.duration:
        kwargs["duration"] = step.duration
    if step.termination:
        kwargs["termination"] = step.termination
    if step.period:
        kwargs["period"] = step.period
    elif default_period:
        kwargs["period"] = default_period
    if step.temperature:
        kwargs["temperature"] = step.temperature
    if step.tags:
        kwargs["tags"] = step.tags
    
    # Handle drive cycle data (time-varying profiles)
    if step.drive_cycle_data:
        logger.debug(f"Building drive cycle step with {len(step.drive_cycle_data)} data points")
        data = np.array(step.drive_cycle_data)
        
        if data.shape[1] != 2:
            raise ValueError(f"Drive cycle data must have 2 columns (time, value), got {data.shape[1]}")
        
        if step.step_type == StepType.CURRENT:
            return pybamm.step.current(data, **kwargs)
        elif step.step_type == StepType.POWER:
            return pybamm.step.power(data, **kwargs)
        elif step.step_type == StepType.VOLTAGE:
            return pybamm.step.voltage(data, **kwargs)
        else:
            raise ValueError(f"Drive cycle not supported for step type: {step.step_type}")
    
    # Handle regular programmatic steps
    value = step.value
    if value is None and step.step_type not in [StepType.REST]:
        raise ValueError(f"Step type {step.step_type} requires a value")
    
    logger.debug(f"Building programmatic step: {step.step_type.value}({value}, {kwargs})")
    
    if step.step_type == StepType.CURRENT:
        return pybamm.step.current(value, **kwargs)
    elif step.step_type == StepType.C_RATE:
        return pybamm.step.c_rate(value, **kwargs)
    elif step.step_type == StepType.VOLTAGE:
        return pybamm.step.voltage(value, **kwargs)
    elif step.step_type == StepType.POWER:
        return pybamm.step.power(value, **kwargs)
    elif step.step_type == StepType.RESISTANCE:
        return pybamm.step.resistance(value, **kwargs)
    
    raise ValueError(f"Unknown step type: {step.step_type}")


def build_experiment_from_definition(definition: ExperimentDefinition) -> List:
    """
    Convert an ExperimentDefinition to a list of PyBAMM Experiment steps.
    
    Each cycle in the definition becomes a tuple of steps.
    Cycles with repeat > 1 are duplicated in the list.
    
    Args:
        definition: ExperimentDefinition object containing cycles
        
    Returns:
        List of step tuples suitable for pybamm.Experiment()
        
    Example:
        definition = ExperimentDefinition(
            cycles=[
                ExperimentCycle(
                    steps=[
                        ExperimentStep(step_type=StepType.STRING, step_string="Discharge at 1C until 3.0V"),
                        ExperimentStep(step_type=StepType.REST, duration="10 minutes"),
                    ],
                    repeat=3
                )
            ]
        )
        # Returns: [("Discharge at 1C until 3.0V", "Rest for 10 minutes")] * 3
    """
    logger.info(f"Building experiment from definition with {len(definition.cycles)} cycles")
    
    experiment_steps = []
    default_period = definition.default_period
    
    for cycle_idx, cycle in enumerate(definition.cycles):
        logger.debug(f"Processing cycle {cycle_idx + 1}: {len(cycle.steps)} steps, repeat={cycle.repeat}")
        
        # Convert each step in the cycle
        cycle_steps = []
        for step_idx, step in enumerate(cycle.steps):
            try:
                pybamm_step = build_pybamm_step(step, default_period)
                cycle_steps.append(pybamm_step)
            except Exception as e:
                logger.error(f"Failed to build step {step_idx + 1} in cycle {cycle_idx + 1}: {e}")
                raise ValueError(f"Invalid step {step_idx + 1} in cycle {cycle_idx + 1}: {e}")
        
        # Create tuple of steps for this cycle
        cycle_tuple = tuple(cycle_steps)
        
        # Add the cycle tuple, repeated as needed
        if cycle.repeat > 1:
            logger.debug(f"Repeating cycle {cycle_idx + 1} {cycle.repeat} times")
            experiment_steps.extend([cycle_tuple] * cycle.repeat)
        else:
            experiment_steps.append(cycle_tuple)
    
    total_step_groups = len(experiment_steps)
    logger.info(f"Built experiment with {total_step_groups} step groups")
    
    return experiment_steps


def build_experiment_from_template(template_data: dict) -> List:
    """
    Convert a template dictionary (from database) to PyBAMM Experiment steps.
    
    Args:
        template_data: Dictionary containing template data with 'cycles' key
        
    Returns:
        List of step tuples suitable for pybamm.Experiment()
    """
    logger.info("Building experiment from template data")
    
    cycles_data = template_data.get("cycles", [])
    default_period = template_data.get("default_period", "1 minute")
    default_temp = template_data.get("default_temperature_celsius", 25.0)
    
    # Convert template format to ExperimentDefinition
    cycles = []
    for cycle_data in cycles_data:
        steps = []
        for step_data in cycle_data.get("steps", []):
            # Handle both dict and ExperimentStep inputs
            if isinstance(step_data, dict):
                step = ExperimentStep(
                    step_type=StepType(step_data.get("step_type", "string")),
                    value=step_data.get("value"),
                    value_unit=step_data.get("value_unit"),
                    duration=step_data.get("duration"),
                    termination=step_data.get("termination"),
                    period=step_data.get("period"),
                    temperature=step_data.get("temperature"),
                    tags=step_data.get("tags"),
                    direction=step_data.get("direction"),
                    step_string=step_data.get("step_string"),
                    drive_cycle_data=step_data.get("drive_cycle_data"),
                    drive_cycle_type=step_data.get("drive_cycle_type"),
                )
            else:
                step = step_data
            steps.append(step)
        
        cycle = ExperimentCycle(
            steps=steps,
            repeat=cycle_data.get("repeat", 1)
        )
        cycles.append(cycle)
    
    definition = ExperimentDefinition(
        cycles=cycles,
        default_period=default_period,
        default_temperature_celsius=default_temp
    )
    
    return build_experiment_from_definition(definition)


def validate_experiment_definition(definition: ExperimentDefinition) -> tuple[bool, List[str]]:
    """
    Validate an experiment definition before building.
    
    Args:
        definition: ExperimentDefinition to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not definition.cycles:
        errors.append("Experiment must have at least one cycle")
        return False, errors
    
    for cycle_idx, cycle in enumerate(definition.cycles):
        if not cycle.steps:
            errors.append(f"Cycle {cycle_idx + 1} must have at least one step")
            continue
        
        for step_idx, step in enumerate(cycle.steps):
            step_errors = _validate_step(step)
            for error in step_errors:
                errors.append(f"Cycle {cycle_idx + 1}, Step {step_idx + 1}: {error}")
    
    return len(errors) == 0, errors


def _validate_step(step: ExperimentStep) -> List[str]:
    """Validate a single experiment step"""
    errors = []
    
    if step.step_type == StepType.STRING:
        if not step.step_string:
            errors.append("STRING step requires step_string")
    elif step.step_type == StepType.REST:
        if not step.duration:
            errors.append("REST step requires duration")
    elif step.drive_cycle_data:
        if step.step_type not in [StepType.CURRENT, StepType.POWER, StepType.VOLTAGE]:
            errors.append(f"Drive cycle not supported for {step.step_type}")
        if len(step.drive_cycle_data) < 2:
            errors.append("Drive cycle needs at least 2 data points")
    else:
        if step.value is None:
            errors.append(f"{step.step_type.value} step requires a value")
        if not step.duration and not step.termination:
            errors.append("Step needs either duration or termination condition")
    
    return errors


def get_experiment_steps(
    experiment_mode: ExperimentMode,
    protocol_type: str,
    experiment_definition: Optional[ExperimentDefinition],
    experiment_template: Optional[dict],
    c_rate: float,
    cycles: int,
    voltage_limits: dict,
    custom_parameters: Optional[dict] = None
) -> List:
    """
    Get experiment steps based on experiment mode.
    
    This is the main entry point for getting experiment steps in the simulation runner.
    
    Args:
        experiment_mode: How the experiment is defined
        protocol_type: Protocol type if mode is PROTOCOL
        experiment_definition: Custom definition if mode is CUSTOM
        experiment_template: Template data if mode is TEMPLATE
        c_rate: C-rate for protocol-based experiments
        cycles: Number of cycles for protocol-based experiments
        voltage_limits: Voltage limits for protocol-based experiments
        custom_parameters: Additional parameters
        
    Returns:
        List of experiment step tuples for PyBAMM
    """
    logger.info(f"Getting experiment steps for mode: {experiment_mode}")
    
    if experiment_mode == ExperimentMode.CUSTOM:
        if not experiment_definition:
            raise ValueError("CUSTOM mode requires experiment_definition")
        return build_experiment_from_definition(experiment_definition)
    
    elif experiment_mode == ExperimentMode.TEMPLATE:
        if not experiment_template:
            raise ValueError("TEMPLATE mode requires experiment_template")
        return build_experiment_from_template(experiment_template)
    
    else:  # PROTOCOL mode - use existing protocol builder
        from .protocols import build_experiment_steps, ProtocolType
        return build_experiment_steps(
            protocol_type=ProtocolType(protocol_type),
            c_rate=c_rate,
            cycles=cycles,
            voltage_limits=voltage_limits,
            custom_parameters=custom_parameters
        )
