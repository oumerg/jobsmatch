"""
Preference Management Package
Contains all preference-related modules for the job bot
"""

from .jobcatagories import JobCategoriesManager
from .jobtype import JobTypesManager
from .location import LocationManager
from .salary import SalaryManager
from .education import EducationManager
from .experience import ExperienceManager

__all__ = [
    'JobCategoriesManager',
    'JobTypesManager', 
    'LocationManager',
    'SalaryManager',
    'EducationManager',
    'ExperienceManager'
]
