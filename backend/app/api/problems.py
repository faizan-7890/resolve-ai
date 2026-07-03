from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.models import Problem, Task
from app.schemas.schemas import ProblemCreate, ProblemOut, TaskOut, TaskUpdate
from app.api.deps import get_current_user
from app.models.models import User
from app.api.activity import log_activity

router = APIRouter(prefix="/problems", tags=["problems"])

@router.get("", response_model=List[ProblemOut])
def read_problems(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all problems created by the current authenticated user."""
    return db.query(Problem).filter(Problem.user_id == current_user.id).order_by(Problem.created_at.desc()).all()

@router.post("", response_model=ProblemOut, status_code=status.HTTP_201_CREATED)
def create_problem(
    problem_in: ProblemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new problem workspace in the database."""
    problem = Problem(
        user_id=current_user.id,
        title=problem_in.title,
        description=problem_in.description,
        category=problem_in.category,
        urgency=problem_in.urgency,
        status="Intake"
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)
    log_activity(db, problem.id, "Problem Created", f"Workspace '{problem.title}' created in {problem.category} category.")
    db.commit()
    return problem

@router.get("/{problem_id}", response_model=ProblemOut)
def read_problem_by_id(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the full details of a specific problem workspace."""
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem workspace not found."
        )
    return problem

@router.delete("/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_problem(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a problem workspace from the database."""
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem workspace not found."
        )
    db.delete(problem)
    db.commit()
    return

# Task status updates
@router.patch("/{problem_id}/tasks/{task_id}", response_model=TaskOut)
def update_task_status(
    problem_id: int,
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update the execution status of a checklist task."""
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem workspace not found."
        )
        
    task = db.query(Task).filter(Task.id == task_id, Task.problem_id == problem_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found in this problem workspace."
        )
        
    task.status = task_update.status
    log_activity(db, problem_id, "Task Status Updated", f"Task '{task.title}' marked as {task_update.status}.")
    db.commit()
    db.refresh(task)
    return task
