from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from api.v1.endpoints import jobs
from core.exceptions import register_exception_handlers
from core.logging import setup_logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Job Description Generator API",
    description="A secure RESTful API for generating professional job descriptions",
    version="1.0.0"
)

# Set up rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

# Set up logging
setup_logging()

# Register exception handlers
register_exception_handlers(app)

# Include API routers 
app.include_router(jobs.router, prefix="/api/v1", tags=["Jobs"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Job Description Generator API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}