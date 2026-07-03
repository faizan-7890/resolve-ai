from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import json
import io

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import Problem, Clarification, Diagnosis, Solution, Task, User

router = APIRouter(prefix="/problems", tags=["export"])


@router.get("/{problem_id}/export")
def export_problem_report(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export a structured Markdown report for a problem workspace."""
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem workspace not found.")

    lines = []
    lines.append(f"# ResolveAI Report: {problem.title}")
    lines.append("")
    lines.append(f"**Status:** {problem.status}  ")
    lines.append(f"**Category:** {problem.category}  ")
    lines.append(f"**Urgency:** {problem.urgency}  ")
    lines.append(f"**Created:** {problem.created_at.strftime('%Y-%m-%d %H:%M')}  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Description
    lines.append("## Problem Description")
    lines.append("")
    lines.append(problem.description)
    lines.append("")

    # Clarifications
    clarifications = db.query(Clarification).filter(Clarification.problem_id == problem_id).all()
    if clarifications:
        lines.append("---")
        lines.append("")
        lines.append("## Clarifying Questions & Answers")
        lines.append("")
        for i, c in enumerate(clarifications, 1):
            lines.append(f"**Q{i}:** {c.question}  ")
            lines.append(f"**A{i}:** {c.answer or '_Not answered_'}  ")
            lines.append("")

    # Diagnosis
    diagnosis = db.query(Diagnosis).filter(Diagnosis.problem_id == problem_id).first()
    if diagnosis:
        lines.append("---")
        lines.append("")
        lines.append("## Diagnosis")
        lines.append("")

        try:
            root_causes = json.loads(diagnosis.root_causes or "[]")
            if root_causes:
                lines.append("### Root Cause Analysis (5 Whys)")
                lines.append("")
                for i, rc in enumerate(root_causes, 1):
                    lines.append(f"{i}. {rc}")
                lines.append("")
        except Exception:
            pass

        try:
            swot = json.loads(diagnosis.swot_analysis or "{}")
            if swot:
                lines.append("### SWOT Analysis")
                lines.append("")
                for section in ['strengths', 'weaknesses', 'opportunities', 'threats']:
                    items = swot.get(section, [])
                    if items:
                        lines.append(f"**{section.capitalize()}:**")
                        for item in items:
                            lines.append(f"- {item}")
                        lines.append("")
        except Exception:
            pass

        try:
            fp = json.loads(diagnosis.first_principles or "[]")
            if fp:
                lines.append("### First Principles Decomposition")
                lines.append("")
                for i, p in enumerate(fp, 1):
                    lines.append(f"{i}. {p}")
                lines.append("")
        except Exception:
            pass

    # Solutions
    solutions = db.query(Solution).filter(Solution.problem_id == problem_id).order_by(Solution.score.desc()).all()
    if solutions:
        lines.append("---")
        lines.append("")
        lines.append("## Strategy Options")
        lines.append("")
        for sol in solutions:
            selected_marker = " ✅ **SELECTED**" if sol.selected else ""
            lines.append(f"### {sol.title}{selected_marker}")
            lines.append("")
            lines.append(f"{sol.strategy_details}")
            lines.append("")
            lines.append(f"| Metric | Score |")
            lines.append(f"|--------|-------|")
            lines.append(f"| Overall Score | {sol.score:.1f} |")
            lines.append(f"| Impact | {sol.impact:.1f}/10 |")
            lines.append(f"| Confidence | {sol.confidence:.1f}/10 |")
            lines.append(f"| Risk | {sol.risk:.1f}/10 |")
            lines.append("")
            if sol.constraints:
                lines.append(f"**Constraints:** {sol.constraints}")
                lines.append("")

    # Tasks
    tasks = db.query(Task).filter(Task.problem_id == problem_id).all()
    if tasks:
        lines.append("---")
        lines.append("")
        lines.append("## Execution Roadmap")
        lines.append("")
        done_count = sum(1 for t in tasks if t.status == "Done")
        lines.append(f"Progress: {done_count}/{len(tasks)} tasks completed")
        lines.append("")
        for t in tasks:
            checkbox = "x" if t.status == "Done" else " "
            lines.append(f"- [{checkbox}] **{t.title}** — _{t.priority} priority_ ({t.timeline or 'No timeline'})")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Generated by ResolveAI — AI Problem-Solving Workspace*")

    markdown_content = "\n".join(lines)

    # Return as downloadable markdown file
    buffer = io.BytesIO(markdown_content.encode("utf-8"))
    return StreamingResponse(
        buffer,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename=resolveai-report-{problem_id}.md"
        }
    )
