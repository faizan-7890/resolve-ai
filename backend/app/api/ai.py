from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
import json

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import Problem, Clarification, Diagnosis, Solution, Task, Memory, User
from app.schemas.schemas import ClarificationOut, DiagnosisOut, SolutionOut, TaskOut
from app.services.ai_service import ai_service
from app.services.qdrant_service import qdrant_service
from app.api.activity import log_activity

router = APIRouter(prefix="/problems", tags=["ai"])

# Pydantic schemas for the AI endpoints
class AnswerItem(BaseModel):
    clarification_id: int
    answer: str

class AnswersSubmit(BaseModel):
    answers: List[AnswerItem]


@router.post("/{problem_id}/clarify/generate", response_model=List[ClarificationOut])
def generate_problem_clarifications(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate 3 clarifying questions for a problem if not already generated."""
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem workspace not found.")

    # Return existing questions if any exist
    existing = db.query(Clarification).filter(Clarification.problem_id == problem_id).all()
    if existing:
        return existing

    # Call AI Service
    questions = ai_service.generate_clarifications(problem.title, problem.description)
    
    clarifications = []
    for q in questions:
        c = Clarification(problem_id=problem_id, question=q)
        db.add(c)
        clarifications.append(c)
        
    problem.status = "Clarifying"
    log_activity(db, problem_id, "Clarifications Generated", f"{len(questions)} clarifying questions created by AI.")
    db.commit()
    for c in clarifications:
        db.refresh(c)
    return clarifications


@router.post("/{problem_id}/clarify/answer", response_model=List[ClarificationOut])
def submit_clarification_answers(
    problem_id: int,
    answers_data: AnswersSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit answers to clarifying questions and progress the workspace status."""
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem workspace not found.")

    for item in answers_data.answers:
        clar = db.query(Clarification).filter(
            Clarification.id == item.clarification_id, 
            Clarification.problem_id == problem_id
        ).first()
        if clar:
            clar.answer = item.answer
            
    problem.status = "Diagnosing"
    log_activity(db, problem_id, "Answers Submitted", f"{len(answers_data.answers)} clarification answers provided.")
    db.commit()
    
    # Return updated list
    return db.query(Clarification).filter(Clarification.problem_id == problem_id).all()


@router.post("/{problem_id}/diagnose", response_model=DiagnosisOut)
def run_diagnosis(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Run Diagnosis Engine: 5 Whys, SWOT, and First Principles."""
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem workspace not found.")

    # Retrieve all QAs
    qas = db.query(Clarification).filter(Clarification.problem_id == problem_id).all()
    qa_list = [{"question": q.question, "answer": q.answer or ""} for q in qas]

    # RAG: Search Qdrant for similar past cases to inject into diagnosis
    rag_context = None
    query_text = f"Problem: {problem.title}. Details: {problem.description}"
    query_vector = ai_service.get_embedding(query_text)
    similar_cases = qdrant_service.search_similar(query_vector, current_user.id, limit=3)
    if similar_cases:
        rag_context = similar_cases

    # Generate Diagnosis (with RAG context if available)
    diag_data = ai_service.generate_diagnosis(problem.title, problem.description, qa_list, rag_context=rag_context)

    # Delete previous diagnosis if running again
    db.query(Diagnosis).filter(Diagnosis.problem_id == problem_id).delete()

    diagnosis = Diagnosis(
        problem_id=problem_id,
        root_causes=json.dumps(diag_data.get("root_causes", [])),
        swot_analysis=json.dumps(diag_data.get("swot_analysis", {})),
        first_principles=json.dumps(diag_data.get("first_principles", []))
    )
    db.add(diagnosis)
    log_activity(db, problem_id, "Diagnosis Completed", "5 Whys, SWOT Analysis, and First Principles generated.")
    db.commit()
    db.refresh(diagnosis)
    return diagnosis


@router.post("/{problem_id}/solutions", response_model=List[SolutionOut])
def generate_solutions(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate solution options and score them using Strategy/Critic Agents."""
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem workspace not found.")

    diagnosis = db.query(Diagnosis).filter(Diagnosis.problem_id == problem_id).first()
    if not diagnosis:
        raise HTTPException(
            status_code=400, 
            detail="Cannot generate solutions without running the diagnosis first."
        )

    diag_dict = {
        "root_causes": json.loads(diagnosis.root_causes or "[]"),
        "swot_analysis": json.loads(diagnosis.swot_analysis or "{}"),
        "first_principles": json.loads(diagnosis.first_principles or "[]")
    }

    # Call AI
    solutions_data = ai_service.generate_solutions(problem.title, problem.description, diag_dict)

    # Clear previous solutions if any
    db.query(Solution).filter(Solution.problem_id == problem_id).delete()

    solutions = []
    for item in solutions_data:
        sol = Solution(
            problem_id=problem_id,
            title=item.get("title", "Untitled Strategy"),
            strategy_details=item.get("strategy_details", ""),
            score=item.get("score", 0.0),
            impact=item.get("impact", 0.0),
            confidence=item.get("confidence", 0.0),
            risk=item.get("risk", 0.0),
            constraints=item.get("constraints", ""),
            selected=False
        )
        db.add(sol)
        solutions.append(sol)
        
    problem.status = "Planning"
    log_activity(db, problem_id, "Solutions Generated", f"{len(solutions)} strategy options scored by Strategist & Critic agents.")
    db.commit()
    for s in solutions:
        db.refresh(s)
    return solutions


@router.post("/{problem_id}/solutions/{solution_id}/select", response_model=List[SolutionOut])
def select_solution(
    problem_id: int,
    solution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Select the primary solution strategy to implement."""
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem workspace not found.")

    solutions = db.query(Solution).filter(Solution.problem_id == problem_id).all()
    found = False
    for sol in solutions:
        if sol.id == solution_id:
            sol.selected = True
            found = True
        else:
            sol.selected = False
            
    if not found:
        raise HTTPException(status_code=404, detail="Solution not found in this problem.")
    
    selected_title = next((s.title for s in solutions if s.id == solution_id), "Unknown")
    log_activity(db, problem_id, "Strategy Selected", f"Selected: {selected_title}")
    db.commit()
    return solutions


@router.post("/{problem_id}/plan", response_model=List[TaskOut])
def generate_tasks_plan(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Convert the selected solution into a task roadmap and checklist."""
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem workspace not found.")

    selected_sol = db.query(Solution).filter(Solution.problem_id == problem_id, Solution.selected == True).first()
    if not selected_sol:
        raise HTTPException(status_code=400, detail="Please select a solution strategy first.")

    # Call AI
    tasks_data = ai_service.generate_plan(problem.title, selected_sol.title, selected_sol.strategy_details)

    # Clear previous tasks if any
    db.query(Task).filter(Task.problem_id == problem_id).delete()

    tasks = []
    for item in tasks_data:
        t = Task(
            problem_id=problem_id,
            title=item.get("title", "Execute action"),
            priority=item.get("priority", "Medium"),
            timeline=item.get("timeline", "Day 1"),
            status="Pending"
        )
        db.add(t)
        tasks.append(t)
        
    problem.status = "Execution"
    log_activity(db, problem_id, "Execution Plan Generated", f"{len(tasks)} milestone tasks created from selected strategy.")
    db.commit()
    for t in tasks:
        db.refresh(t)
    return tasks


@router.post("/{problem_id}/resolve")
def resolve_problem_and_index_memory(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a problem workspace as fully Resolved and index it into semantic memory (RAG)."""
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem workspace not found.")
        
    problem.status = "Resolved"
    
    # Save to memory vector DB
    selected_sol = db.query(Solution).filter(Solution.problem_id == problem_id, Solution.selected == True).first()
    sol_str = selected_sol.strategy_details if selected_sol else "No strategy selected"
    
    summary_text = f"Problem: {problem.title}. Details: {problem.description}"
    sol_summary_text = f"Strategy: {selected_sol.title if selected_sol else 'N/A'}. Details: {sol_str}"
    
    # Generate Embedding
    emb = ai_service.get_embedding(summary_text)
    
    memory = Memory(
        user_id=current_user.id,
        problem_summary=summary_text,
        solution_summary=sol_summary_text,
        embedding_vector=json.dumps(emb)
    )
    db.add(memory)
    db.flush()  # Get memory.id before commit for Qdrant upsert

    # Upsert vector to Qdrant
    qdrant_service.upsert_memory(
        memory_id=memory.id,
        vector=emb,
        user_id=current_user.id,
        problem_summary=summary_text,
        solution_summary=sol_summary_text,
    )

    log_activity(db, problem_id, "Problem Resolved", "Workspace resolved and indexed in semantic memory (RAG).")
    db.commit()
    return {"message": "Workspace resolved successfully and indexed in semantic memory."}


@router.get("/{problem_id}/similar", response_model=List[Dict[str, Any]])
def search_similar_resolved_cases(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search Qdrant vector database for contextually similar resolved cases."""
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.user_id == current_user.id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem workspace not found.")
        
    query_text = f"Problem: {problem.title}. Details: {problem.description}"
    query_vector = ai_service.get_embedding(query_text)
    
    # Search Qdrant for top-3 similar cases (filtered by user)
    results = qdrant_service.search_similar(query_vector, current_user.id, limit=3)
    
    # Fallback to manual search if Qdrant is unavailable
    if not results and not qdrant_service.is_available:
        memories = db.query(Memory).filter(Memory.user_id == current_user.id).all()
        for mem in memories:
            try:
                mem_vector = json.loads(mem.embedding_vector)
                if len(query_vector) != len(mem_vector):
                    continue
                dot_product = sum(q*m for q, m in zip(query_vector, mem_vector))
                results.append({
                    "id": mem.id,
                    "problem_summary": mem.problem_summary,
                    "solution_summary": mem.solution_summary,
                    "similarity": round(dot_product, 3)
                })
            except Exception:
                continue
        results.sort(key=lambda x: x["similarity"], reverse=True)
        results = results[:3]
    
    return results
