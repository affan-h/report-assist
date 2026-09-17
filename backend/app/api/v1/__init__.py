from fastapi import APIRouter
from app.api.v1.process import process_router

router = APIRouter()
router.include_router(process_router, prefix="/api/v1/process")

__all__ = ["router"]
