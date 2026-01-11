"""
Experiments API module for managing experiment steps, templates, and drive cycles.
"""
from fastapi import APIRouter

from .routes import router as experiments_router

router = APIRouter()
router.include_router(experiments_router, prefix="/experiments", tags=["experiments"])

__all__ = ["router", "experiments_router"]
