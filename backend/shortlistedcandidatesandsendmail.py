from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from datetime import datetime, timedelta
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from databaseOperation import db_ops
from database import get_db
from models import ShortlistedScore, FinalShortlistedCandidate, SavedJobPost
from chat_llm_granite import chat

# Load .env
load_dotenv()
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")



#scheduler = BackgroundScheduler()

# Utility: Send Email
def send_email(to_email: str, job_id: int, email_body: str, title: str):
    msg = EmailMessage()
    msg["Subject"] = f"You've been shortlisted for {title}"
    msg["From"] = "info@code24.com.au"
    msg["To"] = to_email
    msg.set_content(email_body)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")

# Utility: Shortlist Candidates
def shortlist_candidates_for_job(db: Session, job_id: int,interview_date):
    q = db.query(ShortlistedScore).filter(ShortlistedScore.job_id == job_id).order_by(ShortlistedScore.score.desc())
    high_scores = q.filter(ShortlistedScore.score >= 80).all()
    selected = high_scores if len(high_scores) >= 15 else q.limit(50).all()

    for s in selected:
        db.add(FinalShortlistedCandidate(job_id=job_id, candidate_id=s.candidate_id, score=s.score,email=s.email,phone=s.phone,name=s.name,sent_email=True,interview_date=interview_date))

    db.commit()
    return selected

# Utility: Get Expired Jobs
def get_expired_jobs(db: Session):
    now = datetime.now(pytz.timezone("Asia/Dhaka")).replace(microsecond=0)+ timedelta(days=6)
    return db.query(SavedJobPost).filter(SavedJobPost.deadline < now, SavedJobPost.is_processed == False).all()

# Utility: Generate Email
def genarate_email(job):
    deadline_date = datetime.combine(job.deadline.date(), datetime.min.time())
    interview_date = deadline_date + timedelta(days=4)
    interview_date_str = interview_date.strftime("%B %d, %Y")
    interview_time = "11:59 PM (GMT+6)"

    prompt = f"""
You are an HR assistant at {job.company}.
Write a professional and friendly email without the subject to all shortlisted candidates for the {job.title} role.

Inform them:
- They are shortlisted.
- They have coding interview due to the date .they have to finished interviwe before due date .
- Their interview have to be done before  {interview_date_str} at {interview_time}.they can give interview before the time end.
- The interview will be on real world coding challenge related to their field.
- Share the interview platform link: www.nexthire.com 
- To conduct an interview, log in to your Nexthire account, click the "Interview" button in the top right corner, enter the job ID, and then click "Interview" to start the interview.

Keep the tone warm and formal. Do not use candidate names, as the email is going to multiple people.Make in short and crisp and donot add the email subject just email body  and star with dear Candidates not shortlisted candidates.
no need to write Hr`s name .
"""
    email_body = chat.invoke(prompt).content.strip()
    return email_body

# Main Processor
def process_expired_jobs(db: Session):
    jobs_to_process = get_expired_jobs(db)
    for job in jobs_to_process:
        email = genarate_email(job)
        deadline_date = datetime.combine(job.deadline.date(), datetime.min.time())
        interview_date = deadline_date + timedelta(days=4)
        interview_date_str = interview_date.strftime("%B %d, %Y")
        interview_time = "11:59 PM (GMT+6)"
        candidates = shortlist_candidates_for_job(db, job.id,interview_date)

        for candidate in candidates:
            send_email(candidate.email, job.id, email, job.title)

        job.is_processed = True
        db.add(job)

    db.commit()
    return {"processed_jobs": [job.id for job in jobs_to_process]}

# Scheduled Task
def shortlistedcandidatesmail():
    db = db_ops.get_db_session()
    try:
        process_expired_jobs(db)
    finally:
        db.close()



