"""
FastAPI route handlers for experiments API.
CRUD operations for experiment steps, templates, and drive cycles.
"""
import logging
import jwt
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header

from app.supabase_client import get_supabase_client_with_token, settings

from ..simulations.schemas import (
    ExperimentStepCreate,
    ExperimentStepResponse,
    ExperimentTemplateCreate,
    ExperimentTemplateResponse,
    DriveCycleCreate,
    DriveCycleResponse,
    ExperimentDefinition,
)
from ..simulations.experiment_builder import validate_experiment_definition

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_user_id(authorization: str = Header(None)) -> str:
    """Extract user ID from Authorization header"""
    if not authorization:
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


# ============================================================================
# Experiment Steps CRUD
# ============================================================================

@router.get("/steps", response_model=List[ExperimentStepResponse])
async def get_experiment_steps(
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None),
    include_public: bool = True
):
    """Get all experiment steps (user's own + public)"""
    logger.info(f"GET /experiments/steps - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        # RLS will handle filtering, but we can also explicitly query
        response = supabase.table("experiment_steps").select("*").execute()
        
        return response.data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /experiments/steps - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/steps", response_model=ExperimentStepResponse)
async def create_experiment_step(
    step: ExperimentStepCreate,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Create a new experiment step"""
    logger.info(f"POST /experiments/steps - user_id: {user_id}, name: {step.name}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        step_data = {
            "user_id": user_id,
            "name": step.name,
            "description": step.description,
            "is_public": step.is_public,
            "step_type": step.step_type.value,
            "value": step.value,
            "value_unit": step.value_unit,
            "duration": step.duration,
            "termination": step.termination,
            "period": step.period,
            "temperature": step.temperature,
            "tags": step.tags,
            "direction": step.direction,
            "step_string": step.step_string,
            "drive_cycle_data": step.drive_cycle_data,
            "drive_cycle_type": step.drive_cycle_type,
        }
        
        response = supabase.table("experiment_steps").insert(step_data).execute()
        
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create experiment step")
        
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"POST /experiments/steps - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/steps/{step_id}", response_model=ExperimentStepResponse)
async def get_experiment_step(
    step_id: str,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Get a specific experiment step"""
    logger.info(f"GET /experiments/steps/{step_id} - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        response = supabase.table("experiment_steps").select("*").eq("id", step_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Experiment step not found")
        
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /experiments/steps/{step_id} - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/steps/{step_id}")
async def delete_experiment_step(
    step_id: str,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Delete an experiment step"""
    logger.info(f"DELETE /experiments/steps/{step_id} - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        response = supabase.table("experiment_steps").delete().eq("id", step_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Experiment step not found or not owned by user")
        
        return {"message": "Experiment step deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DELETE /experiments/steps/{step_id} - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Experiment Templates CRUD
# ============================================================================

@router.get("/templates", response_model=List[ExperimentTemplateResponse])
async def get_experiment_templates(
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Get all experiment templates (user's own + public)"""
    logger.info(f"GET /experiments/templates - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        response = supabase.table("experiment_templates").select("*").order("created_at", desc=True).execute()
        
        return response.data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /experiments/templates - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates", response_model=ExperimentTemplateResponse)
async def create_experiment_template(
    template: ExperimentTemplateCreate,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Create a new experiment template"""
    logger.info(f"POST /experiments/templates - user_id: {user_id}, name: {template.name}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        # Convert cycles to JSON-serializable format
        cycles_data = [cycle.model_dump() for cycle in template.cycles]
        
        template_data = {
            "user_id": user_id,
            "name": template.name,
            "description": template.description,
            "is_public": template.is_public,
            "cycles": cycles_data,
            "default_period": template.default_period,
            "default_temperature_celsius": template.default_temperature_celsius,
        }
        
        response = supabase.table("experiment_templates").insert(template_data).execute()
        
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create experiment template")
        
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"POST /experiments/templates - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates/{template_id}", response_model=ExperimentTemplateResponse)
async def get_experiment_template(
    template_id: str,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Get a specific experiment template"""
    logger.info(f"GET /experiments/templates/{template_id} - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        response = supabase.table("experiment_templates").select("*").eq("id", template_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Experiment template not found")
        
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /experiments/templates/{template_id} - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/templates/{template_id}")
async def delete_experiment_template(
    template_id: str,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Delete an experiment template"""
    logger.info(f"DELETE /experiments/templates/{template_id} - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        response = supabase.table("experiment_templates").delete().eq("id", template_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Experiment template not found or not owned by user")
        
        return {"message": "Experiment template deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DELETE /experiments/templates/{template_id} - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Drive Cycles CRUD
# ============================================================================

@router.get("/drive-cycles", response_model=List[DriveCycleResponse])
async def get_drive_cycles(
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Get all drive cycles (user's own + public)"""
    logger.info(f"GET /experiments/drive-cycles - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        response = supabase.table("drive_cycles").select("*").order("created_at", desc=True).execute()
        
        return response.data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /experiments/drive-cycles - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drive-cycles", response_model=DriveCycleResponse)
async def create_drive_cycle(
    drive_cycle: DriveCycleCreate,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Create a new drive cycle"""
    logger.info(f"POST /experiments/drive-cycles - user_id: {user_id}, name: {drive_cycle.name}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        # Calculate duration if not provided
        duration = drive_cycle.duration_seconds
        if duration is None and drive_cycle.data:
            duration = max(point[0] for point in drive_cycle.data)
        
        cycle_data = {
            "user_id": user_id,
            "name": drive_cycle.name,
            "description": drive_cycle.description,
            "is_public": drive_cycle.is_public,
            "cycle_type": drive_cycle.cycle_type,
            "data": drive_cycle.data,
            "duration_seconds": duration,
            "source": drive_cycle.source,
            "tags": drive_cycle.tags,
        }
        
        response = supabase.table("drive_cycles").insert(cycle_data).execute()
        
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create drive cycle")
        
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"POST /experiments/drive-cycles - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/drive-cycles/{cycle_id}", response_model=DriveCycleResponse)
async def get_drive_cycle(
    cycle_id: str,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Get a specific drive cycle"""
    logger.info(f"GET /experiments/drive-cycles/{cycle_id} - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        response = supabase.table("drive_cycles").select("*").eq("id", cycle_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Drive cycle not found")
        
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /experiments/drive-cycles/{cycle_id} - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/drive-cycles/{cycle_id}")
async def delete_drive_cycle(
    cycle_id: str,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Delete a drive cycle"""
    logger.info(f"DELETE /experiments/drive-cycles/{cycle_id} - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        response = supabase.table("drive_cycles").delete().eq("id", cycle_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Drive cycle not found or not owned by user")
        
        return {"message": "Drive cycle deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DELETE /experiments/drive-cycles/{cycle_id} - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Validation and Preview
# ============================================================================

@router.post("/validate")
async def validate_experiment(
    definition: ExperimentDefinition,
    user_id: str = Depends(get_user_id)
):
    """Validate an experiment definition"""
    logger.info(f"POST /experiments/validate - user_id: {user_id}")
    
    try:
        is_valid, errors = validate_experiment_definition(definition)
        
        return {
            "valid": is_valid,
            "errors": errors,
            "num_cycles": len(definition.cycles),
            "total_steps": sum(len(c.steps) * c.repeat for c in definition.cycles)
        }
        
    except Exception as e:
        logger.error(f"POST /experiments/validate - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/preview")
async def preview_experiment(
    definition: ExperimentDefinition,
    user_id: str = Depends(get_user_id)
):
    """Preview the PyBAMM experiment steps that will be generated"""
    logger.info(f"POST /experiments/preview - user_id: {user_id}")
    
    try:
        from ..simulations.experiment_builder import build_experiment_from_definition
        
        # Validate first
        is_valid, errors = validate_experiment_definition(definition)
        if not is_valid:
            return {
                "valid": False,
                "errors": errors,
                "preview": None
            }
        
        # Build the experiment steps
        steps = build_experiment_from_definition(definition)
        
        # Convert to string representation for preview
        preview_steps = []
        for i, step_group in enumerate(steps):
            if isinstance(step_group, tuple):
                preview_steps.append({
                    "cycle": i + 1,
                    "steps": [str(s) for s in step_group]
                })
            else:
                preview_steps.append({
                    "cycle": i + 1,
                    "steps": [str(step_group)]
                })
        
        return {
            "valid": True,
            "errors": [],
            "preview": preview_steps,
            "total_cycles": len(steps)
        }
        
    except Exception as e:
        logger.error(f"POST /experiments/preview - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
