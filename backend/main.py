from fastapi import FastAPI
import coding_scoring_bot,form_scoring,hr_bot_related_apis,user_apis,hr_apis,auth,service_bot
from shortlistedcandidatesandsendmail import shortlistedcandidatesmail
from recomendation import run_recommendation
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from database import get_db, init_db, close_db
from databaseOperation import db_ops
from fastapi import FastAPI, Depends
from auth import get_current_user
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
scheduler = BackgroundScheduler()
# Start scheduler on FastAPI startup
@app.on_event("startup")
def start_scheduler():
    scheduler.add_job(shortlistedcandidatesmail, CronTrigger(hour=16, minute=15))
    scheduler.add_job(run_recommendation, CronTrigger(hour=16, minute=19))
    scheduler.start()
    

# Shutdown scheduler on app exit
@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()
  

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


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(hr_apis.router, prefix="/hr_apis", tags=["hr_apis"], dependencies=[Depends(get_current_user)])
app.include_router(service_bot.router, prefix="/service_bot", tags=["service_bot"])
app.include_router(user_apis.router, prefix="/user_apis", tags=["user_apis"], dependencies=[Depends(get_current_user)])
app.include_router(hr_bot_related_apis.router, prefix="/hr_bot", tags=["hr_bot"],dependencies=[Depends(get_current_user)])
#app.include_router(AUTH_SIGN.router, prefix="/AUTH_SIGN", tags=["AUTH_SIGN"])

#app.include_router(HR_bot.router, prefix="/HR_bot", tags=["HR_bot"])
#app.include_router(coding_scoring_bot.router, prefix="/coding_scoring_bot", tags=["coding_scoring_bot"])
app.include_router(form_scoring.router, prefix="/form_scoring", tags=["form_scoring"], dependencies=[Depends(get_current_user)])
#app.include_router(recomendetion.router, prefix="/recomendetion", tags=["recomendetion"], dependencies=[Depends(get_current_user)])
#app.include_router(HR_bot.router, prefix="/HR_bot", tags=["HR_bot"], dependencies=[Depends(get_current_user)])
#app.include_router(coding_scoring_bot.router, prefix="/coding_scoring_bot", tags=["coding_scoring_bot"], dependencies=[Depends(get_current_user)])

app.include_router(coding_scoring_bot.router, prefix="/coding_scoring_bot", tags=["coding_scoring_bot"], dependencies=[Depends(get_current_user)])




