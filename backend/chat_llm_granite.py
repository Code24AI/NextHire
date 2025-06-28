
import os
import json
from typing import Dict, List, Optional, TypedDict, Annotated
from datetime import datetime

# LangChain imports
from langchain_ibm import ChatWatsonx
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
# Configuration
WATSONX_URL = "https://au-syd.ml.cloud.ibm.com"
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_API_KEY = os.getenv("WATSONX_API_KEY")

# WatsonX parameters
parameters = {
    "decoding_method": "greedy",
    "max_new_tokens": 250,  # Increased for better JSON generation
    "temperature": 0.7,
    "top_p": 0.9,
    "repetition_penalty": 1.1
}

# Initialize ChatWatsonx
chat = ChatWatsonx(
    model_id="ibm/granite-3-8b-instruct",
    url=WATSONX_URL,
    project_id=WATSONX_PROJECT_ID,
    api_key=WATSONX_API_KEY,  # Added missing API key
    params=parameters
)
