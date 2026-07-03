from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.ticket import Ticket, TicketActivityLog

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("", response_model=None)
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns ticket metrics, category breakdowns, and recent activity logs
    aggregated dynamically for the React Dashboard.
    """
    if current_user.role == "admin":
        tickets = db.query(Ticket).all()
    else:
        tickets = db.query(Ticket).filter(Ticket.user_id == current_user.id).all()
        
    status_counts = {}
    category_counts = {}
    
    for t in tickets:
        status_counts[t.status] = status_counts.get(t.status, 0) + 1
        category_counts[t.category] = category_counts.get(t.category, 0) + 1
        
    # Fetch recent activity logs
    if current_user.role == "admin":
        logs = db.query(TicketActivityLog).order_by(TicketActivityLog.created_at.desc()).limit(5).all()
    else:
        logs = (
            db.query(TicketActivityLog)
            .join(Ticket)
            .filter(Ticket.user_id == current_user.id)
            .order_by(TicketActivityLog.created_at.desc())
            .limit(5)
            .all()
        )
        
    recent_activity = []
    for log in logs:
        # Load associated ticket title
        t_title = log.ticket.title if log.ticket else "Ticket Action"
        recent_activity.append({
            "title": f"{t_title} - {log.action}",
            "status": log.action,
            "created_at": log.created_at.isoformat()
        })
        
    total_tickets = len(tickets)
    resolved_tickets = sum(1 for t in tickets if t.status == "Resolved")
    rate = resolved_tickets / total_tickets if total_tickets > 0 else 0.0
    
    return {
        "status_counts": status_counts,
        "category_counts": category_counts,
        "task_completion": {
            "total": total_tickets,
            "completed": resolved_tickets,
            "rate": rate
        },
        "recent_activity": recent_activity
    }
