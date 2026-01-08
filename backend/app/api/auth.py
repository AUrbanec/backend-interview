import logging
import jwt

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.supabase_client import get_supabase_client, settings

logger = logging.getLogger(__name__)

router = APIRouter()


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    user_id: str
    email: str
    access_token: str
    refresh_token: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None


@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignUpRequest):
    """Sign up a new user"""
    logger.info(f"POST /auth/signup - email: {request.email}")
    try:
        supabase = get_supabase_client()
        
        # Prepare user metadata
        user_metadata = {}
        if request.full_name:
            user_metadata["full_name"] = request.full_name
        
        logger.debug(f"POST /auth/signup - Creating user with metadata: {user_metadata}")
        
        # Sign up user with Supabase Auth
        response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": user_metadata
            }
        })
        
        if not response.user:
            logger.warning("POST /auth/signup - Sign up returned no user")
            raise HTTPException(status_code=400, detail="Failed to create user")
        
        if not response.session:
            logger.info(f"POST /auth/signup - User created, awaiting email confirmation: {response.user.id}")
            # User created but needs email confirmation
            return AuthResponse(
                user_id=response.user.id,
                email=response.user.email,
                access_token="",
                refresh_token=""
            )
        
        logger.info(f"POST /auth/signup - User created successfully: {response.user.id}")
        return AuthResponse(
            user_id=response.user.id,
            email=response.user.email,
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"POST /auth/signup - Exception: {type(e).__name__}: {error_msg}")
        logger.exception("Full traceback:")
        
        # Handle common Supabase auth errors
        if "User already registered" in error_msg:
            raise HTTPException(status_code=400, detail="User already registered")
        if "Password" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        
        raise HTTPException(status_code=400, detail=f"Sign up failed: {error_msg}")


@router.post("/signin", response_model=AuthResponse)
async def signin(request: SignInRequest):
    """Sign in an existing user"""
    logger.info(f"POST /auth/signin - email: {request.email}")
    try:
        supabase = get_supabase_client()
        
        logger.debug(f"POST /auth/signin - Authenticating user")
        response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if not response.user or not response.session:
            logger.warning("POST /auth/signin - Sign in returned no user/session")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        logger.info(f"POST /auth/signin - User signed in successfully: {response.user.id}")
        return AuthResponse(
            user_id=response.user.id,
            email=response.user.email,
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"POST /auth/signin - Exception: {type(e).__name__}: {error_msg}")
        logger.exception("Full traceback:")
        
        # Handle common auth errors
        if "Invalid login credentials" in error_msg:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if "Email not confirmed" in error_msg:
            raise HTTPException(status_code=401, detail="Please confirm your email before signing in")
        
        raise HTTPException(status_code=401, detail=f"Sign in failed: {error_msg}")


@router.post("/signout")
async def signout(authorization: str = Header(None)):
    """Sign out the current user"""
    logger.info("POST /auth/signout")
    try:
        if not authorization:
            logger.warning("POST /auth/signout - No authorization header")
            raise HTTPException(status_code=401, detail="Authorization header missing")
        
        token = authorization.replace("Bearer ", "").strip()
        if not token:
            logger.warning("POST /auth/signout - Empty token")
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
        # Validate token first to ensure it's a valid session
        logger.debug("POST /auth/signout - Validating token before signout")
        try:
            jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=["HS256"],
                audience="authenticated"
            )
        except jwt.ExpiredSignatureError:
            logger.info("POST /auth/signout - Token already expired, treating as signed out")
            return {"message": "Signed out successfully"}
        except jwt.InvalidTokenError as e:
            logger.warning(f"POST /auth/signout - Invalid token: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Sign out from Supabase
        supabase = get_supabase_client()
        supabase.auth.sign_out()
        
        logger.info("POST /auth/signout - User signed out successfully")
        return {"message": "Signed out successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"POST /auth/signout - Exception: {type(e).__name__}: {error_msg}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=f"Sign out failed: {error_msg}")


@router.get("/me", response_model=UserResponse)
async def get_current_user(authorization: str = Header(None)):
    """Get current user information"""
    logger.info("GET /auth/me")
    try:
        if not authorization:
            logger.warning("GET /auth/me - No authorization header")
            raise HTTPException(status_code=401, detail="Authorization header missing")
        
        token = authorization.replace("Bearer ", "").strip()
        if not token:
            logger.warning("GET /auth/me - Empty token")
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
        # Validate and decode JWT locally
        logger.debug("GET /auth/me - Validating JWT token")
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=["HS256"],
                audience="authenticated"
            )
        except jwt.ExpiredSignatureError:
            logger.warning("GET /auth/me - Token expired")
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidAudienceError:
            logger.warning("GET /auth/me - Invalid token audience")
            raise HTTPException(status_code=401, detail="Invalid token audience")
        except jwt.InvalidTokenError as e:
            logger.warning(f"GET /auth/me - Invalid token: {str(e)}")
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
        
        user_id = payload.get("sub")
        email = payload.get("email")
        user_metadata = payload.get("user_metadata", {})
        full_name = user_metadata.get("full_name")
        
        if not user_id:
            logger.warning("GET /auth/me - No user ID in token")
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
        
        logger.info(f"GET /auth/me - Retrieved user info for: {user_id}")
        return UserResponse(
            id=user_id,
            email=email or "",
            full_name=full_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"GET /auth/me - Exception: {type(e).__name__}: {error_msg}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=f"Failed to get user info: {error_msg}")
