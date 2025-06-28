from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from models import Candidate, SavedJobPost  # Import SavedJobPost model
from database import SessionLocal, engine, Base
from pydantic_models import CandidateCreate, jobID
from chat_llm_granite import chat 
import json
from fastapi.responses import JSONResponse
from models import ShortlistedScore,FinalShortlistedCandidate
from typing import List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter()
app = FastAPI()
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ShortlistedCandidateOut(BaseModel):
    candidate_id: int
    score: float
@router.post("/candidates/", status_code=201)
def create_candidate(candidate2: CandidateCreate, db: Session = Depends(get_db)):
   
   
    
    # Retrieve the job post using job_post_id
    job = db.query(SavedJobPost).filter(SavedJobPost.id == candidate2.job_post_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job post not found")

    
   

    # Do not save the candidate, just acknowledge for now
    return {
        "message": "Candidate data received and job post printed in console",
        "job_post_id": candidate2.job_post_id
    }

import json
import re

import json
import re
from langchain_core.messages import AIMessage  # Optional: If you're using LangChain

def extract_overall_score(response):
    # If it's a LangChain AIMessage (common case)
    if hasattr(response, "content"):
        content = response.content
    # If it's a dict (e.g., already parsed JSON)
    elif isinstance(response, dict):
        content = response.get("content", "")
    # If it's a string
    elif isinstance(response, str):
        content = response
    else:
        raise ValueError("Unsupported response format. Expected LangChain AIMessage, dict, or string.")

    content = content.strip()

    # Case 1: Try to parse clean JSON directly
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "overall_score" in parsed:
            return float(parsed["overall_score"])
    except json.JSONDecodeError:
        pass

    # Case 2: Try to extract JSON block from messy content
    try:
        json_part = re.search(r'{.*?"overall_score"\s*:\s*(\d+(\.\d+)?).*?}', content, re.DOTALL)
        if json_part:
            parsed_json = json.loads(json_part.group(0))
            return float(parsed_json["overall_score"])
    except Exception:
        pass

    # Case 3: Regex fallback
    try:
        match = re.search(r'"overall_score"\s*:\s*(\d+(\.\d+)?)', content)
        if match:
            return float(match.group(1))
    except Exception:
        pass

    # Case 4: The LLM directly returned the number as string
    try:
        return float(content)
    except ValueError:
        pass

    raise ValueError("Unable to extract overall_score from response.")



def get_llm_score(prompt: str):
    response = chat.invoke(prompt)  
    score = extract_overall_score(response)
    # Granite/GPT/etc.
    return {"score":score}  # Ensure the output is a valid JSON string

prompt_template = """You are an expert Resume scorer. You are tasked with evaluating a candidate for a job position.

CANDIDATE PROFILE:
Education: {education}, {institution} (Graduated: {graduation_year}, CGPA: {cgpa})
Experience: {experience_years} years as {position} at {previous_company}
Skills: {skills}
Projects: {projects_description} (Tech Stack: {project_techstack})
Responsibilities: {responsibility}
Strengths: {strength}
Weaknesses: {weakness}

JOB DETAILS:
Experience Level: {experience_level}
Description: {job_description}
Requirements: {requirements}
Responsibilities: {job_responsibilities}

TASK:
Strictly evaluate the candidate’s fit for the job by rigorously matching their profile to the job requirements. Use the following rules for scoring:

1. If any value in the candidate profile is 'N/A', 'null', missing, or empty, assign an overall_score of **10** or less.
2. If the candidate's skills, experience, or education do not match at least 80% of the job requirements, assign an overall_score between **10 and 39**.
3. Only assign an overall_score above **60** if the candidate meets or exceeds **all** job requirements and provides a complete profile (no missing or N/A fields).
4. Assign an overall_score between **40 and 59** only if the candidate matches most requirements but is missing some minor elements.
5. Be extremely strict and conservative in scoring. If in doubt, lower the score. Do not give a high score unless the candidate perfectly fits the role and provides all relevant details.
6. Respond **only** with a JSON object in this format:

{{
    "overall_score": <float>
}}
"""

@router.post("/user_form")
async def evaluate_candidate(candidate: CandidateCreate,  db: Session = Depends(get_db)):
    # Get job post data from database
    job = db.query(SavedJobPost).filter(SavedJobPost.id == candidate.job_post_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job post not found")

    # Combine candidate data (user) + job data (DB)
    prompt_data = {
        
        "education": candidate.highest_education,
        "institution": candidate.institution,
        "graduation_year": candidate.graduation_year,
        "cgpa": candidate.cgpa,
        "experience_years": candidate.experience_years,
        "previous_company": candidate.previous_company,
        "position": candidate.positions,
        "skills": candidate.skills,
        "projects_description": candidate.projects_description,
        "project_techstack": candidate.project_techstack,
        "responsibility": candidate.responsibilities,
        "strength": candidate.strength,
        "weakness": candidate.weakness,

        # From SavedJobPost
    
        "experience_level": job.experience_level,
        "job_description": job.description,
        "requirements": ", ".join(job.requirements or []),
        "job_responsibilities": ", ".join(job.responsibilities or []),
    }

    # Fill the prompt
    filled_prompt = prompt_template.format(**prompt_data)
    

    # Call your LLM (Granite, GPT, etc.)
    llm_result = get_llm_score(filled_prompt)
    shortlisted_entry = ShortlistedScore(
        job_id=candidate.job_post_id,
        candidate_id=candidate.id,
        score=llm_result['score'],
        name=candidate.name,
        email=candidate.email,
        phone=candidate.phone

    )
    db.add(shortlisted_entry)
    db.commit()
    

    return {
        "overall_score": llm_result["score"],
    } # Should return { "overall_score": float }

