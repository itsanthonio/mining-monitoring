from fastapi import APIRouter, HTTPException, status, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from api.v1.schemas.job import JobRequest, JobResponse
from core.services import JobGeneratorService
from core.exceptions import SecurityError, ValidationError
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limiter for job generation
limiter = Limiter(key_func=get_remote_address)

@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def generate_job_description(
    request: Request,  # This is required for slowapi rate limiting
    job_request: JobRequest,
    generator: JobGeneratorService = Depends(JobGeneratorService)
):
    """Generate a professional job description based on the provided requirements."""
    try:
        job_description = await generator.generate_job_description_async(
            job_title=job_request.job_title,
            years=job_request.years_experience,
            company_name=job_request.company_name,
            company_overview=job_request.company_overview,
            skills=job_request.skills,
            location=job_request.location,
            employment_type=job_request.employment_type
        )
        
        return JobResponse(**job_description)
        
    except SecurityError as e:
        logger.error(f"Security error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the job description"
        )

@router.get("/jobs/experience-levels")
async def get_experience_levels():
    """Get available experience levels and their year ranges."""
    return {
        "experience_levels": [
            {"level": "Entry", "years_range": "0-3"},
            {"level": "Mid", "years_range": "4-7"},
            {"level": "Senior", "years_range": "8+"}
        ]
    }