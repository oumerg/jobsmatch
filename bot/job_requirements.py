"""
Job Requirements Management
Handles experience levels, skills, qualifications, and other job requirements
"""

import logging
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class ExperienceLevel(Enum):
    """Experience level enumeration"""
    ENTRY_LEVEL = "entry_level"
    JUNIOR = "junior"
    MID_LEVEL = "mid_level"
    SENIOR = "senior"
    LEAD = "lead"
    MANAGER = "manager"
    DIRECTOR = "director"
    EXECUTIVE = "executive"

class EducationLevel(Enum):
    """Education level enumeration"""
    HIGH_SCHOOL = "high_school"
    DIPLOMA = "diploma"
    BACHELORS = "bachelors"
    MASTERS = "masters"
    PHD = "phd"
    PROFESSIONAL = "professional"
    OTHER = "other"

class JobRequirementsManager:
    """Manages job requirements and qualifications"""
    
    def __init__(self):
        # Experience level requirements
        self.experience_levels = {
            'entry_level': {
                'display': '👶 Entry Level (0-2 years)',
                'description': 'Suitable for recent graduates and beginners',
                'skills_required': ['basic communication', 'teamwork', 'eagerness to learn']
            },
            'junior': {
                'display': '🚀 Junior (2-5 years)',
                'description': 'Some professional experience required',
                'skills_required': ['problem solving', 'time management', 'intermediate skills']
            },
            'mid_level': {
                'display': '💼 Mid-Level (5-10 years)',
                'description': 'Solid professional experience required',
                'skills_required': ['leadership', 'project management', 'advanced skills']
            },
            'senior': {
                'display': '🎯 Senior (10+ years)',
                'description': 'Extensive professional experience required',
                'skills_required': ['strategic thinking', 'mentoring', 'expert skills']
            },
            'lead': {
                'display': '👨‍💼 Team Lead',
                'description': 'Leadership and team management experience',
                'skills_required': ['team leadership', 'conflict resolution', 'performance management']
            },
            'manager': {
                'display': '🏢 Manager',
                'description': 'Department or team management experience',
                'skills_required': ['budget management', 'strategic planning', 'department leadership']
            },
            'director': {
                'display': '🏢 Director',
                'description': 'Senior leadership and strategic direction',
                'skills_required': ['executive leadership', 'business strategy', 'organizational development']
            },
            'executive': {
                'display': '👔 Executive',
                'description': 'C-level or senior executive experience',
                'skills_required': ['executive decision making', 'corporate strategy', 'board relations']
            }
        }
        
        # Education level requirements
        self.education_levels = {
            'high_school': {
                'display': '🎓 High School',
                'description': 'High school diploma or equivalent',
                'typical_roles': ['intern', 'junior assistant', 'entry level']
            },
            'diploma': {
                'display': '📜 Diploma',
                'description': 'Technical or vocational diploma',
                'typical_roles': ['technician', 'specialist', 'junior professional']
            },
            'bachelors': {
                'display': '🎓 Bachelor\'s Degree',
                'description': 'Undergraduate degree from accredited institution',
                'typical_roles': ['professional', 'analyst', 'coordinator']
            },
            'masters': {
                'display': '🎯 Master\'s Degree',
                'description': 'Graduate degree with specialization',
                'typical_roles': ['senior professional', 'manager', 'specialist']
            },
            'phd': {
                'display': '🔬 PhD / Doctorate',
                'description': 'Doctoral degree or equivalent research qualification',
                'typical_roles': ['researcher', 'professor', 'executive']
            },
            'professional': {
                'display': '📚 Professional Certification',
                'description': 'Industry-recognized professional certification',
                'typical_roles': ['certified professional', 'specialist', 'consultant']
            },
            'other': {
                'display': '👤 Other',
                'description': 'Other qualifications or combination of experience',
                'typical_roles': ['various based on experience']
            }
        }
        
        # Common skill categories
        self.skill_categories = {
            'technical': {
                'display': '💻 Technical Skills',
                'skills': [
                    'Python', 'JavaScript', 'Java', 'C#', 'SQL', 'NoSQL',
                    'React', 'Node.js', 'Django', 'Flask', 'AWS', 'Docker',
                    'Git', 'Linux', 'Windows Server', 'Networking', 'Cybersecurity'
                ]
            },
            'business': {
                'display': '💼 Business Skills',
                'skills': [
                    'Project Management', 'Business Analysis', 'Financial Analysis',
                    'Marketing', 'Sales', 'Customer Service', 'HR Management',
                    'Strategic Planning', 'Budget Management', 'Risk Assessment'
                ]
            },
            'creative': {
                'display': '🎨 Creative Skills',
                'skills': [
                    'Graphic Design', 'UI/UX Design', 'Video Editing',
                    'Content Writing', 'Social Media Management', 'Photography',
                    'Animation', 'Copywriting', 'Brand Management'
                ]
            },
            'soft_skills': {
                'display': '🤝 Soft Skills',
                'skills': [
                    'Communication', 'Leadership', 'Teamwork', 'Problem Solving',
                    'Time Management', 'Adaptability', 'Critical Thinking',
                    'Creativity', 'Emotional Intelligence', 'Negotiation'
                ]
            },
            'industry_specific': {
                'display': '🏭 Industry-Specific Skills',
                'skills': [
                    'Healthcare', 'Banking', 'Education', 'Manufacturing',
                    'Agriculture', 'Hospitality', 'Construction', 'Transportation',
                    'Government', 'Legal', 'Research', 'Consulting'
                ]
            }
        }
        
        # Common certifications
        self.certifications = {
            'technical': [
                'CompTIA A+', 'CompTIA Network+', 'CompTIA Security+',
                'AWS Certified Developer', 'AWS Solutions Architect', 'Google Cloud Certified',
                'Microsoft Azure', 'Cisco CCNA', 'Oracle Certified',
                'PMP (Project Management)', 'Scrum Master', 'ITIL Foundation'
            ],
            'business': [
                'PMP (Project Management)', 'PRINCE2', 'Six Sigma',
                'CPA (Accounting)', 'CFA (Finance)', 'PHR (HR)',
                'Digital Marketing Certified', 'Salesforce Certified', 'Business Analysis Certified'
            ],
            'healthcare': [
                'BLS/CPR Certified', 'First Aid Certified', 'HIPAA Compliance',
                'Nursing License', 'Medical Assistant Certified', 'Healthcare IT Certified'
            ],
            'education': [
                'Teaching License', 'TESOL/TEFL Certified', 'Educational Technology',
                'Curriculum Development', 'Special Education Certified', 'School Administration'
            ]
        }
    
    def get_experience_requirements(self, level: str) -> Dict[str, Any]:
        """Get requirements for experience level"""
        return self.experience_levels.get(level, {})
    
    def get_education_requirements(self, level: str) -> Dict[str, Any]:
        """Get requirements for education level"""
        return self.education_levels.get(level, {})
    
    def get_skills_by_category(self, category: str) -> List[str]:
        """Get skills by category"""
        return self.skill_categories.get(category, {}).get('skills', [])
    
    def get_certifications_by_field(self, field: str) -> List[str]:
        """Get certifications by field"""
        return self.certifications.get(field, [])
    
    def validate_experience_match(self, candidate_experience: int, required_level: str) -> bool:
        """Validate if candidate experience matches requirement"""
        level_requirements = {
            'entry_level': (0, 2),
            'junior': (2, 5),
            'mid_level': (5, 10),
            'senior': (10, 100),
            'lead': (7, 100),
            'manager': (8, 100),
            'director': (10, 100),
            'executive': (15, 100)
        }
        
        min_exp, max_exp = level_requirements.get(required_level, (0, 100))
        return min_exp <= candidate_experience <= max_exp
    
    def get_salary_expectation(self, level: str, location: str = 'Addis Ababa') -> Dict[str, int]:
        """Get expected salary range based on experience level and location"""
        # Base salary ranges for different levels in Birr
        base_ranges = {
            'entry_level': {'min': 5000, 'max': 12000},
            'junior': {'min': 8000, 'max': 18000},
            'mid_level': {'min': 15000, 'max': 30000},
            'senior': {'min': 25000, 'max': 50000},
            'lead': {'min': 35000, 'max': 65000},
            'manager': {'min': 45000, 'max': 80000},
            'director': {'min': 60000, 'max': 120000},
            'executive': {'min': 80000, 'max': 200000}
        }
        
        # Location adjustments (Addis Ababa is baseline)
        location_multipliers = {
            'Addis Ababa': 1.0,
            'Adama / Nazret': 0.8,
            'Dire Dawa': 0.9,
            'Mekelle': 0.7,
            'Bahir Dar': 0.8,
            'Hawassa': 0.7,
            'Jimma': 0.6,
            'Gondar': 0.6,
            'Remote': 1.2  # Remote jobs often pay more
        }
        
        multiplier = location_multipliers.get(location, 1.0)
        base_range = base_ranges.get(level, {'min': 5000, 'max': 12000})
        
        return {
            'min': int(base_range['min'] * multiplier),
            'max': int(base_range['max'] * multiplier)
        }
    
    def format_job_requirements(self, experience: str, education: str, skills: List[str]) -> str:
        """Format job requirements for display"""
        exp_info = self.get_experience_requirements(experience)
        edu_info = self.get_education_requirements(education)
        
        message = (
            f"📋 *Job Requirements*\n\n"
            f"🎯 *Experience Level:* {exp_info.get('display', experience)}\n"
            f"📚 *Education:* {edu_info.get('display', education)}\n\n"
            f"📝 *Description:* {exp_info.get('description', '')}\n\n"
            f"🔧 *Required Skills:* {', '.join(skills[:5])}"
            f"{'...' if len(skills) > 5 else ''}\n\n"
        )
        
        return message
    
    def get_career_progression_path(self, level: str) -> List[str]:
        """Get typical career progression path"""
        progression_map = {
            'entry_level': ['Junior Professional', 'Mid-Level Professional', 'Senior Professional', 'Team Lead'],
            'junior': ['Mid-Level Professional', 'Senior Professional', 'Team Lead', 'Manager'],
            'mid_level': ['Senior Professional', 'Team Lead', 'Manager', 'Director'],
            'senior': ['Team Lead', 'Manager', 'Director', 'Executive'],
            'lead': ['Manager', 'Director', 'Executive', 'VP'],
            'manager': ['Director', 'Executive', 'VP', 'C-Level'],
            'director': ['Executive', 'VP', 'C-Level', 'Board Member'],
            'executive': ['Board Member', 'Chairperson', 'CEO', 'Entrepreneur']
        }
        
        return progression_map.get(level, [])
    
    def assess_skill_gap(self, candidate_skills: List[str], required_skills: List[str]) -> Dict[str, Any]:
        """Assess skill gaps between candidate and requirements"""
        candidate_set = set(skill.lower() for skill in candidate_skills)
        required_set = set(skill.lower() for skill in required_skills)
        
        matched_skills = candidate_set & required_set
        missing_skills = required_set - candidate_set
        
        match_percentage = (len(matched_skills) / len(required_set)) * 100 if required_skills else 0
        
        return {
            'matched_skills': list(matched_skills),
            'missing_skills': list(missing_skills),
            'match_percentage': round(match_percentage, 1),
            'total_required': len(required_skills),
            'total_matched': len(matched_skills)
        }

# Example usage functions
def create_job_requirement_template(experience_level: str, education_level: str, 
                                 skills: List[str], location: str = 'Addis Ababa') -> Dict[str, Any]:
    """Create a complete job requirement template"""
    manager = JobRequirementsManager()
    
    return {
        'experience': manager.get_experience_requirements(experience_level),
        'education': manager.get_education_requirements(education_level),
        'skills': skills,
        'salary_expectation': manager.get_salary_expectation(experience_level, location),
        'career_progression': manager.get_career_progression_path(experience_level),
        'skill_categories': manager.skill_categories
    }

if __name__ == "__main__":
    # Example usage
    manager = JobRequirementsManager()
    
    # Test experience requirements
    print("=== Experience Requirements ===")
    for level in manager.experience_levels.keys():
        req = manager.get_experience_requirements(level)
        print(f"{level}: {req.get('display')}")
    
    # Test salary expectations
    print("\n=== Salary Expectations ===")
    for level in ['entry_level', 'junior', 'mid_level', 'senior']:
        salary = manager.get_salary_expectation(level)
        print(f"{level}: {salary['min']}-{salary['max']} Birr")
    
    # Test skill gap assessment
    print("\n=== Skill Gap Assessment ===")
    candidate_skills = ['Python', 'Project Management', 'Communication']
    required_skills = ['Python', 'JavaScript', 'Project Management', 'Leadership']
    gap = manager.assess_skill_gap(candidate_skills, required_skills)
    print(f"Match: {gap['match_percentage']}%")
    print(f"Missing: {gap['missing_skills']}")
