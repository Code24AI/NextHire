
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic_models import CandidateOut,CandidateJobStats,AppliedJobInfo,QAScoreResponse,AppliedStatusResponse,CodingChallengeResponse,CandidateUpdate,FinalShortlistedCandidateResponse,InterviewStatusUpdate
from databaseOperation import db_ops
from models import Candidate,SavedJobPost,ShortlistedScore,QAScoring,Finalstatus,FinalShortlistedCandidate
from typing import List

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


router = APIRouter()


@router.get("/candidates", response_model=List[CandidateOut])
def get_all_candidates():
    db=db_ops.get_db_session()
    return db.query(Candidate).all()

@router.get("/candidates/{candidate_id}", response_model=CandidateOut)
def get_candidate_by_id(candidate_id: int):
    db=db_ops.get_db_session()
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate






@router.get("/candidate/{candidate_id}/applied-jobs", response_model=CandidateJobStats)
def get_candidate_applied_jobs(candidate_id: int):
    # Get job_ids from ShortlistedScore where candidate applied
    db=db_ops.get_db_session()
    shortlisted_entries = db.query(ShortlistedScore).filter(ShortlistedScore.candidate_id == candidate_id).all()

    if not shortlisted_entries:
        raise HTTPException(status_code=404, detail="No job applications found for this candidate.")

    job_ids = [entry.job_id for entry in shortlisted_entries]

    # Get job details from SavedJobPost using those job_ids
    job_posts = (
        db.query(SavedJobPost)
        .filter(SavedJobPost.id.in_(job_ids))
        .all()
    )

    applied_jobs = [
        AppliedJobInfo(job_id=job.id, title=job.title)
        for job in job_posts
    ]

    return CandidateJobStats(
        candidate_id=candidate_id,
        total_applied_jobs=len(applied_jobs),
        applied_jobs=applied_jobs
    )
@router.get("/qa-score", response_model=QAScoreResponse)
def get_qa_score(candidate_id: int, job_id: int):
    db=db_ops.get_db_session()
    score = (
        db.query(QAScoring)
        .filter(QAScoring.candidate_id == candidate_id, QAScoring.job_id == job_id)
        .first()
    )

    if not score:
        raise HTTPException(status_code=404, detail="QA score not found for this user and job.")

    return QAScoreResponse(
        correctness_score=score.correctness_score,
        efficiency_score=score.efficiency_score,
        readability_score=score.readability_score,
        edge_case_handling_score=score.edge_case_handling_score,
        overall_score=score.overall_score,
        strengths=score.strengths,
        weaknesses=score.weaknesses
    )

@router.get("/has-applied", response_model=AppliedStatusResponse)
def has_candidate_applied(candidate_id: int, job_id: int):
    db=db_ops.get_db_session()
    applied = (
        db.query(ShortlistedScore)
        .filter(ShortlistedScore.candidate_id == candidate_id, ShortlistedScore.job_id == job_id)
        .first()
    )
    
    return {"applied": bool(applied)}

@router.get("/coding-challenge", response_model=CodingChallengeResponse)
def get_coding_challenge( job_id: int):
    db=db_ops.get_db_session()
    challenge = (
        db.query(SavedJobPost)
        .filter( SavedJobPost.id == job_id)
        .first()
    )

    if not challenge:
        raise HTTPException(status_code=404, detail="No coding challenge found for this candidate and job.")

    return {"coding_challenge": challenge.coding_challenge}




@router.get("/finalstatus/")
def get_finalstatus(job_id: int, candidate_id: int):
    db=db_ops.get_db_session()
    finalstatus = db.query(Finalstatus).filter(
        Finalstatus.job_id == job_id,
        Finalstatus.candidate_id == candidate_id
    ).first()

    if not finalstatus:
        raise HTTPException(status_code=404, detail="Final status not found")

    return {
        "id": finalstatus.id,
        "candidate_id": finalstatus.candidate_id,
        "job_id": finalstatus.job_id,
        "status": finalstatus.status,
        "comment": finalstatus.comment,
    }


@router.patch("/user_APIs/candidates/{candidate_id}", response_model=CandidateUpdate)
async def update_candidate(
    candidate_id: int,
    candidate_update: CandidateUpdate
):
    db=db_ops.get_db_session()
 

    # Get the candidate from the database
    db_candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not db_candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    # Update fields that are provided
    update_data = candidate_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_candidate, key, value)

    try:
        db.commit()
        db.refresh(db_candidate)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")

    return db_candidate


# --- Pydantic Response Model ---
class FinalShortlistedCandidateResponse(BaseModel):
    candidate_id: int
    name: Optional[str]
    email: Optional[str]
    job_id: int
    score: float
    interview_date: Optional[datetime]
    interview_given: Optional[bool]
    sent_email: Optional[bool]

    class Config:
        orm_mode = True

# --- Eligibility Check Endpoint ---
@router.get("/interview-eligibility", response_model=FinalShortlistedCandidateResponse)
def check_interview_eligibility(job_id: int, candidate_id: int):
    db=db_ops.get_db_session()
    record = db.query(FinalShortlistedCandidate).filter(
        FinalShortlistedCandidate.job_id == job_id,
        FinalShortlistedCandidate.candidate_id == candidate_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="No eligibility found")
    return record

# --- Update Interview Status Endpoint ---
@router.post("/update-interview-status")
def update_interview_status(update: InterviewStatusUpdate):
    db=db_ops.get_db_session()
    record = db.query(FinalShortlistedCandidate).filter(
        FinalShortlistedCandidate.job_id == update.job_id,
        FinalShortlistedCandidate.candidate_id == update.candidate_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Candidate/job not found")
    record.interview_given = update.interview_given
    db.commit()
    return {"success": True, "message": "Interview status updated."}

