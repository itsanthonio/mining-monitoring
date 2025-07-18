import os
import json
import re
import hmac
import hashlib
import time
import asyncio
import httpx
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from core.exceptions import SecurityError, ValidationError
import logging

logger = logging.getLogger(__name__)

class JobGeneratorService:
    """Secure job description generator service for FastAPI"""
    
    def __init__(self):
        load_dotenv()
        self.api_key = self._validate_api_key()
        self.api_endpoint = "https://api.deepseek.com/v1/chat/completions"
        self.security_headers = {
            'User-Agent': 'JobGenerator/1.0',
            'Accept': 'application/json',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
    
    def _validate_api_key(self) -> str:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise SecurityError("DEEPSEEK_API_KEY environment variable is required")
        if len(api_key) < 10 or not re.match(r'^[a-zA-Z0-9\-_]+$', api_key):
            raise SecurityError("Invalid API key format")
        return api_key
    
    def _categorize_experience(self, years: int) -> str:
        """Map years to experience level"""
        if years < 0:
            raise ValueError("Years of experience cannot be negative")
        if years <= 3:
            return "Entry"
        elif years <= 7:
            return "Mid"
        else:
            return "Senior"
    
    def _create_prompt(
        self,
        job_title: str,
        years: int,
        level: str,
        company_name: str,
        company_overview: str,
        skills: List[str],
        location: Optional[str] = None,
        employment_type: Optional[str] = None
    ) -> str:
        """Create a secure prompt with escaped content"""
        
        # Escape any potentially dangerous content
        safe_title = json.dumps(job_title)[1:-1]
        safe_company_name = json.dumps(company_name)[1:-1]
        safe_company_overview = json.dumps(company_overview)[1:-1]
        safe_skills = [json.dumps(skill)[1:-1] for skill in skills]
        
        skills_str = ", ".join(safe_skills)
        
        additional_info = ""
        if location:
            safe_location = json.dumps(location)[1:-1]
            additional_info += f"\nLocation: {safe_location}"
        if employment_type:
            additional_info += f"\nEmployment Type: {employment_type}"
        
        prompt = f"""Please generate a professional job description for a {safe_title} position.
Company: {safe_company_name}
Company Overview: {safe_company_overview}
Role: {safe_title} ({level} level, {years} years experience required)
Required skills: {skills_str}{additional_info}

Format the response strictly as a JSON object with the following structure:
{{
    "responsibilities": [
        "responsibility 1",
        "responsibility 2",
        ...
    ],
    "qualifications": [
        "qualification 1",
        "qualification 2",
        ...
    ],
    "required_skills": [
        "skill 1",
        "skill 2",
        ...
    ],
    "optional_skills": [
        "skill 1",
        "skill 2",
        ...
    ]
}}

Include 5-7 items in responsibilities and qualifications lists.
Extract and categorize skills into required and optional based on industry standards.
Focus on professional standards and industry requirements for {level} level positions with {years} years of experience."""
        
        return prompt
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize text content for output"""
        if not isinstance(text, str):
            return ""
        
        # Remove any potentially dangerous content
        malicious_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<link[^>]*>',
            r'<style[^>]*>.*?</style>',
            r'expression\s*\(',
            r'import\s+',
            r'exec\s*\(',
            r'eval\s*\(',
        ]
        
        for pattern in malicious_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Basic HTML escaping
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        
        return text.strip()
    
    async def _make_api_call(self, prompt: str) -> Dict[str, Any]:
        """Make secure async API call"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        headers.update(self.security_headers)
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional job description writer. Respond only with valid JSON. Do not include any code or script tags in your response."
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_endpoint,
                    headers=headers,
                    json=payload
                )
                
                response.raise_for_status()
                
                # Validate response content type
                content_type = response.headers.get('content-type', '').lower()
                if 'application/json' not in content_type:
                    raise SecurityError("Invalid response content type")
                
                return response.json()
                
        except httpx.TimeoutException:
            logger.error("API request timeout")
            raise SecurityError("Request timeout - please try again")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
            if e.response.status_code == 429:
                raise SecurityError("API rate limit exceeded - please wait before retrying")
            elif e.response.status_code == 401:
                raise SecurityError("API authentication failed")
            else:
                raise SecurityError("API request failed")
        except httpx.ConnectError:
            logger.error("Connection error")
            raise SecurityError("Unable to connect to API service")
        except Exception as e:
            logger.error(f"Unexpected API error: {e}")
            raise SecurityError("API request failed")
    
    def _generate_fallback(
        self,
        job_title: str,
        company_name: str,
        company_overview: str,
        years: int,
        level: str,
        location: Optional[str] = None,
        employment_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate secure fallback job description"""
        
        result = {
            "company_name": company_name,
            "company_overview": company_overview,
            "title": job_title,
            "experience_level": level,
            "experience_years": years,
            "responsibilities": [
                f"Lead {job_title} initiatives and projects",
                "Collaborate with cross-functional teams",
                "Implement industry best practices",
                "Develop and maintain documentation",
                "Contribute to process improvements"
            ],
            "qualifications": [
                f"Proven experience as a {job_title}",
                "Strong analytical and problem-solving skills",
                "Excellent communication abilities",
                "Team collaboration experience",
                "Relevant technical expertise"
            ],
            "required_skills": [
                "Communication",
                "Project Management",
                "Problem Solving"
            ],
            "optional_skills": [
                "Leadership",
                "Industry-specific knowledge",
                "Relevant certifications"
            ]
        }
        
        if location:
            result["location"] = location
        if employment_type:
            result["employment_type"] = employment_type
        
        logger.info("Generated fallback job description")
        return result
    
    async def generate_job_description_async(
        self,
        job_title: str,
        years: int,
        company_name: str,
        company_overview: str,
        skills: List[str],
        location: Optional[str] = None,
        employment_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate job description asynchronously"""
        
        try:
            level = self._categorize_experience(years)
            
            prompt = self._create_prompt(
                job_title, years, level, company_name,
                company_overview, skills, location, employment_type
            )
            
            response = await self._make_api_call(prompt)
            
            # Parse and format response
            if not response.get('choices'):
                raise SecurityError("Invalid API response structure")
            
            content = response['choices'][0]['message']['content'].strip()
            
            # Secure JSON parsing
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                logger.warning("No JSON object found in API response")
                return self._generate_fallback(
                    job_title, company_name, company_overview, 
                    years, level, location, employment_type
                )
            
            json_str = content[start_idx:end_idx + 1]
            
            try:
                parsed = json.loads(json_str)
                
                # Validate required keys
                required_keys = ['responsibilities', 'qualifications', 'required_skills', 'optional_skills']
                if not all(key in parsed for key in required_keys):
                    logger.warning("Missing required sections in API response")
                    return self._generate_fallback(
                        job_title, company_name, company_overview,
                        years, level, location, employment_type
                    )
                
                # Sanitize all text content
                sanitized_result = {
                    "company_name": company_name,
                    "company_overview": company_overview,
                    "title": job_title,
                    "experience_level": level,
                    "experience_years": years,
                    "responsibilities": [self._sanitize_text(r) for r in parsed['responsibilities'][:7]],
                    "qualifications": [self._sanitize_text(q) for q in parsed['qualifications'][:7]],
                    "required_skills": [self._sanitize_text(s) for s in parsed['required_skills'][:10]],
                    "optional_skills": [self._sanitize_text(s) for s in parsed['optional_skills'][:10]]
                }
                
                if location:
                    sanitized_result["location"] = location
                if employment_type:
                    sanitized_result["employment_type"] = employment_type
                
                return sanitized_result
                
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.warning(f"Error parsing API response: {e}")
                return self._generate_fallback(
                    job_title, company_name, company_overview,
                    years, level, location, employment_type
                )
                
        except SecurityError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise SecurityError("An error occurred while generating the job description")

