"""
Job Models and Matching Logic for Ethiopian Job Market
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, date
from enum import Enum

class UserRole(str, Enum):
    SEEKER = "seeker"
    EMPLOYER = "employer"
    ADMIN = "admin"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELED = "canceled"
    TRIAL = "trial"

class EducationLevel(str, Enum):
    HIGHSCHOOL = "highschool"
    DIPLOMA = "diploma"
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"
    OTHER = "other"

class JobType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    REMOTE = "remote"
    INTERNSHIP = "internship"

class MatchStatus(str, Enum):
    NEW = "new"
    VIEWED = "viewed"
    APPLIED = "applied"
    REJECTED = "rejected"
    SAVED = "saved"

class ApplicationStatus(str, Enum):
    SUBMITTED = "submitted"
    SEEN = "seen"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    HIRED = "hired"

class PaymentMethod(str, Enum):
    TELEBIRR = "telebirr"
    CBEBIRR = "cbebirr"
    HELLO_CASH = "hello_cash"
    MANUAL = "manual"

class User(BaseModel):
    user_id: int
    phone_number: Optional[str] = None
    telegram_id: Optional[int] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: UserRole = UserRole.SEEKER
    created_at: datetime
    last_active: Optional[datetime] = None
    language: str = "am"

class Subscription(BaseModel):
    subscription_id: Optional[int] = None
    user_id: int
    status: SubscriptionStatus = SubscriptionStatus.TRIAL
    start_date: date
    end_date: date
    payment_method: Optional[PaymentMethod] = None
    transaction_ref: Optional[str] = None
    amount_birr: float = 50.00
    renewal_count: int = 0
    created_at: datetime

class JobSeeker(BaseModel):
    seeker_id: Optional[int] = None
    user_id: int
    education_level: Optional[EducationLevel] = None
    field_of_study: Optional[str] = None
    years_experience: int = 0
    current_job_title: Optional[str] = None
    preferred_location: Optional[str] = None
    expected_salary: Optional[float] = None
    resume_text: Optional[str] = None
    updated_at: datetime

class Job(BaseModel):
    job_id: Optional[int] = None
    title: str
    company_name: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[JobType] = None
    salary_range: Optional[str] = None
    description: str
    requirements: Optional[str] = None
    posted_by_user_id: Optional[int] = None
    source: Optional[str] = None
    posted_date: date
    expires_date: Optional[date] = None
    is_active: bool = True
    views_count: int = 0

class JobMatch(BaseModel):
    match_id: Optional[int] = None
    user_id: int
    job_id: int
    match_score: Optional[float] = None
    status: MatchStatus = MatchStatus.NEW
    created_at: datetime

class Application(BaseModel):
    application_id: Optional[int] = None
    user_id: int
    job_id: int
    applied_at: datetime
    status: ApplicationStatus = ApplicationStatus.SUBMITTED
    notes: Optional[str] = None

class Skill(BaseModel):
    skill_id: Optional[int] = None
    name: str

class SeekerSkill(BaseModel):
    user_id: int
    skill_id: int
    level: str  # beginner, intermediate, expert
    years_experience: Optional[int] = None

class JobSkill(BaseModel):
    job_id: int
    skill_id: int
    required_level: str  # beginner, intermediate, expert

class JobMatcher:
    """Job matching algorithm for Ethiopian job market"""
    
    def __init__(self):
        self.location_weights = {
            'addis ababa': 1.0,
            'adama': 0.8,
            'dire dawa': 0.7,
            'mekelle': 0.6,
            'remote': 0.9
        }
    
    def calculate_match_score(self, seeker: JobSeeker, job: Job, seeker_skills: List[SeekerSkill], job_skills: List[JobSkill]) -> float:
        """Calculate match score between job seeker and job (0-100)"""
        score = 0.0
        
        # Education level matching (30% weight)
        if seeker.education_level and job.requirements:
            score += self._education_match(seeker.education_level, job.requirements) * 0.3
        
        # Experience matching (25% weight)
        score += self._experience_match(seeker.years_experience, job.requirements) * 0.25
        
        # Location matching (20% weight)
        if seeker.preferred_location and job.location:
            score += self._location_match(seeker.preferred_location.lower(), job.location.lower()) * 0.2
        
        # Skills matching (25% weight)
        seeker_skill_names = {s.skill_id for s in seeker_skills}
        job_skill_names = {j.skill_id for j in job_skills}
        
        if job_skill_names:
            skill_match = len(seeker_skill_names & job_skill_names) / len(job_skill_names)
            score += skill_match * 0.25
        
        return min(score * 100, 100.0)
    
    def _education_match(self, seeker_edu: EducationLevel, job_requirements: str) -> float:
        """Match education level with job requirements"""
        edu_levels = {
            EducationLevel.HIGHSCHOOL: 1,
            EducationLevel.DIPLOMA: 2,
            EducationLevel.BACHELOR: 3,
            EducationLevel.MASTER: 4,
            EducationLevel.PHD: 5
        }
        
        requirements_lower = job_requirements.lower()
        
        # Check for specific degree requirements
        if 'phd' in requirements_lower or 'doctorate' in requirements_lower:
            return 1.0 if seeker_edu == EducationLevel.PHD else 0.0
        elif 'master' in requirements_lower or 'm.sc' in requirements_lower:
            return 1.0 if edu_levels[seeker_edu] >= 4 else 0.5
        elif 'bachelor' in requirements_lower or 'degree' in requirements_lower:
            return 1.0 if edu_levels[seeker_edu] >= 3 else 0.3
        elif 'diploma' in requirements_lower:
            return 1.0 if edu_levels[seeker_edu] >= 2 else 0.2
        else:
            # No specific requirement, higher education gets bonus
            return min(edu_levels[seeker_edu] / 3.0, 1.0)
    
    def _experience_match(self, seeker_years: int, job_requirements: str) -> float:
        """Match years of experience with job requirements"""
        requirements_lower = job_requirements.lower()
        
        # Look for experience requirements in the text
        import re
        
        # Find patterns like "5 years", "3+ years", etc.
        experience_pattern = r'(\d+)\+?\s*years?'
        matches = re.findall(experience_pattern, requirements_lower)
        
        if matches:
            required_years = int(matches[0])
            if seeker_years >= required_years:
                return 1.0
            else:
                return seeker_years / required_years
        else:
            # No specific requirement, give partial credit based on experience
            return min(seeker_years / 5.0, 1.0)
    
    def _location_match(self, preferred: str, job_location: str) -> float:
        """Match preferred location with job location"""
        for location, weight in self.location_weights.items():
            if location in preferred or preferred in location:
                if location in job_location or job_location in location:
                    return weight
        
        # No location match
        return 0.2

class JobPostingService:
    """Service for posting and managing jobs"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.matcher = JobMatcher()
    
    async def post_job(self, job_data: Dict[str, Any]) -> bool:
        """Post a new job"""
        try:
            # Implementation would go here
            pass
        except Exception as e:
            print(f"Error posting job: {e}")
            return False
    
    async def find_matches_for_user(self, user_id: int, limit: int = 10) -> List[JobMatch]:
        """Find job matches for a user"""
        try:
            # Implementation would go here
            pass
        except Exception as e:
            print(f"Error finding matches: {e}")
            return []
