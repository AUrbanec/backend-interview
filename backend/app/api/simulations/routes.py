"""
FastAPI route handlers for simulations API.
"""
import logging
import jwt
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks

from app.supabase_client import get_supabase_client_with_token, settings

from .schemas import (
    SimulationStatus,
    BatteryChemistry,
    ProtocolType,
    SimulationCreate,
    SimulationResponse,
    CompareSimulationsRequest,
    MultiChemistryRequest,
)
from .simulation_runner import run_simulation_task

logger = logging.getLogger(__name__)

router = APIRouter()


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
