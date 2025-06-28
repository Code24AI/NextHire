from pydantic import BaseModel, EmailStr
from typing import Optional,List
from datetime import datetime

class CandidateCreate(BaseModel):
    job_post_id: int  # <- New field
    id: int 
    name: str
    phone: str
    email: EmailStr
    address: Optional[str] = None
    highest_education: Optional[str] = None
    institution: Optional[str] = None
    graduation_year: Optional[str] = None
    cgpa: Optional[str] = None
    skills: Optional[str] = None
    previous_company: Optional[str] = None
    positions: Optional[str] = None
    responsibilities: Optional[str] = None
    experience_years: Optional[str] = None
    projects_description: Optional[str] = None
    project_techstack: Optional[str] = None
    project_link: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    current_status: Optional[str] = None
    strength: Optional[str] = None
    weakness: Optional[str] = None
    when_you_can_join: Optional[str] = None

class jobID(BaseModel):
    job_post_id: int  # <- New field


class CandidateOut(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[EmailStr]
    image: Optional[str]
    address: Optional[str]
    highest_education: Optional[str]
    institution: Optional[str]
    graduation_year: Optional[str]
    cgpa: Optional[str]
    skills: Optional[str]
    previous_company: Optional[str]
    positions: Optional[str]
    responsibilities: Optional[str]
    experience_years: Optional[str]
    projects_description: Optional[str]
    project_techstack: Optional[str]
    project_link: Optional[str]
    linkedin: Optional[str]
    github: Optional[str]
    current_status: Optional[str]
    strength: Optional[str]
    weakness: Optional[str]
    when_you_can_join: Optional[str]

class AppliedJobInfo(BaseModel):
    job_id: int
    title: str



class CandidateJobStats(BaseModel):
    candidate_id: int
    name: Optional[str] = None
    email: Optional[str] = None
    total_applied_jobs: int
    applied_jobs: List[AppliedJobInfo]

class QAScoreResponse(BaseModel):
    correctness_score: float
    efficiency_score: float
    readability_score: float
    edge_case_handling_score: float
    overall_score: float
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
class AppliedStatusResponse(BaseModel):
    applied: bool

class CodingChallengeResponse(BaseModel):
    coding_challenge: str

class CompanyResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: str
    address: Optional[str]
    logo: Optional[str]
    website: Optional[str]
    description: Optional[str]
    industry: Optional[str]
    company_size: Optional[str]
    founded_year: Optional[str]
    linkedin: Optional[str]

class SavedJobPostOut(BaseModel):
    id: int
    job_post_id: int
    title: str
    company: Optional[str]
    location: Optional[str]
    job_type: Optional[str]
    experience_level: Optional[str]
    description: Optional[str]
    responsibilities: Optional[List[str]]
    requirements: Optional[List[str]]
    benefits: Optional[List[str]]
    salary_range: Optional[str]
    saved_at: Optional[datetime]
    total_iterations: Optional[int]
    user_feedback: Optional[str]
    completion_time_minutes: Optional[int]
    coding_challenge: Optional[str]
    deadline: Optional[datetime]
    is_processed: Optional[bool]
    is_recomanded: Optional[bool]

class JobApplicationResponse(BaseModel):
    job_id: int
    job_title: str
    candidate_count: int

class TotalApplicationsResponse(BaseModel):
    total_applications: int

class JobRecommendationResponse(BaseModel):
    job_id: int
    candidate_id: int
    candidate_name: Optional[str]  # Nullable as per Candidate schema
    candidate_email: str  # Non-nullable as per Candidate schema
    job_title: str  # Non-nullable as per SavedJobPost schema
    hire_decision: bool  # Non-nullable with default False
    comment: Optional[str] 

# Pydantic model for response structure
class QAScoringResponse(BaseModel):
    candidate_id: int
    candidate_name: Optional[str]  # Nullable
    candidate_email: str  # Non-nullable
    job_id: int
    job_title: str  # Non-nullable
    question: str  # Non-nullable
    answer: str  # Non-nullable
    correctness_score: float  # Non-nullable
    efficiency_score: float  # Non-nullable
    readability_score: float  # Non-nullable
    edge_case_handling_score: float  # Non-nullable
    overall_score: float  # Non-nullable
    strengths: Optional[str]  # Nullable
    weaknesses: Optional[str]  # Nullable

class FinalShortlistedCandidateResponse(BaseModel):
    candidate_id: int
    candidate_name: Optional[str]  # Nullable
    candidate_email: Optional[str]  # Nullable
    job_id: int
    job_title: str  # Non-nullable
    score: float
    interview_date : Optional[datetime]
    interview_given : Optional[bool]
    sent_email: Optional[bool]

# Pydantic model for request body
class FinalStatusRequest(BaseModel):
    candidate_id: int
    job_id: int
    status: Optional[bool] = None  # True (accept), False (reject), null (unpublished/pending)
    comment: Optional[str] = None  # Optional comment

# Pydantic model for response
class FinalStatusResponse(BaseModel):
    id: int
    candidate_id: int
    job_id: int
    status: Optional[bool]
    status_text: str  # Human-readable status (Pending, Accepted, Rejected)
    comment: Optional[str]

class ShortlistedScoreResponse(BaseModel):
    id: int
    job_id: int
    candidate_id: int
    score: float
    name: str | None = None
    phone: str | None = None
    email: str | None = None

class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    image: Optional[str] = None
    address: Optional[str] = None
    highest_education: Optional[str] = None
    institution: Optional[str] = None
    graduation_year: Optional[str] = None
    cgpa: Optional[str] = None
    skills: Optional[str] = None
    previous_company: Optional[str] = None
    positions: Optional[str] = None
    responsibilities: Optional[str] = None
    experience_years: Optional[str] = None
    projects_description: Optional[str] = None
    project_techstack: Optional[str] = None
    project_link: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    current_status: Optional[str] = None
    strength: Optional[str] = None
    weakness: Optional[str] = None
    when_you_can_join: Optional[str] = None

class RecommendationWithCandidateResponse(BaseModel):
    candidate_name: str
    candidate_phone: Optional[str]
    candidate_email: str
    hire_decision: bool
    comment: Optional[str]

# --- Pydantic Response Model ---
class FinalShortlistedCandidateResponse(BaseModel):
    candidate_id: int
    candidate_name: Optional[str]  # Nullable
    candidate_email: Optional[str]  # Nullable
    job_id: int
    job_title: str  # Non-nullable
    score: float
    interview_date : Optional[datetime]
    interview_given : Optional[bool]
    sent_email: Optional[bool]

class InterviewStatusUpdate(BaseModel):
    candidate_id: int
    job_id: int
    interview_given: bool
class QuestionRequest(BaseModel):
    session_id: str = None
    question: str

class AnswerResponse(BaseModel):
    session_id: str
    answer: str