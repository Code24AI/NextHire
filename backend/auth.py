from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import Column, Integer, String, create_engine, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from typing import Optional
from jose import JWTError, jwt
from datetime import datetime, timedelta
from models import Candidate, Company,SavedJobPost
import random
import string
import aiosmtplib
from email.message import EmailMessage
from databaseOperation import db_ops
from pydantic_models import SavedJobPostOut
import os
# -------------------- EMAIL CONFIG --------------------
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
  
from dotenv import load_dotenv
load_dotenv()
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
async def send_otp_email(email: str, otp: str):
    try:
        # Create email message
        message = EmailMessage()
        message.set_content(
    f"Dear User,\n\n"
    f"Your OTP for NextHire registration is: {otp}\n"
    f"This OTP is valid for {OTP_EXPIRE_MINUTES} minutes.\n\n"
    "Please do not share this OTP with anyone for security reasons.\n"
    "If you did not request this OTP, please ignore this email.\n\n"
    "Best regards,\n"
    "Team NextHire"
)


        message["Subject"] = "Your OTP for NextHire Registration"
        message["From"] = SENDER_EMAIL
        message["To"] = email

        # Send email using aiosmtplib
        await aiosmtplib.send(
            message,
            hostname=EMAIL_HOST,
            port=EMAIL_PORT,
            start_tls=True,
            username=SENDER_EMAIL,
            password=SENDER_PASSWORD,
        )
        return True
    except Exception as e:
        print(f"Failed to send OTP email: {str(e)}")  # Log error for debugging
        return False

# -------------------- DB CONFIG --------------------

Base = declarative_base()


# -------------------- OTP MODEL --------------------
class OTP(Base):
    __tablename__ = "otps"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    otp = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

# -------------------- APP CONFIG --------------------
app = FastAPI()
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/candidate/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 5000
OTP_EXPIRE_MINUTES = 5



# -------------------- SCHEMAS --------------------
class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    role:str
    user_name:str


class CandidateCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str

class CompanyCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str
    address: Optional[str] = None

class OTPRequest(BaseModel):
    email: EmailStr

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str

# -------------------- UTILS --------------------


def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def authenticate_user(db: Session, email: str, password: str, role: str):
    user = None
    if role == "candidate":
        user = db.query(Candidate).filter(Candidate.email == email).first()
    elif role == "company":
        user = db.query(Company).filter(Company.email == email).first()
    if user and verify_password(password, user.password):
        return user
    return None

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

# -------------------- OTP ROUTES --------------------
@router.post("/otp/request")
async def request_otp(data: OTPRequest):
    db=db_ops.get_db_session()
    # Check if email already registered
    if (db.query(Candidate).filter(Candidate.email == data.email).first() or
        db.query(Company).filter(Company.email == data.email).first()):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Delete any existing OTP for this email
    db.query(OTP).filter(OTP.email == data.email).delete()

    # Generate and store new OTP
    otp = generate_otp()
    otp_entry = OTP(
        email=data.email,
        otp=otp,
        expires_at=datetime.utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES)
    )
    db.add(otp_entry)
    db.commit()

    # Send OTP
    if not await send_otp_email(data.email, otp):
        raise HTTPException(status_code=500, detail="Failed to send OTP")

    return {"msg": "OTP sent to email"}

# -------------------- SIGNUP ROUTES --------------------
@router.post("/candidate/signup")
async def signup_candidate(data: CandidateCreate, otp_data: OTPVerify):
    db=db_ops.get_db_session()
    # Verify OTP
    otp_entry = db.query(OTP).filter(OTP.email == otp_data.email).first()
    if not otp_entry or otp_entry.otp != otp_data.otp or otp_entry.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Create candidate
    if db.query(Candidate).filter(Candidate.email == data.email).first():
        raise HTTPException(status_code=400, detail="Candidate already exists")
    new_user = Candidate(
        name=data.name,
        email=data.email,
        password=get_password_hash(data.password),
        phone=data.phone
    )
    db.add(new_user)
    db.delete(otp_entry)  # Delete used OTP
    db.commit()
    return {"msg": "Candidate registered"}

@router.post("/company/signup")
async def signup_company(data: CompanyCreate, otp_data: OTPVerify):
    db=db_ops.get_db_session()
    # Verify OTP
    otp_entry = db.query(OTP).filter(OTP.email == otp_data.email).first()
    if not otp_entry or otp_entry.otp != otp_data.otp or otp_entry.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Create company
    if db.query(Company).filter(Company.email == data.email).first():
        raise HTTPException(status_code=400, detail="Company already exists")
    new_user = Company(
        name=data.name,
        email=data.email,
        password=get_password_hash(data.password),
        phone=data.phone,
        address=data.address
    )
    db.add(new_user)
    db.delete(otp_entry)  # Delete used OTP
    db.commit()
    return {"msg": "Company registered"}

# -------------------- LOGIN ROUTES --------------------
@router.post("/candidate/login", response_model=Token)
async def login_candidate(form_data: OAuth2PasswordRequestForm = Depends()):
    db=db_ops.get_db_session()
    user = authenticate_user(db, form_data.username, form_data.password, "candidate")
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.email, "role": "candidate"},expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": token, "token_type": "bearer","user_id": user.id,"role":"candidate","user_name":user.name}

@router.post("/company/login", response_model=Token)
async def login_company(form_data: OAuth2PasswordRequestForm = Depends()):
    db=db_ops.get_db_session()
    user = authenticate_user(db, form_data.username, form_data.password, "company")
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.email, "role": "company"},expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    print(user.name)
    return {"access_token": token, "token_type": "bearer","user_id": user.id,"role":"HR","user_name":user.name}

# -------------------- AUTH CHECK + ROLE DEPENDENCY --------------------
def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(status_code=401, detail="Invalid token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        if not email or not role:
            raise credentials_exception
        return {"email": email, "role": role}
    except JWTError:
        raise credentials_exception

def require_role(required_role: str):
    def role_dependency(user=Depends(get_current_user)):
        if user["role"] != required_role:
            raise HTTPException(status_code=403, detail=f"Access denied for role {user['role']}")
        return user
    return role_dependency

# -------------------- PROTECTED ROUTES --------------------
@router.get("/auth/test")
def test_auth(user=Depends(get_current_user)):
    return {"msg": f"Hello {user['role']} {user['email']} - you are authenticated"}



@router.get("/job-posts")
def read_all_job_posts():
    """Get all saved job posts"""
    db=db_ops.get_db_session()
    return db.query(SavedJobPost).all()



from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


SQLALCHEMY_DATABASE_URL = "postgresql://postgres:1234@localhost:5432/nexthire"


engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,  # Connection pool size
    max_overflow=10  # Allow extra connections
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/job-posts2")
def read_all_job_posts(db: Session = Depends(get_db)):
    return db.query(SavedJobPost).all()

@router.get("/jobs/{job_post_id}", response_model=SavedJobPostOut)
def get_job_by_id(job_post_id: int):
    db=db_ops.get_db_session()
    job = db.query(SavedJobPost).filter(SavedJobPost.id == job_post_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job