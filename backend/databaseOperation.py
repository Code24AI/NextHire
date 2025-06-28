"""
Database operations for HR Job Post Management System
"""
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import desc, and_
from datetime import datetime
import json

from models import Session, JobPost, Message, SavedJobPost,QAScoring
from database import SessionLocal


class DatabaseOperations:
    """
    Class to handle all database operations
    """
    
    def __init__(self):
        self.db = None
    
    def get_db_session(self) -> DBSession:
        """Get database session"""
        if not self.db:
            self.db = SessionLocal()
        return self.db
    
    def close_db_session(self):
        """Close database session"""
        if self.db:
            self.db.close()
            self.db = None
    
    # Session Operations
    def create_session(self, session_id: str,company_id: str) -> Session:
        """Create a new session"""
        db = self.get_db_session()
        try:
            db_session = Session(session_id=session_id,company_id=company_id)
            db.add(db_session)
            db.commit()
            db.refresh(db_session)
            return db_session
        except Exception as e:
            db.rollback()
            raise e
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        db = self.get_db_session()
        return db.query(Session).filter(Session.session_id == session_id).first()
    
    def update_session(self, session_id: str, **kwargs) -> Session:
        """Update session data"""
        db = self.get_db_session()
        try:
            session = db.query(Session).filter(Session.session_id == session_id).first()
            if session:
                for key, value in kwargs.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
                db.commit()
                db.refresh(session)
            return session
        except Exception as e:
            db.rollback()
            raise e
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session and related data"""
        db = self.get_db_session()
        try:
            session = db.query(Session).filter(Session.session_id == session_id).first()
            if session:
                # Delete related messages and job posts
                db.query(Message).filter(Message.session_id == session_id).delete()
                db.query(JobPost).filter(JobPost.session_id == session_id).delete()
                db.delete(session)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            raise e
    
    def get_all_active_sessions(self) -> List[Session]:
        """Get all active sessions"""
        db = self.get_db_session()
        return db.query(Session).filter(Session.is_active == True).all()
    
    # Job Post Operations
    def create_job_post(self, session_id: str, job_post_data: Dict, company_id: Optional[str] = None) -> JobPost:
        """Create a new job post"""
        db = self.get_db_session()

        job_data = job_post_data.copy()
        job_data.pop('company_id', None) 
        try:
            db_job_post = JobPost(
                session_id=session_id,
                title=job_post_data.get('title', ''),
                company=job_post_data.get('company', 'Our Company'),
                location=job_post_data.get('location', 'Remote'),
                job_type=job_post_data.get('job_type', 'Full-time'),
                experience_level=job_post_data.get('experience_level', 'Mid'),
                description=job_post_data.get('description', ''),
                responsibilities=job_post_data.get('responsibilities', []),
                requirements=job_post_data.get('requirements', []),
                benefits=job_post_data.get('benefits', []),
                salary_range=job_post_data.get('salary_range', 'Competitive'),
                deadline=job_post_data.get('deadline', 'gh'),
                company_id=company_id or job_post_data.get('company_id')
                #company_id=company_id
            )
            db.add(db_job_post)
            db.commit()
            db.refresh(db_job_post)
            return db_job_post
        except Exception as e:
            db.rollback()
            raise e
    
    def get_latest_job_post(self, session_id: str) -> Optional[JobPost]:
        """Get the latest job post for a session"""
        db = self.get_db_session()
        return db.query(JobPost).filter(
            and_(JobPost.session_id == session_id, JobPost.is_active == True)
        ).order_by(desc(JobPost.created_at)).first()
    
    def update_job_post(self, session_id: str, job_post_data: Dict, company_id: Optional[str] = None) -> JobPost:
        """Update existing job post"""
        db = self.get_db_session()
        try:
            # Deactivate old job post
            old_job_post = self.get_latest_job_post(session_id)
            if old_job_post:
                old_job_post.is_active = False
                db.commit()
            job_data = job_post_data.copy()
            job_data.pop('company_id', None) 
            # Create new version
            new_job_post = JobPost(
                session_id=session_id,
                title=job_post_data.get('title', ''),
                company=job_post_data.get('company', 'Our Company'),
                location=job_post_data.get('location', 'Remote'),
                job_type=job_post_data.get('job_type', 'Full-time'),
                experience_level=job_post_data.get('experience_level', 'Mid'),
                description=job_post_data.get('description', ''),
                responsibilities=job_post_data.get('responsibilities', []),
                requirements=job_post_data.get('requirements', []),
                benefits=job_post_data.get('benefits', []),
                salary_range=job_post_data.get('salary_range', 'Competitive'),
                version=old_job_post.version + 1 if old_job_post else 1,
                deadline=job_post_data.get('deadline', 'gh'),
                #company_id = job_post_data.get('company_id', 'gh'),
                #company_id=company_id
                company_id=company_id or job_post_data.get('company_id') or (old_job_post.company_id if old_job_post else None)
            )
            db.add(new_job_post)
            db.commit()
            db.refresh(new_job_post)
            return new_job_post
        except Exception as e:
            db.rollback()
            raise e
    
    def get_job_post_history(self, session_id: str) -> List[JobPost]:
        """Get all job post versions for a session"""
        db = self.get_db_session()
        return db.query(JobPost).filter(JobPost.session_id == session_id).order_by(desc(JobPost.version)).all()
    
    # Message Operations
    def add_message(self, session_id: str, message_type: str, content: str) -> Message:
        """Add a message to the conversation"""
        db = self.get_db_session()
        try:
            message = Message(
                session_id=session_id,
                message_type=message_type,
                content=content
            )
            db.add(message)
            db.commit()
            db.refresh(message)
            return message
        except Exception as e:
            db.rollback()
            raise e
    
    def get_conversation_history(self, session_id: str) -> List[Message]:
        """Get conversation history for a session"""
        db = self.get_db_session()
        return db.query(Message).filter(Message.session_id == session_id).order_by(Message.timestamp).all()
    
    def clear_conversation_history(self, session_id: str) -> bool:
        """Clear conversation history for a session"""
        db = self.get_db_session()
        try:
            db.query(Message).filter(Message.session_id == session_id).delete()
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e
    
    # Saved Job Post Operations
    def save_job_post(self, session_id: str, job_post: JobPost,company_id: Optional[str] = None, total_iterations: int = 0) -> SavedJobPost:
        """Save a job post as final"""
        db = self.get_db_session()
        
        try:
            saved_job_post = SavedJobPost(
                session_id=session_id,
                job_post_id=job_post.id,
                title=job_post.title,
                company=job_post.company,
                location=job_post.location,
                job_type=job_post.job_type,
                experience_level=job_post.experience_level,
                description=job_post.description,
                responsibilities=job_post.responsibilities,
                requirements=job_post.requirements,
                benefits=job_post.benefits,
                salary_range=job_post.salary_range,
                total_iterations=total_iterations,
                deadline=job_post.deadline,
                #company_id=job_post.company_id,
                #company_id=company_id
                company_id=company_id or job_post.get('company_id')
            )
            
            # Mark original job post as saved
            job_post.is_saved = True
            
            db.add(saved_job_post)
            db.commit()
            db.refresh(saved_job_post)
            return saved_job_post
        except Exception as e:
            db.rollback()
            raise e
    
    def get_saved_job_posts(self, session_id: str = None) -> List[SavedJobPost]:
        """Get saved job posts, optionally filtered by session"""
        db = self.get_db_session()
        query = db.query(SavedJobPost)
        if session_id:
            query = query.filter(SavedJobPost.session_id == session_id)
        return query.order_by(desc(SavedJobPost.saved_at)).all()
    
    def get_saved_job_post_by_id(self, saved_job_post_id: int) -> Optional[SavedJobPost]:
        """Get saved job post by ID"""
        db = self.get_db_session()
        return db.query(SavedJobPost).filter(SavedJobPost.id == saved_job_post_id).first()
    
    def get_all_saved_job_posts(self) -> Optional[SavedJobPost]:
        db = self.get_db_session()
      
        return db.query(SavedJobPost).all()
    
    # Analytics and Reporting
    def get_session_stats(self) -> Dict:
        """Get session statistics"""
        db = self.get_db_session()
        
        total_sessions = db.query(Session).count()
        active_sessions = db.query(Session).filter(Session.is_active == True).count()
        total_job_posts = db.query(JobPost).count()
        saved_job_posts = db.query(SavedJobPost).count()
        total_messages = db.query(Message).count()
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_job_posts": total_job_posts,
            "saved_job_posts": saved_job_posts,
            "total_messages": total_messages,
            "completion_rate": round((saved_job_posts / total_sessions * 100) if total_sessions > 0 else 0, 2)
        }
    
    def get_popular_job_types(self) -> List[Tuple[str, int]]:
        """Get most popular job types"""
        db = self.get_db_session()
        from sqlalchemy import func
        
        result = db.query(
            SavedJobPost.job_type,
            func.count(SavedJobPost.job_type).label('count')
        ).group_by(SavedJobPost.job_type).order_by(desc('count')).limit(10).all()
        
        return [(row.job_type, row.count) for row in result]
    
    def get_average_iterations(self) -> float:
        """Get average number of iterations per job post"""
        db = self.get_db_session()
        from sqlalchemy import func
        
        result = db.query(func.avg(SavedJobPost.total_iterations)).scalar()
        return round(result, 2) if result else 0.0
    
    # Utility Methods
    def job_post_to_dict(self, job_post: JobPost) -> Dict:
        """Convert JobPost model to dictionary"""
        return {
            "id": job_post.id,
            "title": job_post.title,
            "company": job_post.company,
            "location": job_post.location,
            "job_type": job_post.job_type,
            "experience_level": job_post.experience_level,
            "description": job_post.description,
            "responsibilities": job_post.responsibilities,
            "requirements": job_post.requirements,
            "benefits": job_post.benefits,
            "deadline": job_post.deadline.isoformat() if job_post.deadline else None,
            "salary_range": job_post.salary_range,
            "created_at": job_post.created_at.isoformat() if job_post.created_at else None,
            "updated_at": job_post.updated_at.isoformat() if job_post.updated_at else None,
            "version": job_post.version,
            "is_saved": job_post.is_saved,
            "company_id":job_post.company_id
        }
    
    def session_to_dict(self, session: Session) -> Dict:
        """Convert Session model to dictionary"""
        return {
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "is_active": session.is_active,
            "current_action": session.current_action,
            "iteration_count": session.iteration_count,
            "awaiting_user_input": session.awaiting_user_input
        }
    
    
    
    def getting_saved_job_id(self, id: int):
        """get the perticular job for creating the challenge"""
        db = self.get_db_session()
        return db.query(SavedJobPost).filter(
            and_(SavedJobPost.id == id)).first()
        
    def update_coding_challenge(self, job_id: int, challenge: str) -> bool:
        """Update the coding_challenge column for a specific job."""
        db = self.get_db_session()
        job = db.query(SavedJobPost).filter(SavedJobPost.id == job_id).first()
        if not job:
           return False

        job.coding_challenge = challenge
        db.commit()
        db.refresh(job)
        return True
    def get_job_posts_by_company(self, company_id: str) -> List[SavedJobPost]:
        """Get all saved job posts for a specific company"""
        db = self.get_db_session()
        return db.query(SavedJobPost).filter(
        SavedJobPost.company_id == company_id
        ).order_by(desc(SavedJobPost.saved_at)).all()

    def insert_scores(
        self,
        challenge: str,
        answer: str,
        job_id: int,
        candidate_id: int,
        evaluation: dict
        ) -> None:
        """
    Inserts or updates the scoring result for a given candidate and job.
    
    Args:
        db (Session): SQLAlchemy database session
        challenge (str): Coding challenge description
        answer (str): Submitted answer code
        job_id (int): Job ID
        candidate_id (int): Candidate ID
        evaluation (dict): Evaluation scores and feedback
        """
        db=self.get_db_session()
        existing_entry = db.query(QAScoring).filter_by(
        job_id=job_id,
        candidate_id=candidate_id).first()

        if existing_entry:
        # Update existing record
          existing_entry.question = challenge
          existing_entry.answer = answer
          existing_entry.correctness_score = evaluation["correctness_score"]
          existing_entry.efficiency_score = evaluation["efficiency_score"]
          existing_entry.readability_score = evaluation["readability_score"]
          existing_entry.edge_case_handling_score = evaluation["edge_case_handling_score"]
          existing_entry.overall_score = evaluation["overall_score"]
          existing_entry.strengths = evaluation["strengths"]
          existing_entry.weaknesses = evaluation["weaknesses"]
        else:
        # Create new record
          new_entry = QAScoring(
            question=challenge,
            answer=answer,
            job_id=job_id,
            candidate_id=candidate_id,
            correctness_score=evaluation["correctness_score"],
            efficiency_score=evaluation["efficiency_score"],
            readability_score=evaluation["readability_score"],
            edge_case_handling_score=evaluation["edge_case_handling_score"],
            overall_score=evaluation["overall_score"],
            strengths=evaluation["strengths"],
            weaknesses=evaluation["weaknesses"]
            )
          db.add(new_entry)

        db.commit()

# Global instance
db_ops = DatabaseOperations()