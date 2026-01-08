import logging
import jwt
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel

from app.supabase_client import get_supabase_client_with_token, get_supabase_admin_client, settings

logger = logging.getLogger(__name__)

router = APIRouter()


class UsageResponse(BaseModel):
    id: str
    user_id: str
    simulations_count: int
    simulations_limit: int
    api_calls_count: int
    api_calls_limit: int
    period_start: datetime
    period_end: datetime
    last_simulation_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    simulations_remaining: Optional[int] = None
    api_calls_remaining: Optional[int] = None
    usage_percentage: Optional[float] = None


class ApiCallLogResponse(BaseModel):
    id: str
    user_id: str
    endpoint: str
    method: str
    status_code: Optional[int]
    response_time_ms: Optional[int]
    created_at: datetime


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


def compute_usage_stats(usage_data: dict) -> dict:
    """Add computed statistics to usage data"""
    simulations_count = usage_data.get("simulations_count", 0)
    simulations_limit = usage_data.get("simulations_limit", 100)
    api_calls_count = usage_data.get("api_calls_count", 0)
    api_calls_limit = usage_data.get("api_calls_limit", 10000)
    
    usage_data["simulations_remaining"] = max(0, simulations_limit - simulations_count)
    usage_data["api_calls_remaining"] = max(0, api_calls_limit - api_calls_count)
    usage_data["usage_percentage"] = round((simulations_count / simulations_limit) * 100, 2) if simulations_limit > 0 else 0
    
    return usage_data


@router.get("/", response_model=UsageResponse)
async def get_usage(
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Get current usage statistics for the authenticated user"""
    logger.info(f"GET /usage - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        # Get current period usage
        response = supabase.table("usage_tracking").select("*").eq("user_id", user_id).order("period_start", desc=True).limit(1).execute()
        
        if not response.data:
            # Create initial usage record if none exists
            logger.info(f"Creating initial usage record for user {user_id}")
            now = datetime.utcnow()
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Calculate period end (first day of next month)
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)
            
            new_usage = supabase.table("usage_tracking").insert({
                "user_id": user_id,
                "simulations_count": 0,
                "simulations_limit": 100,
                "api_calls_count": 0,
                "api_calls_limit": 10000,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat()
            }).execute()
            
            if new_usage.data:
                usage_data = compute_usage_stats(new_usage.data[0])
                return usage_data
            else:
                raise HTTPException(status_code=500, detail="Failed to create usage record")
        
        usage_data = compute_usage_stats(response.data[0])
        logger.info(f"GET /usage - Retrieved usage for user {user_id}")
        return usage_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /usage - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs", response_model=List[ApiCallLogResponse])
async def get_api_logs(
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None),
    limit: int = 100,
    offset: int = 0
):
    """Get API call logs for the authenticated user"""
    logger.info(f"GET /usage/logs - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        response = supabase.table("api_call_logs").select("*").eq("user_id", user_id).order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        logger.info(f"GET /usage/logs - Retrieved {len(response.data)} logs")
        return response.data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /usage/logs - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_usage_summary(
    user_id: str = Depends(get_user_id),
    authorization: str = Header(None)
):
    """Get a summary of usage including recent activity"""
    logger.info(f"GET /usage/summary - user_id: {user_id}")
    
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        
        # Get usage stats
        usage_response = supabase.table("usage_tracking").select("*").eq("user_id", user_id).order("period_start", desc=True).limit(1).execute()
        
        # Get simulation counts by status
        simulations_response = supabase.table("simulations").select("status").eq("user_id", user_id).execute()
        
        status_counts = {}
        for sim in simulations_response.data:
            status = sim.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Get recent simulations
        recent_response = supabase.table("simulations").select("id,name,status,created_at").eq("user_id", user_id).order("created_at", desc=True).limit(5).execute()
        
        usage_data = usage_response.data[0] if usage_response.data else {}
        
        summary = {
            "current_period": {
                "simulations_used": usage_data.get("simulations_count", 0),
                "simulations_limit": usage_data.get("simulations_limit", 100),
                "api_calls_used": usage_data.get("api_calls_count", 0),
                "api_calls_limit": usage_data.get("api_calls_limit", 10000),
                "period_start": usage_data.get("period_start"),
                "period_end": usage_data.get("period_end")
            },
            "simulation_stats": {
                "total": len(simulations_response.data),
                "by_status": status_counts
            },
            "recent_simulations": recent_response.data
        }
        
        logger.info(f"GET /usage/summary - Retrieved summary for user {user_id}")
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /usage/summary - Exception: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def log_api_call(user_id: str, endpoint: str, method: str, status_code: int, response_time_ms: int):
    """Log an API call (called by middleware)"""
    try:
        admin_client = get_supabase_admin_client()
        
        admin_client.table("api_call_logs").insert({
            "user_id": user_id,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time_ms": response_time_ms
        }).execute()
        
        # Increment API call count
        admin_client.table("usage_tracking").update({
            "api_calls_count": admin_client.table("usage_tracking").select("api_calls_count").eq("user_id", user_id).execute().data[0].get("api_calls_count", 0) + 1,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("user_id", user_id).execute()
        
    except Exception as e:
        logger.error(f"Failed to log API call: {type(e).__name__}: {str(e)}")


async def check_rate_limit(user_id: str) -> bool:
    """Check if user has exceeded rate limits. Returns True if allowed, False if rate limited."""
    try:
        admin_client = get_supabase_admin_client()
        
        response = admin_client.table("usage_tracking").select("api_calls_count,api_calls_limit").eq("user_id", user_id).execute()
        
        if not response.data:
            return True  # No usage record, allow
        
        usage = response.data[0]
        return usage.get("api_calls_count", 0) < usage.get("api_calls_limit", 10000)
        
    except Exception as e:
        logger.error(f"Failed to check rate limit: {type(e).__name__}: {str(e)}")
        return True  # Allow on error to avoid blocking users


async def increment_simulation_count(user_id: str):
    """Increment the simulation count for a user"""
    try:
        admin_client = get_supabase_admin_client()
        
        # Get current count
        response = admin_client.table("usage_tracking").select("simulations_count").eq("user_id", user_id).execute()
        
        if response.data:
            current_count = response.data[0].get("simulations_count", 0)
            admin_client.table("usage_tracking").update({
                "simulations_count": current_count + 1,
                "last_simulation_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).execute()
            
    except Exception as e:
        logger.error(f"Failed to increment simulation count: {type(e).__name__}: {str(e)}")
