from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional, Any, Dict
from datetime import datetime

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None


# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    role: str = "user"

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Clarification Schemas ---
class ClarificationCreate(BaseModel):
    question: str

class ClarificationAnswer(BaseModel):
    answer: str

class ClarificationOut(BaseModel):
    id: int
    question: str
    answer: Optional[str] = None
    asked_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Diagnosis Schemas ---
class DiagnosisOut(BaseModel):
    id: int
    root_causes: Optional[str] = None      # Will contain JSON array
    swot_analysis: Optional[str] = None    # Will contain JSON object
    first_principles: Optional[str] = None  # Will contain JSON array
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Solution Schemas ---
class SolutionOut(BaseModel):
    id: int
    title: str
    strategy_details: str
    score: float
    impact: float
    confidence: float
    risk: float
    constraints: Optional[str] = None
    selected: bool

    model_config = ConfigDict(from_attributes=True)


# --- Task Schemas ---
class TaskCreate(BaseModel):
    title: str
    priority: str = "Medium"
    timeline: Optional[str] = None

class TaskUpdate(BaseModel):
    status: str  # "Pending", "In Progress", "Done"

class TaskOut(BaseModel):
    id: int
    title: str
    status: str
    priority: str
    timeline: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Problem Schemas ---
class ProblemBase(BaseModel):
    title: str
    description: str
    category: str = "General"
    urgency: str = "Medium"

class ProblemCreate(ProblemBase):
    pass

class ProblemOut(ProblemBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    clarifications: List[ClarificationOut] = []
    diagnoses: List[DiagnosisOut] = []
    solutions: List[SolutionOut] = []
    tasks: List[TaskOut] = []

    model_config = ConfigDict(from_attributes=True)


# --- Memory Schemas ---
class MemoryOut(BaseModel):
    id: int
    problem_summary: str
    solution_summary: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Activity Log Schemas ---
class ActivityLogOut(BaseModel):
    id: int
    action: str
    detail: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Settings Schemas ---
class SettingsOut(BaseModel):
    name: Optional[str] = None
    email: str
    role: str
    has_openai_key: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SettingsUpdate(BaseModel):
    name: Optional[str] = None
    openai_api_key: Optional[str] = None

