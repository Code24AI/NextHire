from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey,Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, nullable=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    current_action = Column(String(50), default="initial")
    iteration_count = Column(Integer, default=0)
    awaiting_user_input = Column(Boolean, default=False)

    # Relationships
    job_posts = relationship("JobPost", back_populates="session")
    messages = relationship("Message", back_populates="session")


class JobPost(Base):
    __tablename__ = "job_posts"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.session_id"), index=True)
    title = Column(String(200), nullable=False)
    company = Column(String(200), default="Our Company")
    location = Column(String(200), default="Remote")
    job_type = Column(String(50), default="Full-time")
    experience_level = Column(String(50), default="Mid")
    description = Column(Text)
    responsibilities = Column(JSON)
    requirements = Column(JSON)
    benefits = Column(JSON)
    salary_range = Column(String(100), default="Competitive")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_saved = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    deadline = Column(DateTime)
    company_id = Column(String, nullable=True)

    # Relationships
    session = relationship("Session", back_populates="job_posts")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.session_id"), index=True)
    message_type = Column(String(20))
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="messages")


class SavedJobPost(Base):
    __tablename__ = "saved_job_posts"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), index=True)
    job_post_id = Column(Integer, ForeignKey("job_posts.id"))

    title = Column(String(200), nullable=False)
    company = Column(String(200))
    location = Column(String(200))
    job_type = Column(String(50))
    experience_level = Column(String(50))
    description = Column(Text)
    responsibilities = Column(JSON)
    requirements = Column(JSON)
    benefits = Column(JSON)
    salary_range = Column(String(100))
    company_id = Column(String, nullable=True)
    saved_at = Column(DateTime(timezone=True), server_default=func.now())
    total_iterations = Column(Integer, default=0)

    user_feedback = Column(Text)
    completion_time_minutes = Column(Integer)
    coding_challenge = Column(Text, nullable=True)
    deadline = Column(DateTime)
    
    is_processed = Column(Boolean, default=False)
    #interview_time = Column(DateTime)
    
    is_recomanded = Column(Boolean, default=False)
    #  Relationship
    candidate_jobs = relationship("CandidateJobs", back_populates="job_post")


from sqlalchemy import Text

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String)
    email = Column(String, unique=True, index=True)
    image = Column(String, nullable=True)  # URL or file path
    address = Column(String)
    highest_education = Column(String)
    institution = Column(String)
    graduation_year = Column(String)
    cgpa = Column(String)
    skills = Column(Text)
    previous_company = Column(String)
    positions = Column(String)
    responsibilities = Column(Text)
    experience_years = Column(String)
    projects_description = Column(Text)
    project_techstack = Column(Text)
    project_link = Column(String)
    linkedin = Column(String)
    github = Column(String)
    current_status = Column(String)
    strength = Column(Text)
    weakness = Column(Text)
    when_you_can_join = Column(String)

    # ✅ New Password Field (stored as hash)
    password = Column(String, nullable=False)

    # ✅ Relationship
    candidate_jobs = relationship("CandidateJobs", back_populates="candidate")
class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)  # Store as hash
    address = Column(Text, nullable=True)
    logo = Column(String, nullable=True)  # URL or file path

    # Optional but useful fields:
    website = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    industry = Column(String, nullable=True)
    company_size = Column(String, nullable=True)
    founded_year = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)


class CandidateJobs(Base):
    __tablename__ = "candidates_jobs"

    id = Column(Integer, primary_key=True, index=True)

    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    job_post_id = Column(Integer, ForeignKey("saved_job_posts.id"))

    name = Column(String)
    phone = Column(String)
    email = Column(String)
    address = Column(String)
    highest_education = Column(String)
    institution = Column(String)
    graduation_year = Column(String)
    cgpa = Column(String)
    skills = Column(Text)
    previous_company = Column(String)
    positions = Column(String)
    responsibilities = Column(Text)
    experience_years = Column(String)
    projects_description = Column(Text)
    project_techstack = Column(Text)
    project_link = Column(String)
    linkedin = Column(String)
    github = Column(String)
    current_status = Column(String)
    strength = Column(Text)
    weakness = Column(Text)
    when_you_can_join = Column(String)

    # ✅ Fixed Relationships
    candidate = relationship("Candidate", back_populates="candidate_jobs")
    job_post = relationship("SavedJobPost", back_populates="candidate_jobs")

    
class QAScoring(Base):
    __tablename__ = "qa_scoring"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    candidate_id = Column(Integer, nullable=False)
    job_id = Column(Integer, nullable=False)

    correctness_score = Column(Float, nullable=False)
    efficiency_score = Column(Float, nullable=False)
    readability_score = Column(Float, nullable=False)
    edge_case_handling_score = Column(Float, nullable=False)
    overall_score = Column(Float, nullable=False)

    strengths = Column(String, nullable=True)
    weaknesses = Column(String, nullable=True)

class CodingChallenge(Base):
    __tablename__ = 'coding_challenges'

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer,  nullable=False)
    candidate_id = Column(Integer,  nullable=False)
    coding_challenge = Column(Text, nullable=False)
    answer = Column(Text)    

class ShortlistedScore(Base):
    __tablename__ = "shortlisted_score"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, nullable=False)
    candidate_id = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    name = Column(String)
    phone = Column(String)
    email = Column(String)

class FinalShortlistedCandidate(Base):
    __tablename__ = "final_shortlisted_candidates"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, nullable=False)
    candidate_id = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    name = Column(String)
    phone = Column(String)
    email = Column(String)
    sent_email=Column(Boolean, default=False)
    interview_date = Column(DateTime)
    interview_given = Column(Boolean, default=False)

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, nullable=False)
    job_id = Column(Integer, nullable=False)
    hire_decision = Column(Boolean, nullable=False, default=False)
    comment = Column(Text, nullable=True)
class Finalstatus(Base):
    __tablename__ = "finalstatus"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, nullable=False)
    job_id = Column(Integer, nullable=False)
    status = Column(Boolean, nullable=True)
    comment = Column(Text, nullable=True)

class Conversation(Base):
    __tablename__ = 'conversations'
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(128), index=True)
    question = Column(Text)
    answer = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())