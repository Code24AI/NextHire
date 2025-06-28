import os
import json
import uuid
from typing import Dict, List, Optional, TypedDict, Annotated
from datetime import datetime

# FastAPI imports
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# LangChain imports
from langchain_ibm import ChatWatsonx
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

# Database imports
from models import Session as DBSession, JobPost, Message, SavedJobPost
from databaseOperation import db_ops
from create_challenge import genarate_question
from pydantic_models import SavedJobPostOut
# Load environment variables from .env file
load_dotenv()

# Configuration
WATSONX_URL = "https://au-syd.ml.cloud.ibm.com"
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_API_KEY = os.getenv("WATSONX_API_KEY")

# WatsonX parameters
parameters = {
    "decoding_method": "greedy",
    "max_new_tokens": 1000,
    "temperature": 0.7,
    "top_p": 0.9,
    "repetition_penalty": 1.1
}

# Initialize ChatWatsonx
llm = ChatWatsonx(
    model_id="ibm/granite-3-8b-instruct",
    url=WATSONX_URL,
    project_id=WATSONX_PROJECT_ID,
    api_key=WATSONX_API_KEY,
    params=parameters
)

# FastAPI Models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    company_id: Optional[str] = None  # Added company_id field

class ChatResponse(BaseModel):
    response: str
    session_id: str
    status: str
    job_post: Optional[Dict] = None
    awaiting_input: bool = False

class JobPostState(TypedDict):
    """State structure for the job post workflow"""
    messages: Annotated[List, add_messages]
    job_post: Optional[Dict]
    user_request: str
    current_action: str
    iteration_count: int
    awaiting_user_input: bool
    session_id: str
    company_id: Optional[str]  # Added company_id to state

class JobPostWorkflow:
    """HR Job Post Management System using LangGraph with Database"""
    
    def __init__(self):
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(JobPostState)
        
        # Add nodes
        workflow.add_node("generate_job_post", self.generate_job_post)
        workflow.add_node("present_job_post", self.present_job_post)
        workflow.add_node("update_job_post", self.update_job_post)
        workflow.add_node("save_job_post", self.save_job_post)
        
        # Define edges
        workflow.set_entry_point("generate_job_post")
        workflow.add_edge("generate_job_post", "present_job_post")
        workflow.add_edge("present_job_post", END)
        workflow.add_edge("update_job_post", "present_job_post")
        workflow.add_edge("save_job_post", END)
        
        return workflow
    
    def generate_job_post(self, state: JobPostState) -> JobPostState:
        """Generate initial job post based on user request"""
        print(f"🔄 Generating job post for session: {state['session_id']}, company: {state.get('company_id', 'N/A')}")
        
        # Save user message to database
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        if user_messages:
            db_ops.add_message(state["session_id"], "human", user_messages[-1].content)
        
        system_prompt = """You are an expert HR assistant. Create a comprehensive job post based on the user's request.

Return ONLY a valid JSON object with this exact structure:
{
    "title": "Job Title",
    "company": "Our Company",
    "location": "Remote/On-site",
    "job_type": "Full-time/Part-time/Contract",
    "experience_level": "Entry/Mid/Senior",
    "description": "Engaging job description paragraph",
    "responsibilities": ["responsibility 1", "responsibility 2", "responsibility 3"],
    "requirements": ["requirement 1", "requirement 2", "requirement 3"],
    "benefits": ["benefit 1", "benefit 2", "benefit 3"],
    "salary_range": "Competitive",
    "deadline": "2025-06-25T23:59:00"
}

Make it professional and comprehensive. Ensure valid JSON format."""
        
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        user_request = user_messages[-1].content if user_messages else state["user_request"]
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Create a job post for: {user_request}")
        ]
        
        try:
            response = llm.invoke(messages)
            job_post_json = self._parse_json_response(response.content)
            
            if job_post_json:
                # Save job post to database with company_id
                db_job_post = db_ops.create_job_post(
                    state["session_id"], 
                    job_post_json, 
                    company_id=state.get("company_id")
                )
                
                # Convert to dict for state
                job_post_json = db_ops.job_post_to_dict(db_job_post)
                
                state["job_post"] = job_post_json
                state["current_action"] = "generated"
                
                # Update session status
                db_ops.update_session(
                    state["session_id"],
                    current_action="generated",
                    iteration_count=0
                )
                
                print(f"✅ Job post generated and saved to database for session: {state['session_id']}, company: {state.get('company_id', 'N/A')}")
            else:
                error_msg = "❌ Failed to generate job post. Please try again with more specific details."
                state["messages"].append(AIMessage(content=error_msg))
                state["current_action"] = "error"
                db_ops.add_message(state["session_id"], "ai", error_msg)
                
        except Exception as e:
            error_msg = f"❌ Error generating job post: {str(e)}"
            state["messages"].append(AIMessage(content=error_msg))
            state["current_action"] = "error"
            db_ops.add_message(state["session_id"], "ai", error_msg)
            print(f"Error in session {state['session_id']}: {e}")
        
        return state
    
    def present_job_post(self, state: JobPostState) -> JobPostState:
        """Present the job post to user and ask for next action"""
        if state["current_action"] == "error":
            return state
        
        if not state.get("job_post"):
            error_msg = "❌ No job post available."
            state["messages"].append(AIMessage(content=error_msg))
            db_ops.add_message(state["session_id"], "ai", error_msg)
            return state
        
        formatted_post = self._format_job_post(state["job_post"])
        
        if state["current_action"] == "generated":
            message = f"✅ Job post created!\n\n{formatted_post}\n\n🤖 What would you like to do next?\n• Type 'post' to save this job post\n• Type 'update' followed by your changes\n• Or describe specific modifications you'd like"
        elif state["current_action"] == "updated":
            message = f"✅ Job post updated!\n\n{formatted_post}\n\n🤖 Would you like to make more changes or post it?\n• Type 'post' to post this job post\n• Type 'update' followed by more changes\n• Or describe additional modifications"
        else:
            message = f"📋 Current job post:\n\n{formatted_post}\n\n🤖 What would you like to do?"
        
        state["messages"].append(AIMessage(content=message))
        state["awaiting_user_input"] = True
        
        # Save AI message to database
        db_ops.add_message(state["session_id"], "ai", message)
        
        # Update session status
        db_ops.update_session(
            state["session_id"],
            awaiting_user_input=True,
            current_action=state["current_action"]
        )
        
        return state
    
    def update_job_post(self, state: JobPostState) -> JobPostState:
        """Update the job post based on user feedback"""
        print(f"🔄 Updating job post for session: {state['session_id']}, company: {state.get('company_id', 'N/A')}")
        
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        if not user_messages:
            error_msg = "❌ No update request found."
            state["messages"].append(AIMessage(content=error_msg))
            db_ops.add_message(state["session_id"], "ai", error_msg)
            return state
            
        update_request = user_messages[-1].content
        
        # Save user message to database
        db_ops.add_message(state["session_id"], "human", update_request)
        
        system_prompt = f"""You are updating an existing job post based on user feedback.

Current job post (JSON format):
{json.dumps(state["job_post"], indent=2)}

User's update request: {update_request}

Return ONLY the updated job post as a valid JSON object with the same structure:
{{
    "title": "Job Title",
    "company": "Company Name",
    "location": "Location",
    "job_type": "Job Type",
    "experience_level": "Experience Level", 
    "description": "Job description",
    "responsibilities": ["resp1", "resp2", "resp3"],
    "requirements": ["req1", "req2", "req3"],
    "benefits": ["benefit1", "benefit2", "benefit3"],
    "salary_range": "Salary Range",
    "deadline": "deadline"
}}

Apply the requested changes while keeping the rest of the job post intact. Ensure valid JSON format."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Please update the job post based on this request: {update_request}")
        ]
        
        try:
            response = llm.invoke(messages)
            updated_job_post = self._parse_json_response(response.content)
            
            if updated_job_post:
                # Update job post in database
                db_job_post = db_ops.update_job_post(
                state["session_id"], 
                updated_job_post, 
                company_id=state.get("company_id")
)
                
                # Convert to dict for state
                job_post_json = db_ops.job_post_to_dict(db_job_post)
                
                state["job_post"] = job_post_json
                state["current_action"] = "updated"
                state["iteration_count"] = state.get("iteration_count", 0) + 1
                
                # Update session status
                db_ops.update_session(
                    state["session_id"],
                    current_action="updated",
                    iteration_count=state["iteration_count"]
                )
                
                print(f"✅ Job post updated and saved to database for session: {state['session_id']}, company: {state.get('company_id', 'N/A')}")
            else:
                error_msg = "❌ Failed to update job post. Please try again."
                state["messages"].append(AIMessage(content=error_msg))
                state["current_action"] = "error"
                db_ops.add_message(state["session_id"], "ai", error_msg)
                
        except Exception as e:
            error_msg = f"❌ Error updating job post: {str(e)}"
            state["messages"].append(AIMessage(content=error_msg))
            state["current_action"] = "error"
            db_ops.add_message(state["session_id"], "ai", error_msg)
            print(f"Update error in session {state['session_id']}: {e}")
        
        return state
    
    def save_job_post(self, state: JobPostState) -> JobPostState:
        """Save the final job post"""
        print(f"💾 Saving job post for session: {state['session_id']}, company: {state.get('company_id', 'N/A')}")
        
        if not state.get("job_post"):
            error_msg = "❌ No job post to save."
            state["messages"].append(AIMessage(content=error_msg))
            db_ops.add_message(state["session_id"], "ai", error_msg)
            return state
        
        try:
            # Get the latest job post from database
            latest_job_post = db_ops.get_latest_job_post(state["session_id"])
            
            if latest_job_post:
                # Save to saved_job_posts table with company_id
                saved_job_post = db_ops.save_job_post(
                session_id=state["session_id"], 
                job_post=latest_job_post, 
                company_id=state.get("company_id"),
                total_iterations=state.get("iteration_count", 0)
                )
                
                success_msg = f"""💾 Job posted successfully on NextHire Website!
                
📋 **{state['job_post']['title']}** at **{state['job_post']['company']}**
🏢 Company ID: {state.get('company_id', 'N/A')}
🕒 Saved at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔄 Total iterations: {state.get('iteration_count', 0)}
🆔 Saved Job Post ID: {saved_job_post.id}

Thank you for using the HR Job Post System! 🎉"""
                
                state["messages"].append(AIMessage(content=success_msg))
                state["current_action"] = "saved"
                
                # Save AI message to database
                db_ops.add_message(state["session_id"], "ai", success_msg)
                
                # Update session status
                db_ops.update_session(
                    state["session_id"],
                    current_action="saved",
                    is_active=False,
                    awaiting_user_input=False
                )
                
                print(f"✅ Job post saved successfully for session: {state['session_id']}, company: {state.get('company_id', 'N/A')}")
                take = genarate_question(saved_job_post.id)
                print(f"take{take}")
            else:
                error_msg = "❌ Could not find job post to save."
                state["messages"].append(AIMessage(content=error_msg))
                db_ops.add_message(state["session_id"], "ai", error_msg)
                
        except Exception as e:
            error_msg = f"❌ Error saving job post: {str(e)}"
            state["messages"].append(AIMessage(content=error_msg))
            state["current_action"] = "error"
            db_ops.add_message(state["session_id"], "ai", error_msg)
            print(f"Save error in session {state['session_id']}: {e}")
        
        return state
    
    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """Parse JSON response from LLM"""
        try:
            response = response.strip()
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
            
            return json.loads(response)
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Response was: {response[:200]}...")
            return None
        except Exception as e:
            print(f"Error parsing response: {e}")
            return None
    
    def _format_job_post(self, job_post: Dict) -> str:
        """Format job post for display"""
        formatted = f"""
📋 **JOB POST**
{'='*50}

🏢 **Company:** {job_post.get('company', 'N/A')}
📍 **Location:** {job_post.get('location', 'N/A')}
💼 **Position:** {job_post.get('title', 'N/A')}
⏰ **Type:** {job_post.get('job_type', 'N/A')}
📈 **Level:** {job_post.get('experience_level', 'N/A')}
💰 **Salary:** {job_post.get('salary_range', 'N/A')}
🗓️ **Deadline:** {job_post.get('deadline', 'N/A')}"""
        
        # Add company ID if available
        if job_post.get('company_id'):
            formatted += f"\n🆔 **Company ID:** {job_post.get('company_id')}"
        
        formatted += f"""

**📝 Description:**
{job_post.get('description', 'N/A')}

**🎯 Key Responsibilities:**"""
        
        for i, resp in enumerate(job_post.get('responsibilities', []), 1):
            formatted += f"\n{i}. {resp}"
        
        formatted += "\n\n**✅ Requirements:**"
        for i, req in enumerate(job_post.get('requirements', []), 1):
            formatted += f"\n{i}. {req}"
        
        formatted += "\n\n**🎁 Benefits:**"
        for i, benefit in enumerate(job_post.get('benefits', []), 1):
            formatted += f"\n{i}. {benefit}"
        
        if job_post.get('created_at'):
            formatted += f"\n\n📅 **Created:** {job_post['created_at']}"
        if job_post.get('updated_at'):
            formatted += f"\n📅 **Last Updated:** {job_post['updated_at']}"
        
        return formatted
    
    def run(self, user_request: str, session_id: str, company_id: Optional[str] = None) -> Dict:
        """Run the complete workflow"""
        # Create or get session from database
        db_session = db_ops.get_session(session_id)
        if not db_session:
            db_session = db_ops.create_session(session_id, company_id=company_id)
        
        initial_state = {
            "messages": [HumanMessage(content=user_request)],
            "job_post": None,
            "user_request": user_request,
            "current_action": "initial",
            "iteration_count": 0,
            "awaiting_user_input": False,
            "session_id": session_id,
            "company_id": company_id
        }
        
        print(f"🚀 Starting HR Job Post Workflow for session {session_id}, company {company_id}: '{user_request}'")
        
        final_state = self.app.invoke(initial_state)
        return final_state
    
    def continue_workflow(self, session_id: str, user_input: str, company_id: Optional[str] = None) -> Dict:
        """Continue workflow with user input"""
        # Get session from database
        db_session = db_ops.get_session(session_id)
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get latest job post
        latest_job_post = db_ops.get_latest_job_post(session_id)
        job_post_dict = db_ops.job_post_to_dict(latest_job_post) if latest_job_post else None
        
        # Build state from database
        state = {
            "messages": [HumanMessage(content=user_input)],
            "job_post": job_post_dict,
            "user_request": user_input,
            "current_action": db_session.current_action,
            "iteration_count": db_session.iteration_count,
            "awaiting_user_input": False,
            "session_id": session_id,
            "company_id": company_id or db_session.company_id  # Use provided or stored company_id
        }
        
        user_input_lower = user_input.lower().strip()
        
        if any(keyword in user_input_lower for keyword in ['save', 'save it', 'save this', 'looks good', 'perfect', 'done','post','posted','post it','post this']):
            return self.save_job_post(state)
        else:
            state = self.update_job_post(state)
            return self.present_job_post(state)

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()

# FastAPI Application
app = FastAPI(
    title="HR Job Post Management System",
    description="AI-powered job post creation, editing, and management with PostgreSQL database",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
workflow_system = JobPostWorkflow()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for interacting with the HR Job Post system
    
    Examples:
    - "Create a job post for Python developer"
    - "Update job for Python developer"
    - "Save the job post"
    """
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Check if session exists in database
        existing_session = db_ops.get_session(session_id)
        
        if existing_session and existing_session.is_active:
            # Continue existing session
            updated_state = workflow_system.continue_workflow(
                session_id, 
                request.message, 
                company_id=request.company_id
            )
        else:
            # Start new session
            updated_state = workflow_system.run(
                request.message, 
                session_id, 
                company_id=request.company_id
            )
        
        # Get the latest AI message
        ai_messages = [msg for msg in updated_state["messages"] if isinstance(msg, AIMessage)]
        response_text = ai_messages[-1].content if ai_messages else "No response available"
        
        # Determine status
        status = updated_state.get("current_action", "processing")
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            status=status,
            job_post=updated_state.get("job_post"),
            awaiting_input=updated_state.get("awaiting_user_input", False)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@router.get("/job-posts")
def read_all_job_posts():
    """Get all saved job posts"""
    return db_ops.get_all_saved_job_posts()

@router.get("/job-posts/company/{company_id}")
def read_job_posts_by_company(company_id: str):
    """Get all job posts for a specific company"""
    return db_ops.get_job_posts_by_company(company_id)

@router.get("/jobs/{job_post_id}", response_model=SavedJobPostOut)
def get_job_by_id(job_post_id: int):
    db=db_ops.get_db_session()
    job = db.query(SavedJobPost).filter(SavedJobPost.id == job_post_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

if __name__ == "__main__":
    import uvicorn
    
    # Check credentials
    if not WATSONX_PROJECT_ID or not WATSONX_API_KEY:
        print("⚠️  Please set your WatsonX credentials as environment variables:")
        print("   export WATSONX_PROJECT_ID='your_project_id'")
        print("   export WATSONX_API_KEY='your_api_key'")
        exit(1)
    
    print("🚀 Starting HR Job Post Management API with PostgreSQL...")
    print("📋 API Documentation available at: http://localhost:8000/docs")
    print("🔍 Example usage:")
    print("   POST /chat with: {'message': 'Create a job post for Python developer', 'company_id': 'comp123'}")
    print("   POST /chat with: {'message': 'Update job for Python developer', 'session_id': 'your_session_id', 'company_id': 'comp123'}")
    print("🗄️  Database: PostgreSQL")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)