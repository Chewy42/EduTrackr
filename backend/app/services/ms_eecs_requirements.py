"""
M.S. EECS Requirements Loader

This module provides functions to load and work with the M.S. Electrical Engineering
and Computer Science curriculum requirements from the JSON configuration file.

The configuration file (ms_eecs_requirements.json) contains:
- Program metadata (name, code, total credits)
- Curriculum structure (Ethics Core, Leadership Core, Technical Core, Mastery Demonstration)
- Valid course codes for the program
- Spring 2026 available courses specific to EECS students
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Path to the MS EECS requirements JSON file
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MS_EECS_REQUIREMENTS_PATH = DATA_DIR / "ms_eecs_requirements.json"

# Cache for the requirements data
_ms_eecs_requirements: Optional[Dict[str, Any]] = None


def load_ms_eecs_requirements() -> Dict[str, Any]:
    """
    Load the M.S. EECS requirements from the JSON configuration file.
    
    Returns:
        Dict containing the full requirements structure, or empty dict if file not found.
    """
    global _ms_eecs_requirements
    
    if _ms_eecs_requirements is not None:
        return _ms_eecs_requirements
    
    if not MS_EECS_REQUIREMENTS_PATH.exists():
        logger.warning(f"MS EECS requirements file not found: {MS_EECS_REQUIREMENTS_PATH}")
        _ms_eecs_requirements = {}
        return _ms_eecs_requirements
    
    try:
        logger.info(f"Loading MS EECS requirements from {MS_EECS_REQUIREMENTS_PATH}")
        with open(MS_EECS_REQUIREMENTS_PATH, 'r', encoding='utf-8') as f:
            _ms_eecs_requirements = json.load(f)
        
        logger.info(f"Loaded MS EECS requirements for program: {_ms_eecs_requirements.get('program_name')}")
        return _ms_eecs_requirements
    except Exception as e:
        logger.error(f"Error loading MS EECS requirements: {e}")
        _ms_eecs_requirements = {}
        return _ms_eecs_requirements


def get_valid_course_codes() -> Set[str]:
    """
    Get the set of all valid course codes for the M.S. EECS program.
    
    Returns:
        Set of course codes like {"ENGR 501", "CPSC 542", ...}
    """
    requirements = load_ms_eecs_requirements()
    valid_codes = requirements.get("valid_course_codes", [])
    return set(valid_codes)


def get_spring_2026_courses() -> List[Dict[str, Any]]:
    """
    Get the list of courses available in Spring 2026 for M.S. EECS students.
    
    Returns:
        List of course dictionaries with course_code, credits, title, category, and area.
    """
    requirements = load_ms_eecs_requirements()
    spring_2026 = requirements.get("spring_2026_available_courses", {})
    return spring_2026.get("courses", [])


def get_technical_core_areas() -> Dict[str, Dict[str, Any]]:
    """
    Get the Technical Core areas and their courses.
    
    Returns:
        Dict mapping area keys to area data including name and courses list.
        Example: {"computing_systems": {"name": "Computing Systems", "courses": [...]}}
    """
    requirements = load_ms_eecs_requirements()
    tech_core = requirements.get("requirements", {}).get("technical_core", {})
    return tech_core.get("areas", {})


def get_core_courses() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get the core required courses (Ethics and Leadership).
    
    Returns:
        Dict with keys "ethics_core" and "leadership_core", each containing a list of courses.
    """
    requirements = load_ms_eecs_requirements()
    reqs = requirements.get("requirements", {})
    
    return {
        "ethics_core": reqs.get("ethics_core", {}).get("courses", []),
        "leadership_core": reqs.get("leadership_core", {}).get("courses", [])
    }


def is_eecs_program(program_name: str) -> bool:
    """
    Check if a program name matches the M.S. EECS program.
    
    Args:
        program_name: The program name to check (case-insensitive partial match)
    
    Returns:
        True if the program is M.S. EECS, False otherwise.
    """
    if not program_name:
        return False
    
    program_lower = program_name.lower()
    eecs_indicators = [
        "electrical engineering and computer science",
        "eecs",
        "m.s. in electrical",
        "ms electrical",
        "ms eecs"
    ]
    
    return any(indicator in program_lower for indicator in eecs_indicators)


def get_categorized_courses_for_eecs() -> Dict[str, List[str]]:
    """
    Get courses categorized by their requirement type for M.S. EECS.
    
    Returns:
        Dict with categories as keys and lists of course codes as values.
        Categories: "ethics_core", "leadership_core", "computing_systems",
                    "data_science_intelligent_systems", "electrical_systems", "mastery"
    """
    requirements = load_ms_eecs_requirements()
    reqs = requirements.get("requirements", {})
    
    categorized: Dict[str, List[str]] = {
        "ethics_core": [],
        "leadership_core": [],
        "computing_systems": [],
        "data_science_intelligent_systems": [],
        "electrical_systems": [],
        "mastery": []
    }
    
    # Ethics Core
    ethics = reqs.get("ethics_core", {})
    for course in ethics.get("courses", []):
        categorized["ethics_core"].append(course["course_code"])
    
    # Leadership Core
    leadership = reqs.get("leadership_core", {})
    for course in leadership.get("courses", []):
        categorized["leadership_core"].append(course["course_code"])
    
    # Technical Core areas
    tech_core = reqs.get("technical_core", {}).get("areas", {})
    for area_key, area_data in tech_core.items():
        if area_key in categorized:
            for course in area_data.get("courses", []):
                categorized[area_key].append(course["course_code"])
    
    # Mastery Demonstration
    mastery = reqs.get("mastery_demonstration", {})
    thesis_track = mastery.get("tracks", {}).get("thesis", {})
    for course in thesis_track.get("courses", []):
        categorized["mastery"].append(course["course_code"])
    
    return categorized


def get_eecs_curriculum_prompt_context() -> str:
    """
    Generate a formatted string describing the M.S. EECS curriculum for LLM prompts.
    
    This provides the LLM with accurate information about the curriculum structure
    to make informed schedule recommendations.
    
    Returns:
        A formatted string describing the EECS curriculum requirements.
    """
    requirements = load_ms_eecs_requirements()
    if not requirements:
        return ""
    
    reqs = requirements.get("requirements", {})
    
    lines = [
        "## M.S. in Electrical Engineering and Computer Science (EECS) Curriculum",
        f"Total Credits Required: {requirements.get('total_credits_required', 30)}",
        "",
        "### Ethics Core (3 credits)",
        "- ENGR 501: Ethical Foundations of Engineering (1 credit each, take 3 unique topics)",
        "",
        "### Leadership Core (6 credits)",
        "- ENGR 510: Engineering and Computational Leadership (3 credits)",
        "- ENGR 520: Technical Writing and Communication (3 credits)",
        "",
        "### Technical Core (15 credits from at least 2 of the following areas):",
        ""
    ]
    
    tech_core = reqs.get("technical_core", {}).get("areas", {})
    for area_key, area_data in tech_core.items():
        lines.append(f"**{area_data.get('name', area_key)}:**")
        for course in area_data.get("courses", [])[:5]:  # Show first 5 per area
            lines.append(f"- {course['course_code']}: {course['title']}")
        if len(area_data.get("courses", [])) > 5:
            lines.append(f"- ... and {len(area_data['courses']) - 5} more courses")
        lines.append("")
    
    lines.extend([
        "### Mastery Demonstration (6 credits)",
        "Students may choose either:",
        "- Thesis Track: ENGR 698 (6 credits)",
        "- Non-Thesis Track: 2 additional Technical Core courses (6 credits total)"
    ])
    
    return "\n".join(lines)


def get_spring_2026_eecs_courses_prompt() -> str:
    """
    Generate a formatted string listing Spring 2026 available courses for EECS students.
    
    Returns:
        A formatted string listing the Spring 2026 EECS courses.
    """
    courses = get_spring_2026_courses()
    if not courses:
        return "No Spring 2026 courses available."
    
    lines = [
        "## Spring 2026 Available Courses for M.S. EECS Students:",
        ""
    ]
    
    for course in courses:
        category = course.get("category", "").replace("_", " ").title()
        area = course.get("area", "").replace("_", " ").title()
        area_str = f" ({area})" if area else ""
        lines.append(f"- {course['course_code']}: {course['title']} ({course['credits']} cr) - {category}{area_str}")
    
    return "\n".join(lines)
