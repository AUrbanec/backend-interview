from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.supabase_client import get_supabase_client, get_supabase_client_with_token

router = APIRouter()


class TodoCreate(BaseModel):
    title: str
    description: Optional[str] = None


class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None


class TodoResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str]
    completed: bool
    created_at: datetime
    updated_at: datetime


async def get_user_id(authorization: str = Header(None)):
    """Extract user ID from Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        # Extract Bearer token
        token = authorization.replace("Bearer ", "").strip()
        if not token:
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
        # Get Supabase client and verify the token
        supabase = get_supabase_client()
        
        # Use get_user with the access token to verify and get user info
        response = supabase.auth.get_user(token)
        
        # Handle different response formats
        if hasattr(response, 'user') and response.user:
            return response.user.id
        elif hasattr(response, 'data') and response.data and hasattr(response.data, 'user'):
            return response.data.user.id
        else:
            raise HTTPException(status_code=401, detail="Invalid token: user not found")
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(status_code=401, detail=f"Invalid token: {error_msg}")


@router.get("/", response_model=List[TodoResponse])
async def get_todos(user_id: str = Depends(get_user_id), authorization: str = Header(None)):
    """Get all todos for the current user"""
    try:
        # Create a Supabase client with the user's access token for authenticated requests
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        response = supabase.table("todos").select("*").eq("user_id", user_id).execute()
        return response.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=TodoResponse)
async def create_todo(todo: TodoCreate, user_id: str = Depends(get_user_id), authorization: str = Header(None)):
    """Create a new todo"""
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        response = supabase.table("todos").insert({
            "user_id": user_id,
            "title": todo.title,
            "description": todo.description,
            "completed": False
        }).execute()
        
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create todo")
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(todo_id: str, user_id: str = Depends(get_user_id), authorization: str = Header(None)):
    """Get a specific todo"""
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        response = supabase.table("todos").select("*").eq("id", todo_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Todo not found")
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{todo_id}", response_model=TodoResponse)
async def update_todo(todo_id: str, todo: TodoUpdate, user_id: str = Depends(get_user_id), authorization: str = Header(None)):
    """Update a todo"""
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        update_data = {}
        if todo.title is not None:
            update_data["title"] = todo.title
        if todo.description is not None:
            update_data["description"] = todo.description
        if todo.completed is not None:
            update_data["completed"] = todo.completed
        
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        response = supabase.table("todos").update(update_data).eq("id", todo_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Todo not found")
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{todo_id}")
async def delete_todo(todo_id: str, user_id: str = Depends(get_user_id), authorization: str = Header(None)):
    """Delete a todo"""
    try:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        if not token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        supabase = get_supabase_client_with_token(token)
        response = supabase.table("todos").delete().eq("id", todo_id).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Todo not found")
        
        return {"message": "Todo deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

