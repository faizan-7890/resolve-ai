from pydantic import BaseModel, EmailStr, ConfigDict, field_validator, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
from app.schemas.validators import CommonValidators

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
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        return CommonValidators.validate_password(v)
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is None:
            return v
        return CommonValidators.validate_name(v)
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        return CommonValidators.validate_enum_field(v, ["user", "admin"])

class UserOut(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Clarification Schemas ---
class ClarificationCreate(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    
    @field_validator('question')
    @classmethod
    def validate_question(cls, v):
        return CommonValidators.sanitize_text(v)

class ClarificationAnswer(BaseModel):
    answer: str = Field(..., min_length=1, max_length=5000)
    
    @field_validator('answer')
    @classmethod
    def validate_answer(cls, v):
        return CommonValidators.sanitize_text(v)

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
    title: str = Field(..., min_length=3, max_length=500)
    priority: str = "Medium"
    timeline: Optional[str] = Field(None, max_length=500)
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        return CommonValidators.sanitize_text(v)
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        return CommonValidators.validate_enum_field(v, ["Low", "Medium", "High", "Critical"])
    
    @field_validator('timeline')
    @classmethod
    def validate_timeline(cls, v):
        if v is None:
            return v
        return CommonValidators.sanitize_text(v)

class TaskUpdate(BaseModel):
    status: str
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        return CommonValidators.validate_enum_field(v, ["Pending", "In Progress", "Done"])

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
    title: str = Field(..., min_length=5, max_length=500)
    description: str = Field(..., min_length=10, max_length=5000)
    category: str = "General"
    urgency: str = "Medium"
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        v = CommonValidators.sanitize_text(v)
        CommonValidators.validate_non_empty_string(v, "title", min_length=5)
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        v = CommonValidators.sanitize_text(v)
        CommonValidators.validate_non_empty_string(v, "description", min_length=10)
        return v
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        return CommonValidators.validate_enum_field(
            v, ["General", "Technical", "Billing", "Feature Request", "Bug Report"]
        )
    
    @field_validator('urgency')
    @classmethod
    def validate_urgency(cls, v):
        return CommonValidators.validate_enum_field(v, ["Low", "Medium", "High", "Critical"])

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
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is None:
            return v
        return CommonValidators.validate_name(v)

