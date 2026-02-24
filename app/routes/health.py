from fastapi import APIRouter
from app.models.schemas import APIResponse

router = APIRouter()


@router.get("/health", response_model=APIResponse)
async def health():
    return APIResponse(success=True, message="ok", data={"status": "healthy"}, errors=[])
