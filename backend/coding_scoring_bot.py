from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableSequence
from chat_llm_granite import chat
from databaseOperation import db_ops
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter()
from typing import Dict, Any
import os
from database import get_db, init_db, close_db
# FastAPI app initialization
app = FastAPI(
    title="Coding Challenge Scoring Bot API",
    description="API to evaluate coding challenge submissions based on correctness, efficiency, readability, and edge case handling.",
    version="1.0.0"
)
# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup"""
    print("🔧 Initializing database...")
    init_db()
    print("✅ Database initialized successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown"""
    print("🔧 Closing database connections...")
    close_db()
    db_ops.close_db_session()
    print("✅ Database connections closed!")

class CodeEvaluation(BaseModel):
    correctness_score: float = Field(ge=0, le=10, description="Score for code correctness (0-10)")
    efficiency_score: float = Field(ge=0, le=10, description="Score for code efficiency (0-10)")
    readability_score: float = Field(ge=0, le=10, description="Score for code readability (0-10)")
    edge_case_handling_score: float = Field(ge=0, le=10, description="Score for edge case handling (0-10)")
    overall_score: float = Field(ge=0, le=10, description="Weighted average score (0-10)")
    strengths: str = Field(description="Brief description of the code's strengths")
    weaknesses: str = Field(description="Brief description of the code's weaknesses")

# Pydantic schema for request input
#class CodeSubmission(BaseModel):
    #challenge: str = Field(description="Description of the coding challenge", min_length=10)
    #answer: str = Field(description="Submitted code answer", min_length=1)


class CodeSubmission(BaseModel):
    challenge: str = Field(..., description="Coding challenge description", min_length=10)
    answer: str = Field(..., description="Multiline submitted code")
    job_id: int = Field(..., description="Job ID associated with the submission")
    candidate_id: int = Field(..., description="Candidate ID associated with the submission")


# LangChain prompt template for code evaluation with escaped braces
EVALUATION_PROMPT = PromptTemplate(
    input_variables=["challenge", "answer"],
    template="""
You are an expert coding challenge scoring bot. Your task is to evaluate a user's code submission for a given coding challenge. Analyze the code based on the following criteria, each scored out of 10 (provide float scores, rounded to two decimal places):
1. **Correctness**: Does the code produce the correct output for the given inputs, including edge cases, as specified in the challenge?
2. **Efficiency**: How optimal is the code in terms of time and space complexity relative to the challenge's constraints?
3. **Readability**: Is the code well-organized, clear, and maintainable (e.g., meaningful variable names, proper indentation, comments)?
4. **Edge Case Handling**: Does the code handle edge cases and boundary conditions effectively, as outlined in the challenge?

Calculate an **Overall Score** (out of 10) as a weighted average:
- Correctness: 40% weight
- Efficiency: 30% weight
- Readability: 20% weight
- Edge Case Handling: 10% weight

Provide qualitative feedback:
- **Strengths**: A concise description (50-200 characters) of what the code does well.
- **Weaknesses**: A concise description (50-200 characters) of areas for improvement.

**Input**:
- **Coding Challenge**: {challenge}
- **Submitted Answer**: 
{answer}

**Output**:
Return a JSON object conforming to this Pydantic schema:
```python
class CodeEvaluation(BaseModel):
    correctness_score: float
    efficiency_score: float
    readability_score: float
    edge_case_handling_score: float
    overall_score: float
    strengths: str
    weaknesses: str
```

**Constraints**:
- All scores must be between 0 and 10, rounded to two decimal places.
- Strengths and weaknesses must be non-empty, 50-200 characters each.
- If the code is invalid or fails to run, assign low scores and explain in weaknesses.
- Assume Python code unless specified otherwise.
- Simulate evaluation based on code analysis (no actual execution).

**Example**:
**Challenge**: Write a function to check if a string is a palindrome. Ignore case and non-alphanumeric characters.
**Answer**:
```python
def isPalindrome(s: str) -> bool:
    s = ''.join(c.lower() for c in s if c.isalnum())
    return s == s[::-1]
```
**Output**:
```json
{{
    "correctness_score": 8.50,
    "efficiency_score": 7.00,
    "readability_score": 9.00,
    "edge_case_handling_score": 8.00,
    "overall_score": 8.05,
    "strengths": "Clean and concise code with clear logic. Handles case and non-alphanumeric characters well.",
    "weaknesses": "Using string slicing (s[::-1]) may be less efficient for very large strings."
}}
```

Provide the evaluation as a valid JSON object.
"""
)

# Function to simulate code analysis
def analyze_code(challenge: str, answer: str) -> Dict[str, Any]:
    try:
        # Set up JSON output parser
        parser = JsonOutputParser(pydantic_object=CodeEvaluation)
        
        # Create LangChain evaluation chain
        chain = EVALUATION_PROMPT | chat | parser
        
        # Run the chain with input
        result = chain.invoke({"challenge": challenge, "answer": answer})
        
        # Validate and adjust output
        result["correctness_score"] = round(min(max(result["correctness_score"], 0), 10), 2)
        result["efficiency_score"] = round(min(max(result["efficiency_score"], 0), 10), 2)
        result["readability_score"] = round(min(max(result["readability_score"], 0), 10), 2)
        result["edge_case_handling_score"] = round(min(max(result["edge_case_handling_score"], 0), 10), 2)
        
        # Calculate overall score
        result["overall_score"] = round(
            (0.4 * result["correctness_score"] +
             0.3 * result["efficiency_score"] +
             0.2 * result["readability_score"] +
             0.1 * result["edge_case_handling_score"]), 2
        )
        
        # Ensure strengths and weaknesses are within length constraints
        result["strengths"] = result["strengths"][:200] if len(result["strengths"]) > 200 else result["strengths"]
        result["weaknesses"] = result["weaknesses"][:200] if len(result["weaknesses"]) > 200 else result["weaknesses"]
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")
from sqlalchemy.orm import Session
from models import QAScoring


# FastAPI endpoint to evaluate code submission
@router.post("/evaluate", response_model=CodeEvaluation)
async def evaluate_code(submission: CodeSubmission):
    """
    Evaluate a coding challenge submission and return scores for correctness, efficiency, readability, and edge case handling.
    
    Args:
        submission: Object containing the coding challenge and submitted answer.
    
    Returns:
        CodeEvaluation: Structured evaluation with scores and feedback.
    
    Raises:
        HTTPException: If evaluation fails due to invalid input or internal error.
    """
    try:
        result = analyze_code(submission.challenge, submission.answer)
        db_ops.insert_scores(
            
            challenge=submission.challenge,
            answer=submission.answer,
            job_id=submission.job_id,
            candidate_id=submission.candidate_id,
            evaluation=result
        )
        return CodeEvaluation(**result)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

