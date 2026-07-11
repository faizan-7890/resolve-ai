from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.core.config import settings
from pydantic import BaseModel

router = APIRouter(prefix="/settings", tags=["settings"])

class SettingsUpdate(BaseModel):
    name: str

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
        "has_openai_key": bool(settings.NVIDIA_NIM_API_KEY),
        "created_at": current_user.created_at.isoformat()
    }

@router.patch("", response_model=None)
def update_settings(
    settings_in: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update user profile name settings.
    """
    if settings_in.name is not None:
        current_user.name = settings_in.name

    db.commit()
    db.refresh(current_user)

    return {
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "has_openai_key": bool(settings.NVIDIA_NIM_API_KEY),
        "created_at": current_user.created_at.isoformat()
    }
