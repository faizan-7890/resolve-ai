from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import ActivityLog, Problem, User
from app.schemas.schemas import ActivityLogOut

router = APIRouter(prefix="/problems", tags=["activity"])


@router.get("/{problem_id}/activity", response_model=List[ActivityLogOut])
def get_activity_log(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the full activity timeline for a problem workspace, ordered newest first."""
    # Verify ownership
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        return []

    logs = (
        db.query(ActivityLog)
        .filter(ActivityLog.problem_id == problem_id)
        .order_by(ActivityLog.created_at.desc())
        .all()
    )
    return logs


def log_activity(db: Session, problem_id: int, action: str, detail: str = None):
    """Helper function to insert an activity log entry."""
    entry = ActivityLog(
        problem_id=problem_id,
        action=action,
        detail=detail
    )
    db.add(entry)
