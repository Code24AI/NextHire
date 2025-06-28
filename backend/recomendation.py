from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from sqlalchemy.orm import Session
from database import get_db
from models import SavedJobPost, QAScoring, Recommendation
from chat_llm_granite import chat  
from databaseOperation import db_ops
import pytz
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from sqlalchemy import func
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
import json
from typing import Text
scheduler = BackgroundScheduler()

from pydantic import BaseModel, Field
from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import SavedJobPost, QAScoring, Recommendation as RecommendationDB

# Use these Pydantic models exactly as you defined
class Recommendation(BaseModel):
    hire_decision: bool = Field(description="Whether to hire the candidate")
    comment: str = Field(description="Reasoning for the hiring decision", )

class CodeEvaluation(BaseModel):
    correctness_score: float = Field(ge=0, le=10, description="Score for code correctness (0-10)")
    efficiency_score: float = Field(ge=0, le=10, description="Score for code efficiency (0-10)")
    readability_score: float = Field(ge=0, le=10, description="Score for code readability (0-10)")
    edge_case_handling_score: float = Field(ge=0, le=10, description="Score for edge case handling (0-10)")
    overall_score: float = Field(ge=0, le=10, description="Weighted average score (0-10)")
    strengths: str = Field(description="Brief description of the code's strengths")
    weaknesses: str = Field(description="Brief description of the code's weaknesses")



RECOMMENDATION_PROMPT = PromptTemplate(
    input_variables=["scores"],
    template="""
You are an HR recommendation bot tasked with determining whether a candidate should be hired based on their coding challenge scores from a qa_scoring database table. The scores are provided as a JSON object with the following fields:
- correctness_score: float (0-10)
- efficiency_score: float (0-10)
- readability_score: float (0-10)
- edge_case_handling_score: float (0-10)
- overall_score: float (0-10)
- strengths: str
- weaknesses: str

**Task**:
- Decide whether to hire the candidate based on their scrores in different scoring criteria and also on strengths and weaknesses.
 Recommend hiring if all  scores 
(
correctness_score:>=7
efficiency_score: >=7
- readability_score: >=7
- edge_case_handling_score: >=7
- overall_score: >=7
)
 otherwise recommend against hiring.return False .
- Generate a concise comment (50-250 characters) explaining the decision, referencing the strengths and/or weaknesses to highlight why the candidate is suitable or not.

**Input**:
- **Scores**: {scores}

**Output**:
Return a JSON object conforming to this Pydantic rook:
```python
class Recommendation(BaseModel):
    hire_decision: bool
    comment: str
```

**Constraints**:
- hire_decision must be a boolean (true for hire, false for no hire).
- comment must be a string, 50-200 characters, explaining the decision.
- Base the decision primarily on the overall_score (threshold: 7.0) and strengths and weaknesses to craft a meaningful comment.

Provide the recommendation as a valid JSON object.
"""
)







def run_recommendation():
    db=db_ops.get_db_session()
    now = datetime.now(pytz.timezone("Asia/Dhaka")).replace(microsecond=0)
    

    job_posts = db.query(SavedJobPost).filter(SavedJobPost.deadline + timedelta(days=-6) < now, SavedJobPost.is_recomanded == False).all()

    for job in job_posts:
        candidate_scores = db.query(QAScoring).filter(QAScoring.job_id == job.id).all()

        for score in candidate_scores:
            # Validate and prepare input with CodeEvaluation model
            parser = JsonOutputParser(pydantic_object=Recommendation)
            validated_scores = CodeEvaluation(**{
            key: value for key, value in score.__dict__.items() if not key.startswith("_")
                   })

    
            # Generate recommendation
            #recommendation = validated_scores.dict()
            #scores_str = json.dumps(recommendation)
            # Call your LLM evaluation function passing the validated dict
            chain = RECOMMENDATION_PROMPT | chat | parser
            result = chain.invoke({"scores": validated_scores})
            print(result)
            # Validate the LLM response using Recommendation model
            
            recommendation = Recommendation(**result)
            # Save to DB
            db_recommendation = RecommendationDB(
                job_id=score.job_id,
                candidate_id=score.candidate_id,
                hire_decision=recommendation.hire_decision,
                comment=recommendation.comment
            )
            db.add(db_recommendation)

        # Mark the job as recommended after processing all candidates
        job.is_recomanded = True
        db.commit()


app = FastAPI()
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter()
@router.get("/trigger-now")
def trigger_recommendations():
    run_recommendation()
    return {"status": "Triggered"}
