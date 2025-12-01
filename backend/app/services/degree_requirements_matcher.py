"""
Degree Requirements Matcher - Matches available classes against user's degree requirements.
This service extracts remaining requirements from parsed program evaluations and
matches them against available classes to show relevant badges.
"""
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.models.schedule_types import (
    ClassSection,
    DegreeRequirement,
    RequirementBadge,
    RequirementType,
    REQUIREMENT_COLORS,
)
from app.services.ms_eecs_requirements import (
    is_eecs_program,
    get_categorized_courses_for_eecs,
    get_valid_course_codes as get_eecs_valid_courses,
)


# Common GE area mappings based on Chapman's curriculum
# Maps course prefixes/numbers to GE areas they typically satisfy
GE_AREA_MAPPINGS = {
    "Written Inquiry": {
        "prefixes": ["ENG"],
        "courses": ["ENG 103", "ENG 104", "ENG 105"],
    },
    "Quantitative Inquiry": {
        "prefixes": ["MATH"],
        "courses": ["MATH 101", "MATH 110", "MATH 111", "MATH 150"],
    },
    "Scientific Inquiry": {
        "prefixes": ["BIOL", "CHEM", "PHYS", "ENV"],
        "courses": [],
    },
    "Social Inquiry": {
        "prefixes": ["SOC", "PSY", "POLS", "ECON", "ANTH"],
        "courses": [],
    },
    "Values and Ethical Inquiry": {
        "prefixes": ["PHIL", "REL"],
        "courses": [],
    },
    "Artistic Inquiry": {
        "prefixes": ["ART", "MUS", "DANC", "FTV", "THTR"],
        "courses": [],
    },
    "Global Perspectives": {
        "prefixes": ["HIST", "GS"],
        "courses": [],
    },
}

# M.S. EECS Requirement Category Mappings
EECS_CATEGORY_LABELS = {
    "ethics_core": ("Ethics Core", RequirementType.MAJOR_CORE),
    "leadership_core": ("Leadership Core", RequirementType.MAJOR_CORE),
    "computing_systems": ("Technical Core - Computing Systems", RequirementType.MAJOR_ELECTIVE),
    "data_science_intelligent_systems": ("Technical Core - Data Science & AI", RequirementType.MAJOR_ELECTIVE),
    "electrical_systems": ("Technical Core - Electrical Systems", RequirementType.MAJOR_ELECTIVE),
    "mastery": ("Mastery Demonstration", RequirementType.MAJOR_CORE),
}


def get_eecs_requirement_badge(course_code: str) -> Optional[RequirementBadge]:
    """
    Get a requirement badge for an EECS curriculum course.
    
    Args:
        course_code: Course code like "CPSC 542" or "ENGR 501"
    
    Returns:
        RequirementBadge if the course is part of EECS curriculum, None otherwise
    """
    categorized = get_categorized_courses_for_eecs()
    
    for category_key, course_codes in categorized.items():
        if course_code in course_codes:
            label, req_type = EECS_CATEGORY_LABELS.get(category_key, ("EECS Elective", RequirementType.MAJOR_ELECTIVE))
            
            # Generate short label based on category
            if "ethics" in category_key:
                short_label = "Ethics"
            elif "leadership" in category_key:
                short_label = "Lead"
            elif "computing" in category_key:
                short_label = "Tech-CS"
            elif "data_science" in category_key:
                short_label = "Tech-DS"
            elif "electrical" in category_key:
                short_label = "Tech-EE"
            elif "mastery" in category_key:
                short_label = "Thesis"
            else:
                short_label = "EECS"
            
            return RequirementBadge(
                type=req_type,
                label=label,
                short_label=short_label,
                color=REQUIREMENT_COLORS.get(req_type, "gray"),
            )
    
    return None


def get_eecs_degree_requirements() -> List[DegreeRequirement]:
    """
    Get the M.S. EECS curriculum requirements as DegreeRequirement objects.
    This allows the View Impact modal to properly show progress for EECS students.
    
    Returns:
        List of DegreeRequirement objects for the EECS curriculum.
    """
    from app.services.ms_eecs_requirements import load_ms_eecs_requirements
    
    requirements = []
    eecs_data = load_ms_eecs_requirements()
    reqs = eecs_data.get("requirements", {})
    
    # Ethics Core - 3 credits
    ethics = reqs.get("ethics_core", {})
    if ethics:
        requirements.append(DegreeRequirement(
            type=RequirementType.MAJOR_CORE,
            label="Ethics Core",
            credits_needed=float(ethics.get("credits_required", 3)),
        ))
    
    # Leadership Core - 6 credits
    leadership = reqs.get("leadership_core", {})
    if leadership:
        requirements.append(DegreeRequirement(
            type=RequirementType.MAJOR_CORE,
            label="Leadership Core",
            credits_needed=float(leadership.get("credits_required", 6)),
        ))
    
    # Technical Core areas - 15 credits total, from any of the three areas
    tech_core = reqs.get("technical_core", {})
    if tech_core:
        areas = tech_core.get("areas", {})
        
        # Computing Systems
        if "computing_systems" in areas:
            requirements.append(DegreeRequirement(
                type=RequirementType.MAJOR_ELECTIVE,
                label="Technical Core - Computing Systems",
                credits_needed=float(areas["computing_systems"].get("credits_per_course", 3)),
            ))
        
        # Data Science & Intelligent Systems
        if "data_science_intelligent_systems" in areas:
            requirements.append(DegreeRequirement(
                type=RequirementType.MAJOR_ELECTIVE,
                label="Technical Core - Data Science & AI",
                credits_needed=float(areas["data_science_intelligent_systems"].get("credits_per_course", 3)),
            ))
        
        # Electrical Systems
        if "electrical_systems" in areas:
            requirements.append(DegreeRequirement(
                type=RequirementType.MAJOR_ELECTIVE,
                label="Technical Core - Electrical Systems",
                credits_needed=float(areas["electrical_systems"].get("credits_per_course", 3)),
            ))
    
    # Mastery Demonstration - 6 credits
    mastery = reqs.get("mastery_demonstration", {})
    if mastery:
        requirements.append(DegreeRequirement(
            type=RequirementType.MAJOR_CORE,
            label="Mastery Demonstration",
            credits_needed=float(mastery.get("credits_required", 6)),
        ))
    
    return requirements


def _normalize_course_code(code: str) -> Tuple[str, str]:
    """
    Normalize a course code into (subject, number) tuple.
    Handles formats like 'CPSC 350', 'CPSC350', 'CPSC 350-01'.
    """
    # Remove section numbers
    code = re.sub(r"[-_]\d+$", "", code.strip())
    
    # Try to split by space or find the boundary
    match = re.match(r"([A-Z]+)\s*(\d+[A-Z]?)", code.upper())
    if match:
        return match.group(1), match.group(2)
    
    return code.upper(), ""


def _extract_requirements_from_remaining_courses(
    remaining_courses: List[Dict[str, Any]]
) -> List[DegreeRequirement]:
    """
    Extract DegreeRequirement objects from the remaining_required courses list.
    Handles various formats of course data from the program evaluation PDF parser.
    """
    requirements = []
    
    for course in remaining_courses:
        subject = (course.get("subject") or "").strip().upper()
        number = (course.get("number") or "").strip()
        title = (course.get("title") or "").strip()
        req_type_str = (course.get("requirement_type") or course.get("requirement_satisfied") or "other").lower()
        credits = float(course.get("credits", 0) or 0)
        
        # Map requirement type string to enum
        if "core" in req_type_str or "major core" in req_type_str or "required" in req_type_str:
            req_type = RequirementType.MAJOR_CORE
        elif "elective" in req_type_str or "major elective" in req_type_str or "technical" in req_type_str:
            req_type = RequirementType.MAJOR_ELECTIVE
        elif "ge" in req_type_str or "general" in req_type_str or "inquiry" in req_type_str:
            req_type = RequirementType.GENERAL_EDUCATION
        elif "minor" in req_type_str:
            req_type = RequirementType.MINOR
        elif "concentration" in req_type_str:
            req_type = RequirementType.CONCENTRATION
        else:
            req_type = RequirementType.OTHER
        
        # Create a descriptive label
        if subject and number:
            label = f"{subject} {number}"
        elif subject:
            label = f"{subject} Elective" if "elective" in req_type_str else subject
        elif title:
            label = title
        else:
            label = "Required Course"
        
        requirements.append(DegreeRequirement(
            type=req_type,
            label=label,
            subject=subject if subject else None,
            number=number if number else None,
            title=title if title else None,
            credits_needed=credits,
        ))
    
    return requirements


def _extract_ge_requirements(degree_requirements: Dict[str, Any]) -> List[DegreeRequirement]:
    """
    Extract GE area requirements from degree_requirements.general_education.
    """
    requirements = []
    
    ge_data = degree_requirements.get("general_education", {})
    areas = ge_data.get("areas", [])
    
    for area in areas:
        name = area.get("name", "")
        status = area.get("status", "")
        required = float(area.get("required", 0) or 0)
        earned = float(area.get("earned", 0) or 0)
        
        # Only include areas that are still needed
        if status in ("needed", "in_progress") or earned < required:
            requirements.append(DegreeRequirement(
                type=RequirementType.GENERAL_EDUCATION,
                label=name,
                area=name,
                credits_needed=max(0, required - earned),
            ))
    
    return requirements


def extract_user_requirements(parsed_evaluation: Dict[str, Any]) -> List[DegreeRequirement]:
    """
    Extract all remaining degree requirements from a parsed program evaluation.
    
    Args:
        parsed_evaluation: The parsed_data from a program evaluation
    
    Returns:
        List of DegreeRequirement objects
    """
    requirements: List[DegreeRequirement] = []
    
    # Get courses data
    courses = parsed_evaluation.get("courses", {})
    remaining_required = courses.get("remaining_required", [])
    
    # Extract requirements from remaining_required courses
    requirements.extend(_extract_requirements_from_remaining_courses(remaining_required))
    
    # Extract GE requirements
    degree_reqs = parsed_evaluation.get("degree_requirements", {})
    requirements.extend(_extract_ge_requirements(degree_reqs))
    
    # Extract from credit_requirements for any areas with needed credits
    credit_reqs = parsed_evaluation.get("credit_requirements", [])
    for cr in credit_reqs:
        label = cr.get("label", "")
        needed = float(cr.get("needed", 0) or 0)
        
        if needed > 0 and "elective" in label.lower():
            # This is likely an elective requirement
            subject_match = re.match(r"([A-Z]+)", label)
            subject = subject_match.group(1) if subject_match else None
            
            requirements.append(DegreeRequirement(
                type=RequirementType.MAJOR_ELECTIVE,
                label=f"{label} Elective",
                subject=subject,
                credits_needed=needed,
            ))
    
    # Extract from additional_programs (minors, concentrations)
    additional = parsed_evaluation.get("additional_programs", [])
    for prog in additional:
        prog_type = prog.get("type", "").lower()
        name = prog.get("name", "")
        status = prog.get("status", "")
        
        if status == "in_progress":
            if "minor" in prog_type:
                req_type = RequirementType.MINOR
            elif "concentration" in prog_type:
                req_type = RequirementType.CONCENTRATION
            else:
                req_type = RequirementType.OTHER
            
            requirements.append(DegreeRequirement(
                type=req_type,
                label=name,
                credits_needed=float(prog.get("credits_required", 0) or 0) - float(prog.get("credits_earned", 0) or 0),
            ))
    
    return requirements


def _get_short_label(req_type: RequirementType, label: str) -> str:
    """Get a short label for display in badges."""
    if req_type == RequirementType.MAJOR_CORE:
        return "Core"
    elif req_type == RequirementType.MAJOR_ELECTIVE:
        return "Elective"
    elif req_type == RequirementType.GENERAL_EDUCATION:
        # Create abbreviated GE labels
        if "written" in label.lower():
            return "GE-WI"
        elif "quantitative" in label.lower():
            return "GE-QI"
        elif "scientific" in label.lower():
            return "GE-SI"
        elif "social" in label.lower():
            return "GE-SoI"
        elif "values" in label.lower() or "ethical" in label.lower():
            return "GE-VEI"
        elif "artistic" in label.lower():
            return "GE-AI"
        elif "global" in label.lower():
            return "GE-GP"
        else:
            return "GE"
    elif req_type == RequirementType.MINOR:
        return "Minor"
    elif req_type == RequirementType.CONCENTRATION:
        return "Conc"
    else:
        return "Req"


def _is_ge_course(subject: str, number: str, ge_area: str) -> bool:
    """
    Check if a course satisfies a particular GE area.
    Uses the GE_AREA_MAPPINGS lookup table.
    """
    area_data = GE_AREA_MAPPINGS.get(ge_area, {})
    prefixes = area_data.get("prefixes", [])
    specific_courses = area_data.get("courses", [])
    
    # Check specific courses first
    course_code = f"{subject} {number}"
    if course_code in specific_courses:
        return True
    
    # Check subject prefix
    if subject in prefixes:
        return True
    
    return False


def match_class_to_requirements(
    class_section: ClassSection,
    requirements: List[DegreeRequirement]
) -> List[RequirementBadge]:
    """
    Match a class section against degree requirements.
    
    Args:
        class_section: The class to check
        requirements: List of user's remaining requirements
    
    Returns:
        List of RequirementBadge objects for matching requirements
    """
    badges: List[RequirementBadge] = []
    seen_labels: Set[str] = set()
    
    class_subject = class_section.subject
    class_number = class_section.number
    class_title_lower = class_section.title.lower()
    class_credits = class_section.credits
    
    # Parse class number for level comparisons
    try:
        class_num_val = int(class_number.rstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
    except (ValueError, AttributeError):
        class_num_val = 0
    
    for req in requirements:
        # Skip if we already have a badge for this label
        if req.label in seen_labels:
            continue
        
        matched = False
        
        # Direct course match (exact subject and number)
        if req.subject and req.number:
            # Exact match
            if class_subject == req.subject and class_number == req.number:
                matched = True
            # Handle number variants (e.g., "350" matching "350L")
            elif class_subject == req.subject:
                try:
                    req_num_val = int(req.number.rstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
                    if class_num_val == req_num_val:
                        matched = True
                except (ValueError, AttributeError):
                    pass
        
        # Subject-only match with title hints
        elif req.subject and not req.number and req.title:
            if class_subject == req.subject:
                # Check if titles are similar
                req_title_lower = req.title.lower()
                if req_title_lower in class_title_lower or class_title_lower in req_title_lower:
                    matched = True
                # Also match if credits align with requirement
                elif req.credits_needed > 0 and class_credits == req.credits_needed:
                    matched = True
        
        # GE area match
        elif req.type == RequirementType.GENERAL_EDUCATION and req.area:
            if _is_ge_course(class_subject, class_number, req.area):
                matched = True
        
        # Major elective match (same subject, appropriate level)
        elif req.type == RequirementType.MAJOR_ELECTIVE and req.subject:
            if class_subject == req.subject:
                # Check for graduate requirement indicators
                is_grad_req = (
                    "graduate" in req.label.lower() or 
                    "500" in req.label or
                    "grad" in req.label.lower() or
                    "ms " in req.label.lower() or
                    "m.s." in req.label.lower()
                )
                
                if is_grad_req:
                    # Graduate courses are 500+
                    if class_num_val >= 500:
                        matched = True
                else:
                    # Upper division courses are typically 300+
                    if class_num_val >= 300:
                        matched = True
        
        # Major core match (same subject, check level for grad programs)
        elif req.type == RequirementType.MAJOR_CORE and req.subject:
            if class_subject == req.subject:
                # Check for graduate requirement indicators
                is_grad_req = (
                    "graduate" in req.label.lower() or 
                    "500" in req.label or
                    "grad" in req.label.lower() or
                    "ms " in req.label.lower() or
                    "m.s." in req.label.lower()
                )
                
                if is_grad_req:
                    # Graduate courses are 500+
                    if class_num_val >= 500:
                        matched = True
                else:
                    # Any matching subject works for undergrad
                    matched = True
        
        # Subject-only match for electives (no specific number required)
        elif req.subject and not req.number:
            if class_subject == req.subject:
                # Check course level for graduate requirements
                is_grad_req = (
                    "graduate" in req.label.lower() or 
                    "500" in req.label or
                    "grad" in req.label.lower()
                )
                
                if is_grad_req:
                    if class_num_val >= 500:
                        matched = True
                else:
                    matched = True
        
        # Title-based fuzzy match (for courses without specific subject/number)
        elif req.title and not req.subject:
            req_title_lower = req.title.lower()
            # Check for significant word overlap
            req_words = set(req_title_lower.split())
            class_words = set(class_title_lower.split())
            # Remove common words
            common_ignore = {'and', 'or', 'the', 'a', 'an', 'in', 'of', 'for', 'to', 'i', 'ii', 'iii'}
            req_words -= common_ignore
            class_words -= common_ignore
            
            if req_words and class_words:
                overlap = req_words & class_words
                if len(overlap) >= 1 and len(overlap) / len(req_words) >= 0.5:
                    matched = True
        
        if matched:
            seen_labels.add(req.label)
            badges.append(RequirementBadge(
                type=req.type,
                label=req.label,
                short_label=_get_short_label(req.type, req.label),
                color=REQUIREMENT_COLORS.get(req.type, "gray"),
            ))
    
    return badges


def enrich_classes_with_requirements(
    classes: List[ClassSection],
    requirements: List[DegreeRequirement]
) -> List[ClassSection]:
    """
    Enrich a list of classes with requirement satisfaction information.
    Modifies classes in-place and returns them.
    
    Args:
        classes: List of classes to enrich
        requirements: User's remaining requirements
    
    Returns:
        List of classes with requirements_satisfied field populated
    """
    for cls in classes:
        badges = match_class_to_requirements(cls, requirements)
        cls.requirements_satisfied = [badge.to_dict() for badge in badges]
    
    return classes


def enrich_classes_with_eecs_requirements(
    classes: List[ClassSection],
    program_name: Optional[str] = None,
) -> List[ClassSection]:
    """
    Enrich a list of classes with EECS-specific requirement badges.
    This should be called for M.S. EECS students to show how courses
    map to curriculum areas like Ethics Core, Leadership Core, Technical Core.
    
    Args:
        classes: List of classes to enrich
        program_name: The program name (to verify EECS)
    
    Returns:
        List of classes with requirements_satisfied field populated
    """
    # Only apply EECS badges for EECS program
    if program_name and not is_eecs_program(program_name):
        return classes
    
    for cls in classes:
        course_code = f"{cls.subject} {cls.number}"
        badge = get_eecs_requirement_badge(course_code)
        
        if badge:
            # Add to existing badges or create new list
            if cls.requirements_satisfied:
                # Check if badge already exists
                existing_labels = {b.get("label") for b in cls.requirements_satisfied}
                if badge.label not in existing_labels:
                    cls.requirements_satisfied.append(badge.to_dict())
            else:
                cls.requirements_satisfied = [badge.to_dict()]
    
    return classes


def get_requirement_summary(requirements: List[DegreeRequirement]) -> Dict[str, Any]:
    """
    Get a summary of requirements for display.
    
    Args:
        requirements: List of requirements
    
    Returns:
        Summary dictionary with counts by type
    """
    summary = {
        "total": len(requirements),
        "byType": {},
        "requirements": [req.to_dict() for req in requirements],
    }
    
    for req in requirements:
        type_name = req.type.value
        if type_name not in summary["byType"]:
            summary["byType"][type_name] = 0
        summary["byType"][type_name] += 1
    
    return summary
