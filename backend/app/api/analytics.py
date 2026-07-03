from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import Problem, Task, User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("")
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return aggregated analytics data for the current user's workspaces."""
    problems = db.query(Problem).filter(Problem.user_id == current_user.id).all()

    # Status distribution
    status_counts = {}
    category_counts = {}
    for p in problems:
        status_counts[p.status] = status_counts.get(p.status, 0) + 1
        category_counts[p.category] = category_counts.get(p.category, 0) + 1

    # Task completion across all problems
    problem_ids = [p.id for p in problems]
    total_tasks = 0
    completed_tasks = 0
    if problem_ids:
        total_tasks = db.query(func.count(Task.id)).filter(Task.problem_id.in_(problem_ids)).scalar() or 0
        completed_tasks = db.query(func.count(Task.id)).filter(
            Task.problem_id.in_(problem_ids),
            Task.status == "Done"
        ).scalar() or 0

    task_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0

    # Recent activity (last 5 problems created/resolved)
    recent = (
        db.query(Problem)
        .filter(Problem.user_id == current_user.id)
        .order_by(Problem.created_at.desc())
        .limit(5)
        .all()
    )
    recent_activity = [
        {"title": p.title, "status": p.status, "created_at": p.created_at.isoformat()}
        for p in recent
    ]

    return {
        "status_counts": status_counts,
        "category_counts": category_counts,
        "task_completion": {
            "total": total_tasks,
            "completed": completed_tasks,
            "rate": task_rate
        },
        "recent_activity": recent_activity
    }
