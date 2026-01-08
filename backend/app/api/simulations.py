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


class SimulationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    chemistry: BatteryChemistry = BatteryChemistry.LFP
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


def get_pybamm_model(chemistry: BatteryChemistry):
    """Get the appropriate PyBaMM model for the chemistry"""
    logger.info(f"Loading PyBaMM model for chemistry: {chemistry}")
    
    if chemistry == BatteryChemistry.LFP:
        model = pybamm.lithium_ion.DFN()
        parameter_values = pybamm.ParameterValues("Prada2013")
    elif chemistry == BatteryChemistry.NMC:
        model = pybamm.lithium_ion.DFN()
        parameter_values = pybamm.ParameterValues("Chen2020")
    elif chemistry == BatteryChemistry.NCA:
        model = pybamm.lithium_ion.DFN()
        parameter_values = pybamm.ParameterValues("NCA_Kim2011")
    elif chemistry == BatteryChemistry.LCO:
        model = pybamm.lithium_ion.DFN()
        parameter_values = pybamm.ParameterValues("Marquis2019")
    else:
        model = pybamm.lithium_ion.DFN()
        parameter_values = pybamm.ParameterValues("Chen2020")
    
    return model, parameter_values


def run_pybamm_simulation(
    simulation_id: str,
    chemistry: BatteryChemistry,
    c_rate: float,
    temperature_celsius: float,
    cycles: int,
    custom_parameters: Optional[dict] = None
) -> dict:
    """Run a PyBaMM simulation synchronously (to be run in thread pool)"""
    logger.info(f"Starting PyBaMM simulation {simulation_id}")
    logger.info(f"Parameters: chemistry={chemistry}, c_rate={c_rate}, temp={temperature_celsius}°C, cycles={cycles}")
    
    try:
        # Get model and parameters
        model, parameter_values = get_pybamm_model(chemistry)
        
        # Apply C-rate
        parameter_values.update({"Current function [A]": parameter_values["Nominal cell capacity [A.h]"] * c_rate})
        
        # Apply temperature
        parameter_values.update({"Ambient temperature [K]": temperature_celsius + 273.15})
        
        # Apply custom parameters if provided
        if custom_parameters:
            for key, value in custom_parameters.items():
                try:
                    parameter_values.update({key: value})
                except Exception as e:
                    logger.warning(f"Failed to apply custom parameter {key}: {e}")
        
        # Create experiment for cycling
        if cycles > 1:
            experiment = pybamm.Experiment(
                [
                    ("Discharge at {0}C until 2.5V".format(c_rate),
                     "Rest for 10 minutes",
                     "Charge at {0}C until 4.2V".format(c_rate / 2),
                     "Hold at 4.2V until C/50",
                     "Rest for 10 minutes")
                ] * cycles
            )
            sim = pybamm.Simulation(model, parameter_values=parameter_values, experiment=experiment)
            solution = sim.solve()
        else:
            # Single discharge - must provide t_eval
            # t_eval = [0, 3700/C] gives full discharge time at C-rate
            t_eval = [0, 3700 / c_rate]
            sim = pybamm.Simulation(model, parameter_values=parameter_values)
            solution = sim.solve(t_eval=t_eval)
        
        # Run simulation
        logger.info(f"Running simulation {simulation_id}...")
        
        # Extract results
        time = solution["Time [s]"].entries.tolist()
        voltage = solution["Voltage [V]"].entries.tolist()
        current = solution["Current [A]"].entries.tolist()
        
        # Try to get additional outputs if available
        results = {
            "time_seconds": time,
            "voltage_v": voltage,
            "current_a": current,
            "summary": {
                "max_voltage": float(np.max(voltage)),
                "min_voltage": float(np.min(voltage)),
                "total_time_hours": float(time[-1] / 3600) if time else 0,
                "chemistry": chemistry.value,
                "c_rate": c_rate,
                "temperature_celsius": temperature_celsius,
                "cycles": cycles
            }
        }
        
        # Add capacity if available
        try:
            capacity = solution["Discharge capacity [A.h]"].entries.tolist()
            results["discharge_capacity_ah"] = capacity
            results["summary"]["total_capacity_ah"] = float(np.max(capacity)) if capacity else 0
        except Exception:
            pass
        
        logger.info(f"Simulation {simulation_id} completed successfully")
        return results
        
    except Exception as e:
        logger.error(f"Simulation {simulation_id} failed: {type(e).__name__}: {str(e)}")
        raise


async def run_simulation_task(
    simulation_id: str,
    user_id: str,
    chemistry: BatteryChemistry,
    c_rate: float,
    temperature_celsius: float,
    cycles: int,
    custom_parameters: Optional[dict] = None
):
    """Background task to run simulation and update database"""
    logger.info(f"Background task started for simulation {simulation_id}")
    
    admin_client = get_supabase_admin_client()
    
    try:
        # Update status to running
        admin_client.table("simulations").update({
            "status": SimulationStatus.RUNNING.value,
            "started_at": datetime.utcnow().isoformat(),
            "progress": 10,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", simulation_id).execute()
        
        # Run simulation in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            simulation_executor,
            run_pybamm_simulation,
            simulation_id,
            chemistry,
            c_rate,
            temperature_celsius,
            cycles,
            custom_parameters
        )
        
        # Update with results
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
