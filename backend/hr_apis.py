from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic_models import CompanyResponse,SavedJobPostOut,JobApplicationResponse,TotalApplicationsResponse,JobRecommendationResponse,QAScoringResponse,FinalShortlistedCandidateResponse,FinalStatusResponse,FinalStatusRequest,ShortlistedScoreResponse,RecommendationWithCandidateResponse
from databaseOperation import db_ops
from models import Candidate,SavedJobPost,ShortlistedScore,QAScoring,Company,Recommendation,FinalShortlistedCandidate,Finalstatus
from typing import List
from sqlalchemy import func
from sqlalchemy import and_

router = APIRouter()

@router.get("/company/{company_id}", response_model=CompanyResponse)
def get_company_by_id(company_id: int):
    db =db_ops.get_db_session()
    company = db.query(Company).filter(Company.id == company_id).first()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company

@router.get("/job-posts/by-company/{company_id}", response_model=List[SavedJobPostOut])
def get_job_posts_by_company(company_id: str):
    db=db_ops.get_db_session()
    job_posts = db.query(SavedJobPost).filter(SavedJobPost.company_id == company_id).all()
    if not job_posts:
        raise HTTPException(status_code=404, detail="No job posts found for this company.")
    return job_posts


@router.get("/company/{company_id}/job-applications", response_model=List[JobApplicationResponse])
async def get_job_applications(company_id: str):
    """
    Fetch total applications per job for a company using SavedJobPost and ShortlistedScore.
    Returns job ID, job title, and number of candidates who applied.
    """
    db=db_ops.get_db_session()
    # Step 1: Find all saved job posts for the company
    jobs = db.query(SavedJobPost.id, SavedJobPost.title).filter(SavedJobPost.company_id == company_id).all()
    
    if not jobs:
        raise HTTPException(status_code=404, detail="No jobs found for this company")

    # Step 2: Count applications for each job from ShortlistedScore
    job_ids = [job.id for job in jobs]
    application_counts = (
        db.query(
            ShortlistedScore.job_id,
            func.count(ShortlistedScore.id).label("candidate_count")
        )
        .filter(ShortlistedScore.job_id.in_(job_ids))
        .group_by(ShortlistedScore.job_id)
        .all()
    )

    # Step 3: Prepare response, including jobs with zero applications
    job_applications = []
    application_dict = {app.job_id: app.candidate_count for app in application_counts}
    
    for job in jobs:
        job_applications.append(
            JobApplicationResponse(
                job_id=job.id,
                job_title=job.title,
                candidate_count=application_dict.get(job.id, 0)  # Default to 0 if no applications
            )
        )

    return job_applications

@router.get("/company/{company_id}/total-applications", response_model=TotalApplicationsResponse)
async def get_total_applications(company_id: str):
    """
    Fetch the total number of applications across all jobs for a company.
    Uses SavedJobPost and ShortlistedScore tables.
    """
    db=db_ops.get_db_session()
    # Step 1: Find all saved job posts for the company
    job_ids = db.query(SavedJobPost.id).filter(SavedJobPost.company_id == company_id).all()
    
    if not job_ids:
        return TotalApplicationsResponse(total_applications=0)

    # Step 2: Count total applications for these jobs
    job_ids = [job.id for job in job_ids]
    total_count = (
        db.query(func.count(ShortlistedScore.id))
        .filter(ShortlistedScore.job_id.in_(job_ids))
        .scalar() or 0
    )

    return TotalApplicationsResponse(total_applications=total_count)


@router.get("/company/{company_id}/job-recommendations", response_model=List[JobRecommendationResponse])
async def get_job_recommendations(company_id: str):
    """
    Fetch all job recommendations for a company, including job details and candidate information.
    Returns job ID, candidate ID, candidate name, candidate email, job title, hire decision, and comment.
    Handles nullable fields: candidate_name and comment may be null.
    """
    db=db_ops.get_db_session()
    # Step 1: Find all saved job posts for the company
    jobs = db.query(SavedJobPost.id, SavedJobPost.title).filter(SavedJobPost.company_id == company_id).all()
    
    if not jobs:
        return []

    job_ids = [job.id for job in jobs]
    job_title_map = {job.id: job.title for job in jobs}

    # Step 2: Join Recommendation with Candidate to get recommendations and candidate details
    recommendations = (
        db.query(
            Recommendation.job_id,
            Recommendation.candidate_id,
            Recommendation.hire_decision,
            Recommendation.comment,
            Candidate.name.label("candidate_name"),
            Candidate.email.label("candidate_email")
        )
        .join(Candidate, Recommendation.candidate_id == Candidate.id)
        .filter(Recommendation.job_id.in_(job_ids))
        .all()
    )

    # Step 3: Prepare response with null handling
    result = [
        JobRecommendationResponse(
            job_id=rec.job_id,
            candidate_id=rec.candidate_id,
            candidate_name=rec.candidate_name,  # May be None
            candidate_email=rec.candidate_email,  # Non-null
            job_title=job_title_map.get(rec.job_id, "Unknown"),  # Non-null due to schema
            hire_decision=rec.hire_decision,  # Non-null with default
            comment=rec.comment  # May be None
        )
        for rec in recommendations
    ]

    return result


@router.get("/company/{saved_job_id}/qa-scoring", response_model=List[QAScoringResponse])
async def get_qa_scoring(saved_job_id:int):
    """
    Fetch all QA scoring data for a company, including candidate and job details.
    Returns candidate ID, name, email, job ID, job title, and all QA scoring fields.
    """
    db=db_ops.get_db_session()
    # Step 1: Find all saved job posts for the company
    jobs = db.query(SavedJobPost.id, SavedJobPost.title).filter(SavedJobPost.id == saved_job_id).all()
    
    if not jobs:
        return []

    job_ids = [job.id for job in jobs]
    job_title_map = {job.id: job.title for job in jobs}

    # Step 2: Join QAScoring with Candidate to get scoring and candidate details
    scoring_data = (
        db.query(
            QAScoring.candidate_id,
            QAScoring.job_id,
            QAScoring.question,
            QAScoring.answer,
            QAScoring.correctness_score,
            QAScoring.efficiency_score,
            QAScoring.readability_score,
            QAScoring.edge_case_handling_score,
            QAScoring.overall_score,
            QAScoring.strengths,
            QAScoring.weaknesses,
            Candidate.name.label("candidate_name"),
            Candidate.email.label("candidate_email")
        )
        .join(Candidate, QAScoring.candidate_id == Candidate.id)
        .filter(QAScoring.job_id.in_(job_ids))
        .all()
    )

    # Step 3: Prepare response
    result = [
        QAScoringResponse(
            candidate_id=data.candidate_id,
            candidate_name=data.candidate_name,
            candidate_email=data.candidate_email,
            job_id=data.job_id,
            job_title=job_title_map.get(data.job_id, "Unknown"),
            question=data.question,
            answer=data.answer,
            correctness_score=data.correctness_score,
            efficiency_score=data.efficiency_score,
            readability_score=data.readability_score,
            edge_case_handling_score=data.edge_case_handling_score,
            overall_score=data.overall_score,
            strengths=data.strengths,
            weaknesses=data.weaknesses
        )
        for data in scoring_data
    ]

    return result




@router.get("/job/{job_id}/final-shortlisted-candidates", response_model=List[FinalShortlistedCandidateResponse])
async def get_final_shortlisted_candidates(job_id: int):
    """
    Fetch all final shortlisted candidates for a specific job,
    including all details required by the response model.
    """
    db = db_ops.get_db_session()
    # Step 1: Verify job exists and get job title
    job = db.query(SavedJobPost.id, SavedJobPost.title).filter(SavedJobPost.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Step 2: Fetch all columns from FinalShortlistedCandidate and job title from SavedJobPost
    candidates = (
        db.query(
            FinalShortlistedCandidate.candidate_id,
            FinalShortlistedCandidate.name.label("candidate_name"),
            FinalShortlistedCandidate.email.label("candidate_email"),
            FinalShortlistedCandidate.job_id,
            FinalShortlistedCandidate.score,
            FinalShortlistedCandidate.sent_email,
            FinalShortlistedCandidate.interview_date,
            FinalShortlistedCandidate.interview_given,
            SavedJobPost.title.label("job_title")
        )
        .join(SavedJobPost, FinalShortlistedCandidate.job_id == SavedJobPost.id)
        .filter(FinalShortlistedCandidate.job_id == job_id)
        .all()
    )

    result = [
        FinalShortlistedCandidateResponse(
            candidate_id=candidate.candidate_id,
            candidate_name=candidate.candidate_name,
            candidate_email=candidate.candidate_email,
            job_id=candidate.job_id,
            job_title=candidate.job_title,
            score=candidate.score,
            sent_email=candidate.sent_email,
            interview_date=candidate.interview_date,
            interview_given=candidate.interview_given
        )
        for candidate in candidates
    ]

    return result


@router.post("/final-status", response_model=FinalStatusResponse)
async def save_final_status(request: FinalStatusRequest):
    """
    Save or update the final status (accept/reject/pending) for a candidate for a specific job.
    Status: True (accept), False (reject), null (unpublished/pending).
    Creates a new record or updates an existing one based on candidate_id and job_id.
    """
    db=db_ops.get_db_session()
    # Validate job_id exists in SavedJobPost
    job = db.query(SavedJobPost).filter(SavedJobPost.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check if a record already exists for candidate_id and job_id
    existing_status = db.query(Finalstatus).filter(
        and_(
            Finalstatus.candidate_id == request.candidate_id,
            Finalstatus.job_id == request.job_id
        )
    ).first()

    # Determine human-readable status text
    status_text = "Pending" if request.status is None else "Accepted" if request.status else "Rejected"

    if existing_status:
        # Update existing record
        existing_status.status = request.status
        existing_status.comment = request.comment
        db.commit()
        db.refresh(existing_status)
        return FinalStatusResponse(
            id=existing_status.id,
            candidate_id=existing_status.candidate_id,
            job_id=existing_status.job_id,
            status=existing_status.status,
            status_text=status_text,
            comment=existing_status.comment
        )
    else:
        # Create new record
        new_status = Finalstatus(
            candidate_id=request.candidate_id,
            job_id=request.job_id,
            status=request.status,
            comment=request.comment
        )
        db.add(new_status)
        db.commit()
        db.refresh(new_status)
        return FinalStatusResponse(
            id=new_status.id,
            candidate_id=new_status.candidate_id,
            job_id=new_status.job_id,
            status=new_status.status,
            status_text=status_text,
            comment=new_status.comment
        )
    
@router.put("/finalstatus/reject_remaining/{job_id}")
def reject_remaining_candidates(job_id: int):
    db=db_ops.get_db_session()
    # Find all who are not yet accepted
    remaining = db.query(Finalstatus).filter(
        Finalstatus.job_id == job_id,
        Finalstatus.status != True  # Reject if not already accepted
    ).all()

    if not remaining:
        raise HTTPException(status_code=404, detail="No remaining candidates to reject.")

    for candidate in remaining:
        candidate.status = False
        candidate.comment = "Rejected by HR"

    db.commit()

    return {"message": f"{len(remaining)} candidates rejected for job_id {job_id}"}

@router.get("/shortlisted-scores/{job_id}", response_model=List[ShortlistedScoreResponse])
def get_shortlisted_scores(job_id: int):
    db=db_ops.get_db_session()
    scores = db.query(ShortlistedScore).filter(ShortlistedScore.job_id == job_id).all()
    if not scores:
        raise HTTPException(status_code=404, detail="No shortlisted scores found for this job id.")
    return scores


@router.get("/job-recommendations", response_model=List[RecommendationWithCandidateResponse])
def get_job_recommendations(job_id: int):
    """
    Retrieve candidate name, phone, email, hire_decision, and comment for all recommendations of a job.
    """
    db=db_ops.get_db_session()
    results = (
        db.query(
            Candidate.name.label("candidate_name"),
            Candidate.phone.label("candidate_phone"),
            Candidate.email.label("candidate_email"),
            Recommendation.hire_decision,
            Recommendation.comment
        )
        .join(Recommendation, Candidate.id == Recommendation.candidate_id)
        .filter(Recommendation.job_id == job_id)
        .all()
    )

    # If no recommendations found, return empty list or raise HTTPException
    if not results:
        raise HTTPException(status_code=404, detail="No recommendations found for this job.")

    # Convert SQLAlchemy Row objects to dict for Pydantic model
    return [RecommendationWithCandidateResponse(
                candidate_name=row.candidate_name,
                candidate_phone=row.candidate_phone,
                candidate_email=row.candidate_email,
                hire_decision=row.hire_decision,
                comment=row.comment
            ) for row in results]