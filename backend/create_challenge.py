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
from database import get_db, init_db, close_db
from models import Session as DBSession, JobPost, Message, SavedJobPost
from databaseOperation import db_ops
from chat_llm_granite import chat

# Load environment variables from .env file
load_dotenv()

# Configuration


from langchain_core.prompts import PromptTemplate  # if you're using LangChain
from typing import Optional

def genarate_question(job_id: int) -> Optional[str]:
    # 1. Fetch job from DB
    job = db_ops.getting_saved_job_id(job_id)
    if not job:
        return None

    # 2. Prepare prompt data
    prompt_data = {
        "job_title": job.title,
        "company": job.company,
        "experience_level": job.experience_level,
        "job_description": job.description,
        "requirements": ", ".join(job.requirements or []),
        "job_responsibilities": ", ".join(job.responsibilities or []),
        "years": str(job.experience_level)
    }

    # 3. Template
    template = """
    Create a coding challenge for a {job_title} with {years} years of experience ({experience_level} level).
    JOB DETAILS:
    Title: {job_title}
    Company: {company}
    Experience Level: {experience_level}
    Description: {job_description}
    Requirements: {requirements}
    Responsibilities: {job_responsibilities}

    Using this job data, create a coding challenge that checks in-depth understanding.
    It must cover:
    - System design and architecture
    - Database design and optimization  
    - API design and scalability
    - Concurrency and distributed systems
    - Performance optimization
    - Security considerations

    Experience Level Guidelines:
    - Junior (0-2 years): Basic algorithms, simple API design
    - Mid (2-5 years): System design, caching
    - Senior (5-8 years): Distributed systems, advanced concurrency
    - Principal (8+ years): Large-scale architecture, trade-offs

    The challenge timmer will showed on the top of the page:
    1. Clear problem statement
    2. Technical requirements
    3. Performance constraints
   
    

    Make it realistic and similar to actual production work.tell user to only submit the code in the provided code editor in this webpage.
    """

    # 4. Fill prompt
    prompt = PromptTemplate.from_template(template)
    filled_prompt = prompt.format(**prompt_data)

    # 5. Call LLM
    result = chat.invoke(filled_prompt).content.strip()

    update = db_ops.update_coding_challenge( job_id, result)
    if update:
        return result

    


