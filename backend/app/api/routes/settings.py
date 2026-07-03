from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.models.user import User
from app.core.config import settings

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("", response_model=None)
def get_settings(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user profile settings.
    """
    return {
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "has_openai_key": bool(settings.OPENAI_API_KEY),
        "created_at": current_user.created_at.isoformat()
    }
