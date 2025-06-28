import os
import uuid
from fastapi import APIRouter
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from pydantic_models import AnswerResponse, QuestionRequest
from databaseOperation import db_ops
from models import Conversation
from langchain_ibm import ChatWatsonx
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
    "max_new_tokens": 100,  # Increased for better JSON generation
    "temperature": 0.8,
    "top_p": 0.9,
    "repetition_penalty": 1.1
}

# Initialize ChatWatsonx
chat = ChatWatsonx(
    model_id="ibm/granite-3-8b-instruct",
    url=WATSONX_URL,
    project_id=WATSONX_PROJECT_ID,
    api_key=WATSONX_API_KEY,
    params=parameters
)

router = APIRouter()

# --- Embedding and Vector Store setup
embeddings_model_path = "ibm-granite/granite-embedding-30m-english"
embedding_model = HuggingFaceEmbeddings(model_name=embeddings_model_path)

def load_and_process_documents(file_path):
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        length_function=len
    )
    chunks = text_splitter.split_documents(documents)
    return chunks

def create_vector_store(chunks, persist_dir="./chroma_db"):
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=persist_dir
    )
    vector_store.persist()
    return vector_store

# --- Load or Create Vector Store (singleton style for app)
file_path = "nexthire customer service.pdf"
persist_dir = "./chroma_db"
if os.path.exists(persist_dir):
    vector_store = Chroma(persist_directory=persist_dir, embedding_function=embedding_model)
else:
    chunks = load_and_process_documents(file_path)
    vector_store = create_vector_store(chunks, persist_dir)

# --- API Endpoint (NO QA Chain, just manual workflow)
@router.post("/ask", response_model=AnswerResponse)
def ask_question(request: QuestionRequest):
    db = db_ops.get_db_session()
    session_id = request.session_id or str(uuid.uuid4())
    answer = None

    try:
        # 1. Retrieve relevant context from the vector store (top 3 most similar chunks)
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
        docs = retriever.get_relevant_documents(request.question)
        context = "\n\n".join(doc.page_content for doc in docs)

        # 2. Format the prompt manually
        prompt_template = """You are a helpful and concise Q&A bot for the NextHire website. Use only the provided context and conversation history to answer the user's question as accurately and briefly as possible.

**Instructions:**
- Give direct, factual answers in **20–30 words**.
- If the answer is not clearly present in the context or history, reply: "I do not know."
- Do not guess or make up information.
- Ignore irrelevant information in context/history.
- Avoid filler words or generic responses.

Context:
{context}

Question:
{question}

Answer:
"""
        prompt = prompt_template.format(context=context, question=request.question)

        # 3. Pass the prompt to your LLM directly
        llm_response = chat.invoke(prompt)
        # if isinstance(llm_response, dict) and "content" in llm_response:
        #     answer = llm_response["content"]
        # else:
        #     answer = llm_response

    except Exception as e:
        answer = f"Error: {e}"

    # 4. Save conversation to DB
    conversation = Conversation(
        session_id=session_id,
        question=request.question,
        answer=answer
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return AnswerResponse(session_id=session_id, answer=llm_response.content)
