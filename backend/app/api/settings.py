from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import User
from app.schemas.schemas import SettingsOut, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user profile and configuration."""
    return SettingsOut(
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        has_openai_key=bool(current_user.openai_api_key),
        created_at=current_user.created_at
    )


@router.patch("", response_model=SettingsOut)
def update_settings(
    settings_in: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user profile settings and/or OpenAI API key."""
    if settings_in.name is not None:
        current_user.name = settings_in.name

    if settings_in.openai_api_key is not None and settings_in.openai_api_key.strip():
        # Basic validation: OpenAI keys start with sk-
        key = settings_in.openai_api_key.strip()
        if not key.startswith("sk-"):
            raise HTTPException(status_code=400, detail="Invalid API key format. OpenAI keys start with 'sk-'.")
        current_user.openai_api_key = key

    db.commit()
    db.refresh(current_user)

    return SettingsOut(
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        has_openai_key=bool(current_user.openai_api_key),
        created_at=current_user.created_at
    )
