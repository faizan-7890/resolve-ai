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

    # Advanced Calculations for Recharts Charts
    from datetime import datetime, timedelta, timezone

    # 1. Calculate resolution times by category
    resolved_list = [t for t in tickets if t.status == "Resolved"]
    category_times = {}
    category_resolutions = {}
    for t in resolved_list:
        if t.created_at and t.updated_at:
            duration_hours = (t.updated_at - t.created_at).total_seconds() / 3600.0
            category_times[t.category] = category_times.get(t.category, 0.0) + duration_hours
            category_resolutions[t.category] = category_resolutions.get(t.category, 0) + 1

    resolution_times = []
    for cat in category_counts.keys():
        count = category_resolutions.get(cat, 0)
        avg_time = round(category_times.get(cat, 0.0) / count, 1) if count > 0 else 0.0
        resolution_times.append({
            "category": cat,
            "avg_time_hours": avg_time,
            "resolved_count": count
        })

    # 2. Calculate daily trends for the last 30 days
    now = datetime.now(timezone.utc)
    daily_counts = {}
    for i in range(30):
        date_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_counts[date_str] = 0

    for t in tickets:
        if t.created_at:
            date_str = t.created_at.strftime("%Y-%m-%d")
            if date_str in daily_counts:
                daily_counts[date_str] += 1

    daily_trends = [{"date": d, "count": daily_counts[d]} for d in sorted(daily_counts.keys())]

    # 3. Calculate escalation stats by category
    category_escalated = {}
    category_total = {}
    for t in tickets:
        category_total[t.category] = category_total.get(t.category, 0) + 1
        if t.status == "Escalated":
            category_escalated[t.category] = category_escalated.get(t.category, 0) + 1

    escalation_stats = []
    for cat, total in category_total.items():
        escalated = category_escalated.get(cat, 0)
        rate_pct = round((escalated / total) * 100, 1) if total > 0 else 0.0
        escalation_stats.append({
            "category": cat,
            "escalation_rate": rate_pct,
            "escalated_count": escalated,
            "total_count": total
        })

    return {
        "status_counts": status_counts,
        "category_counts": category_counts,
        "task_completion": {
            "total": total_tickets,
            "completed": resolved_tickets,
            "rate": rate
        },
        "recent_activity": recent_activity,
        "daily_trends": daily_trends,
        "resolution_times": resolution_times,
        "escalation_stats": escalation_stats
    }
