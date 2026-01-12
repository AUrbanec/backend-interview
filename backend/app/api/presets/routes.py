"""
FastAPI route handlers for presets API.
"""
import logging
import jwt
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header

from app.supabase_client import get_supabase_client_with_token, settings

from .schemas import (
    BatteryChemistry,
    PresetCreate,
    PresetUpdate,
    PresetResponse,
)
from .pybamm_options import (
    get_model_options_schema,
    validate_model_options,
    get_recommended_options_for_use_case,
)
from .parameter_sets import (
    get_parameter_set_info,
    get_parameter_sets_for_chemistry,
    get_chemistry_defaults,
    list_all_parameter_sets,
)

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


# =============================================================================
# PRESET CRUD ENDPOINTS
# =============================================================================

@router.post("/", response_model=PresetResponse)
async def create_preset(
    preset: PresetCreate,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Create a new parameter preset"""
    logger.info(f"POST /presets - user_id: {user_id}, name: {preset.name}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        # Check if preset with same name already exists for this user
        existing = supabase.table("parameter_presets").select("id").eq("user_id", user_id).eq("name", preset.name).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="A preset with this name already exists")
        
        response = supabase.table("parameter_presets").insert({
            "user_id": user_id,
            "name": preset.name,
            "description": preset.description,
            "is_public": preset.is_public,
            "chemistry": preset.chemistry.value,
            "c_rate": preset.c_rate,
            "temperature_celsius": preset.temperature_celsius,
            "cycles": preset.cycles,
            "custom_parameters": preset.custom_parameters or {}
        }).execute()
        
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create preset")
        
        logger.info(f"POST /presets - Created preset {response.data[0]['id']}")
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"POST /presets - Exception: {type(e).__name__}: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[PresetResponse])
async def get_presets(
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None),
    include_public: bool = True,
    include_system: bool = True
):
    """Get all presets available to the user (own, public, and system presets)"""
    logger.info(f"GET /presets - user_id: {user_id}, include_public: {include_public}, include_system: {include_system}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        # Build query to get user's own presets
        all_presets = []
        
        # Get user's own presets
        own_response = supabase.table("parameter_presets").select("*").eq("user_id", user_id).execute()
        all_presets.extend(own_response.data)
        
        # Get public presets from other users
        if include_public:
            public_response = supabase.table("parameter_presets").select("*").eq("is_public", True).neq("user_id", user_id).execute()
            all_presets.extend(public_response.data)
        
        # Get system presets (user_id is null)
        if include_system:
            system_response = supabase.table("parameter_presets").select("*").is_("user_id", "null").execute()
            all_presets.extend(system_response.data)
        
        # Sort by name
        all_presets.sort(key=lambda x: x.get("name", ""))
        
        logger.info(f"GET /presets - Retrieved {len(all_presets)} presets")
        return all_presets
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /presets - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{preset_id}", response_model=PresetResponse)
async def get_preset(
    preset_id: str,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Get a specific preset by ID"""
    logger.info(f"GET /presets/{preset_id} - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        # Get preset - RLS will handle access control
        response = supabase.table("parameter_presets").select("*").eq("id", preset_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Preset not found")
        
        preset = response.data[0]
        
        # Check access: user owns it, it's public, or it's a system preset
        if preset.get("user_id") != user_id and not preset.get("is_public") and preset.get("user_id") is not None:
            raise HTTPException(status_code=403, detail="Access denied to this preset")
        
        return preset
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /presets/{preset_id} - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{preset_id}", response_model=PresetResponse)
async def update_preset(
    preset_id: str,
    preset: PresetUpdate,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Update a preset (only own presets can be updated)"""
    logger.info(f"PUT /presets/{preset_id} - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        # Build update data
        update_data = {"updated_at": datetime.utcnow().isoformat()}
        
        if preset.name is not None:
            update_data["name"] = preset.name
        if preset.description is not None:
            update_data["description"] = preset.description
        if preset.is_public is not None:
            update_data["is_public"] = preset.is_public
        if preset.chemistry is not None:
            update_data["chemistry"] = preset.chemistry.value
        if preset.c_rate is not None:
            update_data["c_rate"] = preset.c_rate
        if preset.temperature_celsius is not None:
            update_data["temperature_celsius"] = preset.temperature_celsius
        if preset.cycles is not None:
            update_data["cycles"] = preset.cycles
        if preset.custom_parameters is not None:
            update_data["custom_parameters"] = preset.custom_parameters
        
        # Update only user's own preset
        response = supabase.table("parameter_presets").update(update_data).eq("id", preset_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Preset not found or you don't have permission to update it")
        
        logger.info(f"PUT /presets/{preset_id} - Updated successfully")
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PUT /presets/{preset_id} - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{preset_id}")
async def delete_preset(
    preset_id: str,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Delete a preset (only own presets can be deleted)"""
    logger.info(f"DELETE /presets/{preset_id} - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        # Delete only user's own preset
        response = supabase.table("parameter_presets").delete().eq("id", preset_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Preset not found or you don't have permission to delete it")
        
        logger.info(f"DELETE /presets/{preset_id} - Deleted successfully")
        return {"message": "Preset deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DELETE /presets/{preset_id} - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{preset_id}/duplicate", response_model=PresetResponse)
async def duplicate_preset(
    preset_id: str,
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None),
    new_name: Optional[str] = None
):
    """Duplicate a preset (can duplicate any accessible preset)"""
    logger.info(f"POST /presets/{preset_id}/duplicate - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        # Get the original preset
        original_response = supabase.table("parameter_presets").select("*").eq("id", preset_id).execute()
        
        if not original_response.data:
            raise HTTPException(status_code=404, detail="Preset not found")
        
        original = original_response.data[0]
        
        # Create duplicate with new name
        duplicate_name = new_name or f"{original['name']} (Copy)"
        
        response = supabase.table("parameter_presets").insert({
            "user_id": user_id,
            "name": duplicate_name,
            "description": original.get("description"),
            "is_public": False,  # Duplicates are private by default
            "chemistry": original.get("chemistry"),
            "c_rate": original.get("c_rate"),
            "temperature_celsius": original.get("temperature_celsius"),
            "cycles": original.get("cycles"),
            "custom_parameters": original.get("custom_parameters", {})
        }).execute()
        
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to duplicate preset")
        
        logger.info(f"POST /presets/{preset_id}/duplicate - Created duplicate {response.data[0]['id']}")
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"POST /presets/{preset_id}/duplicate - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# PYBAMM OPTIONS REFERENCE ENDPOINTS
# =============================================================================

@router.get("/pybamm/models")
async def get_pybamm_models():
    """
    Get all available PyBAMM models and their descriptions.
    
    Returns comprehensive information about:
    - Lithium-ion models (SPM, SPMe, DFN, MPM, etc.)
    - Lead-acid models
    - Equivalent circuit models
    """
    schema = get_model_options_schema()
    return {
        "lithium_ion": schema["lithium_ion_models"],
        "lead_acid": schema["lead_acid_models"],
        "equivalent_circuit": schema["equivalent_circuit_models"],
    }


@router.get("/pybamm/options")
async def get_pybamm_options():
    """
    Get all available PyBAMM model options (submodels).
    
    Returns comprehensive information about configurable options like:
    - thermal (isothermal, lumped, x-lumped, x-full)
    - SEI (none, constant, reaction limited, etc.)
    - lithium_plating (none, reversible, irreversible)
    - particle (Fickian diffusion, uniform profile, etc.)
    - And many more...
    """
    schema = get_model_options_schema()
    return schema["model_options"]


@router.get("/pybamm/parameter-sets")
async def get_pybamm_parameter_sets():
    """
    Get all available PyBAMM parameter sets.
    
    Returns information about validated parameter sets for different chemistries.
    """
    return list_all_parameter_sets()


@router.get("/pybamm/parameter-sets/{name}")
async def get_parameter_set_details(name: str):
    """
    Get detailed information about a specific parameter set.
    """
    info = get_parameter_set_info(name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Parameter set '{name}' not found")
    return info


@router.get("/pybamm/chemistry/{chemistry}")
async def get_chemistry_info(chemistry: str):
    """
    Get default parameters and recommended settings for a chemistry.
    """
    defaults = get_chemistry_defaults(chemistry.upper())
    if not defaults:
        raise HTTPException(status_code=404, detail=f"Chemistry '{chemistry}' not found")
    
    parameter_sets = get_parameter_sets_for_chemistry(chemistry.upper())
    
    return {
        **defaults,
        "available_parameter_sets": parameter_sets,
    }


@router.post("/pybamm/validate-options")
async def validate_options(options: dict):
    """
    Validate a dictionary of model options against available PyBAMM options.
    
    Returns validation errors if any options are invalid.
    """
    errors = validate_model_options(options)
    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


@router.get("/pybamm/recommendations/{use_case}")
async def get_recommendations(use_case: str):
    """
    Get recommended model options for a use case.
    
    Available use cases:
    - fast: Quick screening simulations
    - accurate: High-fidelity simulations
    - thermal: Thermal analysis
    - degradation: Degradation modeling
    - optimization: Parameter optimization
    """
    recommendations = get_recommended_options_for_use_case(use_case.lower())
    if not recommendations:
        raise HTTPException(
            status_code=404, 
            detail=f"Unknown use case '{use_case}'. Available: fast, accurate, thermal, degradation, optimization"
        )
    return recommendations
