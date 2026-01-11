"""
Core simulation execution logic for PyBAMM battery simulations.
"""
import logging
import asyncio
import time
import traceback
import os
import psutil
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime
from typing import Optional, Dict, Any
from functools import wraps

import pybamm

from app.supabase_client import get_supabase_admin_client

from .schemas import (
    BatteryChemistry, ProtocolType, ThermalMode, SimulationStatus,
    ExperimentMode, ExperimentDefinition
)
from .constants import get_voltage_limits, get_thermal_thresholds
from .protocols import build_experiment_steps, estimate_step_count
from .experiment_builder import get_experiment_steps, build_experiment_from_definition
from .pybamm_models import get_pybamm_model, apply_simulation_parameters
from .results import extract_simulation_results

logger = logging.getLogger(__name__)

# Thread pool for running CPU-intensive PyBaMM simulations
simulation_executor = ThreadPoolExecutor(max_workers=4)

# Simulation timeout in seconds (default: 10 minutes per cycle)
DEFAULT_TIMEOUT_PER_CYCLE_SECONDS = 600
MAX_SIMULATION_TIMEOUT_SECONDS = 3600  # 1 hour max

# Memory thresholds
MEMORY_WARNING_PERCENT = 80
MEMORY_CRITICAL_PERCENT = 90


class SimulationError(Exception):
    """Custom exception for simulation errors with context"""
    def __init__(self, message: str, stage: str, context: Dict[str, Any] = None):
        self.message = message
        self.stage = stage
        self.context = context or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        return {
            "error": self.message,
            "stage": self.stage,
            "context": self.context
        }


def get_memory_usage() -> Dict[str, float]:
    """Get current memory usage statistics"""
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        system_memory = psutil.virtual_memory()
        return {
            "process_rss_mb": memory_info.rss / (1024 * 1024),
            "process_vms_mb": memory_info.vms / (1024 * 1024),
            "system_percent": system_memory.percent,
            "system_available_mb": system_memory.available / (1024 * 1024)
        }
    except Exception as e:
        logger.warning(f"Failed to get memory stats: {e}")
        return {}


def check_memory_safe() -> tuple[bool, str]:
    """Check if memory usage is within safe limits"""
    try:
        system_memory = psutil.virtual_memory()
        if system_memory.percent >= MEMORY_CRITICAL_PERCENT:
            return False, f"Critical memory usage: {system_memory.percent}%"
        if system_memory.percent >= MEMORY_WARNING_PERCENT:
            logger.warning(f"High memory usage: {system_memory.percent}%")
        return True, ""
    except Exception:
        return True, ""  # Assume safe if we can't check


def log_simulation_context(simulation_id: str, stage: str, **kwargs):
    """Log simulation context with structured data"""
    memory = get_memory_usage()
    context = {
        "simulation_id": simulation_id,
        "stage": stage,
        "timestamp": datetime.utcnow().isoformat(),
        "memory": memory,
        **kwargs
    }
    logger.info(f"[SIM:{simulation_id}] {stage} | memory_rss={memory.get('process_rss_mb', 'N/A'):.1f}MB | {kwargs}")


def run_pybamm_simulation(
    simulation_id: str,
    chemistry: BatteryChemistry,
    protocol: ProtocolType,
    c_rate: float,
    temperature_celsius: float,
    cycles: int,
    custom_parameters: Optional[dict] = None,
    experiment_mode: ExperimentMode = ExperimentMode.PROTOCOL,
    experiment_definition: Optional[ExperimentDefinition] = None,
    experiment_template: Optional[dict] = None
) -> dict:
    """
    Run a PyBaMM simulation synchronously (to be run in thread pool).
    
    Always uses PyBaMM Experiment for unified behavior.
    Supports three experiment modes: protocol, custom, and template.
    Returns step segmentation and per-step metrics.
    
    Args:
        simulation_id: Unique identifier for logging
        chemistry: Battery chemistry type
        protocol: Test protocol type
        c_rate: C-rate for the simulation
        temperature_celsius: Operating temperature
        cycles: Number of cycles
        custom_parameters: Optional additional parameters
        
    Returns:
        Comprehensive results dictionary
        
    Raises:
        SimulationError: If simulation fails with detailed context
    """
    start_time = time.time()
    current_stage = "initialization"
    
    # Build context for error reporting
    sim_context = {
        "chemistry": chemistry.value,
        "protocol": protocol.value,
        "c_rate": c_rate,
        "temperature_celsius": temperature_celsius,
        "cycles": cycles,
        "custom_parameters": custom_parameters
    }
    
    log_simulation_context(simulation_id, "STARTING", **sim_context)
    
    try:
        # Check memory before starting
        memory_safe, memory_msg = check_memory_safe()
        if not memory_safe:
            raise SimulationError(
                f"Insufficient memory to start simulation: {memory_msg}",
                stage="pre_check",
                context=sim_context
            )
        
        # Stage 1: Parse thermal mode
        current_stage = "parse_thermal_mode"
        log_simulation_context(simulation_id, current_stage)
        
        thermal_mode = ThermalMode.ISOTHERMAL
        if custom_parameters and "thermal_mode" in custom_parameters:
            try:
                thermal_mode = ThermalMode(custom_parameters["thermal_mode"])
                logger.info(f"[SIM:{simulation_id}] Using thermal mode: {thermal_mode.value}")
            except ValueError as e:
                logger.warning(f"[SIM:{simulation_id}] Invalid thermal_mode '{custom_parameters['thermal_mode']}', defaulting to isothermal. Error: {e}")
        
        # Stage 2: Load PyBaMM model
        current_stage = "load_model"
        log_simulation_context(simulation_id, current_stage, thermal_mode=thermal_mode.value)
        
        try:
            model, parameter_values = get_pybamm_model(chemistry, thermal_mode)
            logger.info(f"[SIM:{simulation_id}] Model loaded successfully")
        except Exception as e:
            raise SimulationError(
                f"Failed to load PyBaMM model for {chemistry.value}: {str(e)}",
                stage=current_stage,
                context={**sim_context, "thermal_mode": thermal_mode.value, "error_type": type(e).__name__}
            )
        
        # Stage 3: Apply simulation parameters
        current_stage = "apply_parameters"
        log_simulation_context(simulation_id, current_stage)
        
        try:
            apply_simulation_parameters(
                parameter_values,
                c_rate,
                temperature_celsius,
                thermal_mode,
                custom_parameters
            )
            logger.info(f"[SIM:{simulation_id}] Parameters applied successfully")
        except Exception as e:
            raise SimulationError(
                f"Failed to apply simulation parameters: {str(e)}",
                stage=current_stage,
                context={**sim_context, "error_type": type(e).__name__}
            )
        
        # Stage 4: Get voltage limits and thermal thresholds
        current_stage = "get_limits"
        log_simulation_context(simulation_id, current_stage)
        
        thermal_thresholds = get_thermal_thresholds(custom_parameters)
        voltage_limits = get_voltage_limits(chemistry, custom_parameters)
        logger.info(f"[SIM:{simulation_id}] Voltage limits: {voltage_limits}")
        logger.info(f"[SIM:{simulation_id}] Thermal thresholds: {thermal_thresholds}")
        
        # Stage 5: Build experiment steps based on experiment_mode
        current_stage = "build_experiment"
        log_simulation_context(simulation_id, current_stage, experiment_mode=experiment_mode.value)
        
        try:
            experiment_steps = get_experiment_steps(
                experiment_mode=experiment_mode,
                protocol_type=protocol.value,
                experiment_definition=experiment_definition,
                experiment_template=experiment_template,
                c_rate=c_rate,
                cycles=cycles,
                voltage_limits=voltage_limits,
                custom_parameters=custom_parameters
            )
            logger.info(f"[SIM:{simulation_id}] Built {len(experiment_steps)} experiment step groups (mode: {experiment_mode.value})")
            
            # Log first few steps for debugging
            for i, step_group in enumerate(experiment_steps[:3]):
                logger.debug(f"[SIM:{simulation_id}] Step group {i+1}: {step_group}")
        except Exception as e:
            raise SimulationError(
                f"Failed to build experiment steps: {str(e)}",
                stage=current_stage,
                context={**sim_context, "experiment_mode": experiment_mode.value, "error_type": type(e).__name__}
            )
        
        # Stage 6: Create PyBaMM experiment and simulation
        current_stage = "create_simulation"
        log_simulation_context(simulation_id, current_stage, num_step_groups=len(experiment_steps))
        
        try:
            experiment = pybamm.Experiment(experiment_steps)
            sim = pybamm.Simulation(model, parameter_values=parameter_values, experiment=experiment)
            logger.info(f"[SIM:{simulation_id}] PyBaMM Simulation object created")
        except Exception as e:
            raise SimulationError(
                f"Failed to create PyBaMM simulation: {str(e)}",
                stage=current_stage,
                context={**sim_context, "num_steps": len(experiment_steps), "error_type": type(e).__name__}
            )
        
        # Stage 7: Run simulation (this is the CPU-intensive part)
        current_stage = "solve_simulation"
        solve_start = time.time()
        log_simulation_context(simulation_id, current_stage, status="starting_solve")
        
        # Check memory again before the heavy computation
        memory_safe, memory_msg = check_memory_safe()
        if not memory_safe:
            raise SimulationError(
                f"Insufficient memory before solve: {memory_msg}",
                stage=current_stage,
                context=sim_context
            )
        
        try:
            solution = sim.solve()
            solve_duration = time.time() - solve_start
            logger.info(f"[SIM:{simulation_id}] Solve completed in {solve_duration:.2f}s")
        except Exception as e:
            solve_duration = time.time() - solve_start
            error_traceback = traceback.format_exc()
            logger.error(f"[SIM:{simulation_id}] Solve failed after {solve_duration:.2f}s")
            logger.error(f"[SIM:{simulation_id}] Traceback:\n{error_traceback}")
            raise SimulationError(
                f"PyBaMM solve failed after {solve_duration:.2f}s: {str(e)}",
                stage=current_stage,
                context={**sim_context, "solve_duration_s": solve_duration, "error_type": type(e).__name__, "traceback": error_traceback[:1000]}
            )
        
        # Stage 8: Extract results
        current_stage = "extract_results"
        log_simulation_context(simulation_id, current_stage)
        
        try:
            results = extract_simulation_results(
                solution=solution,
                parameter_values=parameter_values,
                chemistry_value=chemistry.value,
                protocol_type_value=protocol.value,
                voltage_limits=voltage_limits,
                thermal_thresholds=thermal_thresholds,
                thermal_mode_value=thermal_mode.value,
                c_rate=c_rate,
                temperature_celsius=temperature_celsius,
                cycles=cycles
            )
            logger.info(f"[SIM:{simulation_id}] Results extracted successfully")
        except Exception as e:
            error_traceback = traceback.format_exc()
            raise SimulationError(
                f"Failed to extract results: {str(e)}",
                stage=current_stage,
                context={**sim_context, "error_type": type(e).__name__, "traceback": error_traceback[:1000]}
            )
        
        # Final logging
        total_duration = time.time() - start_time
        log_simulation_context(
            simulation_id, 
            "COMPLETED",
            total_duration_s=f"{total_duration:.2f}",
            num_data_points=len(results.get("time_seconds", [])),
            num_steps=results.get("summary", {}).get("num_steps", 0)
        )
        
        # Add timing metadata to results
        results["_metadata"] = {
            "total_duration_seconds": total_duration,
            "solve_duration_seconds": solve_duration,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        return results
        
    except SimulationError:
        raise
    except Exception as e:
        total_duration = time.time() - start_time
        error_traceback = traceback.format_exc()
        logger.error(f"[SIM:{simulation_id}] Unexpected error in stage '{current_stage}' after {total_duration:.2f}s")
        logger.error(f"[SIM:{simulation_id}] Error: {type(e).__name__}: {str(e)}")
        logger.error(f"[SIM:{simulation_id}] Traceback:\n{error_traceback}")
        raise SimulationError(
            f"Unexpected error in {current_stage}: {str(e)}",
            stage=current_stage,
            context={**sim_context, "duration_s": total_duration, "error_type": type(e).__name__, "traceback": error_traceback[:1000]}
        )


async def run_simulation_task(
    simulation_id: str,
    user_id: str,
    chemistry: BatteryChemistry,
    protocol: ProtocolType,
    c_rate: float,
    temperature_celsius: float,
    cycles: int,
    custom_parameters: Optional[dict] = None,
    experiment_mode: ExperimentMode = ExperimentMode.PROTOCOL,
    experiment_definition: Optional[ExperimentDefinition] = None,
    experiment_template: Optional[dict] = None
):
    """
    Background task to run simulation and update database.
    
    Supports three experiment modes:
    - PROTOCOL: Use predefined protocol_type
    - CUSTOM: Use custom experiment_definition
    - TEMPLATE: Use experiment_template
    
    Progress stages:
    - 5%: Initializing model and parameters
    - 10%: Building experiment steps
    - 15-85%: Running simulation (scaled by estimated step count)
    - 90%: Processing results
    - 95%: Calculating safety metrics
    - 100%: Complete
    """
    task_start_time = time.time()
    current_stage = "initialization"
    
    # Build context for logging
    task_context = {
        "simulation_id": simulation_id,
        "user_id": user_id,
        "chemistry": chemistry.value,
        "protocol": protocol.value,
        "c_rate": c_rate,
        "temperature_celsius": temperature_celsius,
        "cycles": cycles,
        "custom_parameters": custom_parameters,
        "experiment_mode": experiment_mode.value
    }
    
    logger.info(f"[TASK:{simulation_id}] Background task started")
    logger.info(f"[TASK:{simulation_id}] Parameters: {task_context}")
    
    admin_client = get_supabase_admin_client()
    
    # Estimate complexity for progress reporting
    estimated_steps = estimate_step_count(protocol, cycles, custom_parameters)
    is_thermal = custom_parameters and custom_parameters.get("thermal_mode") == "lumped"
    
    # Calculate timeout based on cycles and complexity
    timeout_seconds = min(
        cycles * DEFAULT_TIMEOUT_PER_CYCLE_SECONDS * (1.5 if is_thermal else 1.0),
        MAX_SIMULATION_TIMEOUT_SECONDS
    )
    
    logger.info(f"[TASK:{simulation_id}] Estimated steps: {estimated_steps}, thermal: {is_thermal}, timeout: {timeout_seconds}s")
    
    def update_progress(progress: int, stage: str = None):
        """Helper to update progress with logging"""
        nonlocal current_stage
        if stage:
            current_stage = stage
        try:
            admin_client.table("simulations").update({
                "progress": progress,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", simulation_id).execute()
            logger.debug(f"[TASK:{simulation_id}] Progress: {progress}% (stage: {current_stage})")
        except Exception as e:
            logger.warning(f"[TASK:{simulation_id}] Failed to update progress: {e}")
    
    try:
        # Stage 1: Initializing (5%)
        current_stage = "db_init"
        logger.info(f"[TASK:{simulation_id}] Starting: updating status to RUNNING")
        
        try:
            admin_client.table("simulations").update({
                "status": SimulationStatus.RUNNING.value,
                "started_at": datetime.utcnow().isoformat(),
                "progress": 5,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", simulation_id).execute()
        except Exception as e:
            logger.error(f"[TASK:{simulation_id}] Failed to update initial status: {e}")
            raise SimulationError(
                f"Failed to update simulation status: {str(e)}",
                stage=current_stage,
                context={"error_type": type(e).__name__}
            )
        
        # Stage 2: Building experiment (10%)
        current_stage = "preparing"
        await asyncio.sleep(0.1)  # Allow status update to propagate
        update_progress(10, "preparing")
        
        # Check memory before starting simulation
        memory_safe, memory_msg = check_memory_safe()
        if not memory_safe:
            raise SimulationError(
                f"Insufficient memory to start task: {memory_msg}",
                stage="memory_check",
                context=get_memory_usage()
            )
        
        # Stage 3: Running simulation (15-85%)
        current_stage = "simulation_execution"
        update_progress(15, "simulation_execution")
        
        logger.info(f"[TASK:{simulation_id}] Submitting to thread pool executor (timeout: {timeout_seconds}s)")
        
        # Run simulation in thread pool with timeout
        loop = asyncio.get_event_loop()
        
        try:
            # Use functools.partial to pass all arguments including experiment mode
            from functools import partial
            simulation_func = partial(
                run_pybamm_simulation,
                simulation_id=simulation_id,
                chemistry=chemistry,
                protocol=protocol,
                c_rate=c_rate,
                temperature_celsius=temperature_celsius,
                cycles=cycles,
                custom_parameters=custom_parameters,
                experiment_mode=experiment_mode,
                experiment_definition=experiment_definition,
                experiment_template=experiment_template
            )
            results = await asyncio.wait_for(
                loop.run_in_executor(simulation_executor, simulation_func),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            elapsed = time.time() - task_start_time
            logger.error(f"[TASK:{simulation_id}] Simulation timed out after {elapsed:.1f}s (limit: {timeout_seconds}s)")
            raise SimulationError(
                f"Simulation timed out after {timeout_seconds}s. Consider reducing cycles or simplifying parameters.",
                stage="timeout",
                context={
                    "timeout_seconds": timeout_seconds,
                    "elapsed_seconds": elapsed,
                    "cycles": cycles,
                    "is_thermal": is_thermal
                }
            )
        
        simulation_duration = time.time() - task_start_time
        logger.info(f"[TASK:{simulation_id}] Simulation completed in {simulation_duration:.2f}s")
        
        # Stage 4: Processing results (90%)
        current_stage = "processing_results"
        update_progress(90, "processing_results")
        
        # Stage 5: Finalizing (95%)
        current_stage = "finalizing"
        update_progress(95, "finalizing")
        
        # Stage 6: Complete (100%)
        current_stage = "saving_results"
        logger.info(f"[TASK:{simulation_id}] Saving results to database")
        
        try:
            admin_client.table("simulations").update({
                "status": SimulationStatus.COMPLETED.value,
                "progress": 100,
                "results": results,
                "completed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", simulation_id).execute()
        except Exception as e:
            logger.error(f"[TASK:{simulation_id}] Failed to save results: {e}")
            raise SimulationError(
                f"Simulation completed but failed to save results: {str(e)}",
                stage=current_stage,
                context={"error_type": type(e).__name__}
            )
        
        # Update usage tracking - call RPC to increment count
        current_stage = "usage_tracking"
        try:
            admin_client.rpc("increment_simulation_count", {"uid": user_id}).execute()
        except Exception as e:
            logger.warning(f"[TASK:{simulation_id}] Failed to update usage tracking: {e}")
            # Don't fail the simulation for usage tracking errors
        
        total_duration = time.time() - task_start_time
        logger.info(f"[TASK:{simulation_id}] Task completed successfully in {total_duration:.2f}s")
        log_simulation_context(simulation_id, "TASK_COMPLETED", total_duration_s=f"{total_duration:.2f}")
        
    except SimulationError as e:
        total_duration = time.time() - task_start_time
        error_details = e.to_dict()
        error_msg = f"[{e.stage}] {e.message}"
        
        logger.error(f"[TASK:{simulation_id}] SimulationError in stage '{e.stage}' after {total_duration:.2f}s")
        logger.error(f"[TASK:{simulation_id}] Error details: {error_details}")
        
        try:
            admin_client.table("simulations").update({
                "status": SimulationStatus.FAILED.value,
                "error_message": error_msg,
                "results": {"error_details": error_details},
                "completed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", simulation_id).execute()
        except Exception as db_error:
            logger.error(f"[TASK:{simulation_id}] Failed to save error status: {db_error}")
            
    except Exception as e:
        total_duration = time.time() - task_start_time
        error_traceback = traceback.format_exc()
        error_msg = f"[{current_stage}] Unexpected error: {type(e).__name__}: {str(e)}"
        
        logger.error(f"[TASK:{simulation_id}] Unexpected error in stage '{current_stage}' after {total_duration:.2f}s")
        logger.error(f"[TASK:{simulation_id}] Error: {type(e).__name__}: {str(e)}")
        logger.error(f"[TASK:{simulation_id}] Traceback:\n{error_traceback}")
        
        error_details = {
            "error": str(e),
            "error_type": type(e).__name__,
            "stage": current_stage,
            "duration_seconds": total_duration,
            "traceback": error_traceback[:2000],
            "context": task_context
        }
        
        try:
            admin_client.table("simulations").update({
                "status": SimulationStatus.FAILED.value,
                "error_message": error_msg[:500],  # Limit error message length
                "results": {"error_details": error_details},
                "completed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", simulation_id).execute()
        except Exception as db_error:
            logger.error(f"[TASK:{simulation_id}] Failed to save error status: {db_error}")
