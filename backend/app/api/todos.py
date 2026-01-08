import logging
import jwt

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.supabase_client import get_supabase_client_with_token, settings

logger = logging.getLogger(__name__)

router = APIRouter()


class TodoCreate(BaseModel):
    title: str
    description: Optional[str] = None
    simulation_id: Optional[str] = None


class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    simulation_id: Optional[str] = None


class TodoResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str]
    completed: bool
    simulation_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


async def get_user_id(authorization: str = Header(None)):
    """Extract user ID from Authorization header using local JWT validation"""
    logger.info("=== AUTH: get_user_id called ===")
    logger.debug(f"Authorization header present: {authorization is not None}")
    logger.debug(f"Authorization header value: {authorization[:50] if authorization else 'None'}...")
    
    if not authorization:
        logger.warning("AUTH FAILED: Authorization header missing")
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        # Extract Bearer token
        token = authorization.replace("Bearer ", "").strip()
        logger.debug(f"Token extracted, length: {len(token) if token else 0}")
        logger.debug(f"Token prefix: {token[:20] if token else 'None'}...")
        
        if not token:
            logger.warning("AUTH FAILED: Empty token after Bearer prefix removal")
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
        # Validate JWT locally using the Supabase JWT secret
        logger.info("Validating JWT token locally...")
        logger.debug(f"Using JWT secret: {settings.jwt_secret[:10]}...")
        
        try:
            # Decode and validate the JWT token
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=["HS256"],
                audience="authenticated"
            )
            logger.debug(f"JWT payload: {payload}")
            
            # Extract user ID from the 'sub' claim
            user_id = payload.get("sub")
            if not user_id:
                logger.warning("AUTH FAILED: No 'sub' claim in JWT payload")
                raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
            
            logger.info(f"AUTH SUCCESS: User ID extracted from JWT: {user_id}")
            return user_id
            
        except jwt.ExpiredSignatureError:
            logger.warning("AUTH FAILED: Token has expired")
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidAudienceError:
            logger.warning("AUTH FAILED: Invalid token audience")
            raise HTTPException(status_code=401, detail="Invalid token audience")
        except jwt.InvalidTokenError as e:
            logger.warning(f"AUTH FAILED: Invalid token - {str(e)}")
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"AUTH EXCEPTION: {type(e).__name__}: {error_msg}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=401, detail=f"Invalid token: {error_msg}")


@router.get("/", response_model=List[TodoResponse])
async def get_todos(user_id: str = Depends(get_user_id), authorization: str = Header(None)):
    """Get all todos for the current user"""
    logger.info(f"GET /todos - user_id: {user_id}")
    try:
        # Create a Supabase client with the user's access token for authenticated requests
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            logger.warning("GET /todos - No token provided")
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        logger.debug(f"GET /todos - Creating Supabase client with token")
        supabase = get_supabase_client_with_token(token)
        logger.debug(f"GET /todos - Querying todos table for user_id: {user_id}")
        response = supabase.table("todos").select("*").eq("user_id", user_id).execute()
        logger.info(f"GET /todos - Retrieved {len(response.data)} todos")
        return response.data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /todos - Exception: {type(e).__name__}: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=TodoResponse)
async def create_todo(todo: TodoCreate, user_id: str = Depends(get_user_id), authorization: str = Header(None)):
    """Create a new todo"""
    logger.info(f"POST /todos - user_id: {user_id}, title: {todo.title}")
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            logger.warning("POST /todos - No token provided")
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        logger.debug(f"POST /todos - Inserting todo for user_id: {user_id}")
        insert_data = {
            "user_id": user_id,
            "title": todo.title,
            "description": todo.description,
            "completed": False
        }
        if todo.simulation_id:
            insert_data["simulation_id"] = todo.simulation_id
        
        response = supabase.table("todos").insert(insert_data).execute()
        
        if not response.data:
            logger.warning("POST /todos - Insert returned no data")
            raise HTTPException(status_code=400, detail="Failed to create todo")
        
        logger.info(f"POST /todos - Created todo with id: {response.data[0].get('id')}")
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"POST /todos - Exception: {type(e).__name__}: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(todo_id: str, user_id: str = Depends(get_user_id), authorization: str = Header(None)):
    """Get a specific todo"""
    logger.info(f"GET /todos/{todo_id} - user_id: {user_id}")
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            logger.warning(f"GET /todos/{todo_id} - No token provided")
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        response = supabase.table("todos").select("*").eq("id", todo_id).eq("user_id", user_id).execute()
        
        if not response.data:
            logger.warning(f"GET /todos/{todo_id} - Todo not found")
            raise HTTPException(status_code=404, detail="Todo not found")
        
        logger.info(f"GET /todos/{todo_id} - Found todo")
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /todos/{todo_id} - Exception: {type(e).__name__}: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{todo_id}", response_model=TodoResponse)
async def update_todo(todo_id: str, todo: TodoUpdate, user_id: str = Depends(get_user_id), authorization: str = Header(None)):
    """Update a todo"""
    logger.info(f"PUT /todos/{todo_id} - user_id: {user_id}, updates: {todo}")
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            logger.warning(f"PUT /todos/{todo_id} - No token provided")
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        update_data = {}
        if todo.title is not None:
            update_data["title"] = todo.title
        if todo.description is not None:
            update_data["description"] = todo.description
        if todo.completed is not None:
            update_data["completed"] = todo.completed
        if todo.simulation_id is not None:
            update_data["simulation_id"] = todo.simulation_id if todo.simulation_id else None
        
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        logger.debug(f"PUT /todos/{todo_id} - Update data: {update_data}")
        response = supabase.table("todos").update(update_data).eq("id", todo_id).eq("user_id", user_id).execute()
        
        if not response.data:
            logger.warning(f"PUT /todos/{todo_id} - Todo not found")
            raise HTTPException(status_code=404, detail="Todo not found")
        
        logger.info(f"PUT /todos/{todo_id} - Updated successfully")
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PUT /todos/{todo_id} - Exception: {type(e).__name__}: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{todo_id}")
async def delete_todo(todo_id: str, user_id: str = Depends(get_user_id), authorization: str = Header(None)):
    """Delete a todo"""
    logger.info(f"DELETE /todos/{todo_id} - user_id: {user_id}")
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            logger.warning(f"DELETE /todos/{todo_id} - No token provided")
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        response = supabase.table("todos").delete().eq("id", todo_id).eq("user_id", user_id).execute()
        
        if not response.data:
            logger.warning(f"DELETE /todos/{todo_id} - Todo not found")
            raise HTTPException(status_code=404, detail="Todo not found")
        
        logger.info(f"DELETE /todos/{todo_id} - Deleted successfully")
        return {"message": "Todo deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DELETE /todos/{todo_id} - Exception: {type(e).__name__}: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=str(e))

