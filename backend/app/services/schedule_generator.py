import csv
import os
import json
import logging
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from openai import OpenAI

from app.services.classes_service import load_all_classes, get_classes_by_ids, validate_schedule
from app.services.degree_requirements_matcher import extract_user_requirements, enrich_classes_with_requirements
from app.services.program_evaluation_store import load_parsed_payload
from app.services.evaluation_service import load_parsed_data as load_parsed_data_from_supabase
from app.services.chat_service import get_scheduling_preferences
from app.models.schedule_types import DegreeRequirement, ClassSection

# Set up logging
logger = logging.getLogger(__name__)

# Token budget for LLM prompt (aiming for under 30,000 tokens)
MAX_TOKEN_BUDGET = 100000  # ~400,000 characters, but we'll aim much lower
MAX_CHAR_BUDGET = 100000   # Approximately 25,000 tokens
logging.basicConfig(level=logging.INFO)

# Initialize OpenAI Client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)
MODEL = os.getenv("OPENAI_MODEL", "openai/gpt-5-nano")

# Data file paths
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CLASSES_CSV_PATH = DATA_DIR / "available_classes_spring_2026.csv"
CATALOG_JSON_PATH = DATA_DIR / "chapman_catalogs_full.json"
COURSE_MAPPING_PATH = DATA_DIR / "course_to_program_mapping.json"

# Default preferences when user hasn't set any
DEFAULT_PREFERENCES = {
    "preferred_credits_min": 12,
    "preferred_credits_max": 15,
    "preferred_time_of_day": "flexible",
    "days_to_avoid": [],
    "priority_focus": "balanced",
}


# Subjects that qualify as Technical Core Electives for Engineering/CS graduate programs
TECHNICAL_CORE_ELECTIVE_SUBJECTS = {
    "CPSC", "CS", "ENGR", "EENG", "MATH", "PHYS", "DATA", "CSCE", "ECE", "EE"
}

# Cache for course-to-program mapping
_course_to_program_mapping: Optional[Dict[str, List[Dict]]] = None


def _load_course_to_program_mapping() -> Dict[str, List[Dict]]:
    """
    Load the course-to-program mapping from JSON file.
    This mapping tells us which courses are valid for which degree programs.
    Cached after first load.
    """
    global _course_to_program_mapping
    if _course_to_program_mapping is not None:
        return _course_to_program_mapping

    if not COURSE_MAPPING_PATH.exists():
        logger.warning(f"Course mapping file not found: {COURSE_MAPPING_PATH}")
        _course_to_program_mapping = {}
        return _course_to_program_mapping

    try:
        logger.info(f"Loading course-to-program mapping from {COURSE_MAPPING_PATH}")
        with open(COURSE_MAPPING_PATH, 'r', encoding='utf-8') as f:
            _course_to_program_mapping = json.load(f)

        total_courses = len(_course_to_program_mapping)
        logger.info(f"Loaded course-to-program mapping with {total_courses} courses")

        # Debug: specifically confirm that ENGR 501 is present in the mapping
        engr_501_programs = _course_to_program_mapping.get("ENGR 501")
        if engr_501_programs is not None:
            logger.info(f"ENGR 501 mapping entries: {engr_501_programs}")
        else:
            logger.warning("ENGR 501 not found in course-to-program mapping")
    except Exception as e:
        logger.error(f"Error loading course mapping: {e}")
        _course_to_program_mapping = {}

    return _course_to_program_mapping


def _is_course_valid_for_program(
    course_code: str,
    program_name: str,
    catalog_year: str = "2025-2026",
    is_graduate: bool = False
) -> Optional[Dict]:
    """
    Check if a course is valid for a given degree program.

    Args:
        course_code: Course code like "ENGR 501" or "CPSC 540"
        program_name: Degree program name like "Electrical Engineering and Computer Science, M.S."
        catalog_year: Catalog year to check (default: current year)
        is_graduate: Whether to filter for graduate catalog only

    Returns:
        Dict with program info if valid, None otherwise
    """
    mapping = _load_course_to_program_mapping()
    programs = mapping.get(course_code, [])

    for prog in programs:
        # Check if program name matches (partial match for flexibility)
        prog_name = prog.get('program', '')
        if program_name.lower() in prog_name.lower() or prog_name.lower() in program_name.lower():
            # Check catalog type if graduate filter is set
            if is_graduate and prog.get('catalog_type') != 'graduate':
                continue
            # Prefer matching year, but accept any year
            if prog.get('year') == catalog_year:
                return prog
            # Keep looking for exact year match, but remember this as fallback
            if not hasattr(_is_course_valid_for_program, '_fallback'):
                _is_course_valid_for_program._fallback = prog

    # Return fallback if we found a program match but not exact year
    fallback = getattr(_is_course_valid_for_program, '_fallback', None)
    if fallback:
        delattr(_is_course_valid_for_program, '_fallback')
        return fallback

    return None


def _get_valid_courses_for_program(
    program_name: str,
    is_graduate: bool = False,
    catalog_year: str = "2025-2026"
) -> Set[str]:
    """Get all valid course codes for a given degree program.

    Matching is done by loose substring match on program name and optional
    graduate/undergraduate flag.
    """

    if not program_name:
        logger.warning("_get_valid_courses_for_program called with empty program_name")
        return set()

    mapping = _load_course_to_program_mapping()
    valid_courses: Set[str] = set()

    logger.info(
        "Building valid course set for program '%s' (is_graduate=%s, catalog_year=%s)",
        program_name,
        is_graduate,
        catalog_year,
    )

    for course_code, programs in mapping.items():
        for prog in programs:
            prog_name = prog.get("program", "")
            # Partial match for flexibility
            if program_name.lower() in prog_name.lower() or prog_name.lower() in program_name.lower():
                if is_graduate and prog.get("catalog_type") != "graduate":
                    continue
                valid_courses.add(course_code)
                break  # Found a match, no need to check other programs for this course

    logger.info(
        "Found %d courses in mapping for program '%s'", len(valid_courses), program_name
    )
    if valid_courses:
        sample = sorted(valid_courses)[:10]
        logger.info("Sample valid courses for '%s': %s", program_name, sample)

    return valid_courses


def _extract_required_subjects(requirements: List[DegreeRequirement]) -> set:
    """
    Extract the set of subject codes that are required by degree requirements.
    Returns a set of subject codes (e.g., {'CPSC', 'MATH', 'ENGL'}).

    Special handling for "VARIOUS" subject:
    - When subject is "VARIOUS", it typically indicates an elective requirement
    - For Technical Core Electives, we expand this to include all qualifying subjects
    """
    subjects = set()
    for req in requirements:
        if req.subject:
            subject_upper = req.subject.upper()

            # Handle "VARIOUS" placeholder for elective requirements
            if subject_upper == "VARIOUS":
                # Check if this is a Technical Core Elective requirement
                label_lower = (req.label or "").lower()
                if "technical" in label_lower or "core" in label_lower or "elective" in label_lower:
                    logger.info(f"Expanding VARIOUS subject for '{req.label}' to Technical Core Elective subjects")
                    subjects.update(TECHNICAL_CORE_ELECTIVE_SUBJECTS)
                else:
                    # For other VARIOUS requirements, skip (don't add "VARIOUS" as a literal subject)
                    logger.warning(f"Skipping VARIOUS subject for requirement '{req.label}' - not recognized as Technical Core")
            else:
                subjects.add(subject_upper)
    return subjects


def _extract_required_course_codes(requirements: List[DegreeRequirement]) -> set:
    """
    Extract specific course codes (subject + number) from requirements.
    Returns a set of course codes (e.g., {'CPSC 350', 'MATH 210'}).
    """
    course_codes = set()
    for req in requirements:
        if req.subject and req.number:
            course_codes.add(f"{req.subject.upper()} {req.number}")
    return course_codes


def _is_graduate_level_course(course_number: str) -> bool:
    """
    Check if a course is graduate level (500+).
    Returns True if course number is 500 or higher.
    """
    try:
        # Extract numeric portion from course number (e.g., "501" or "101L" -> 501, 101)
        numeric_part = ''.join(c for c in str(course_number) if c.isdigit())
        if numeric_part:
            return int(numeric_part) >= 500
    except (ValueError, TypeError):
        pass
    return False


def _is_administrative_placeholder_course(cls) -> bool:
    """
    Check if a course is an administrative placeholder that shouldn't be recommended.

    These include:
    - Extended Continuous Enrollment courses (for students who need to maintain enrollment)
    - Dissertation/Thesis placeholder courses (not the actual thesis credits)
    - Courses with numbers ending in 'B' (typically administrative variants)
    """
    title_lower = (cls.title or "").lower()
    number_str = str(cls.number or "")

    # Check for administrative placeholder titles
    placeholder_keywords = [
        "extended continuous enrollment",
        "continuous enrollment",
        "extended enrollment",
    ]
    for keyword in placeholder_keywords:
        if keyword in title_lower:
            return True

    # Check for course numbers ending in 'B' (administrative variants)
    # e.g., CS-698B, CS-798B
    if number_str.endswith("B") or number_str.endswith("b"):
        return True

    return False


def _get_completed_course_codes(email: str) -> set:
    """
    Get the set of course codes (e.g., "ENGR 520") that the student has already
    completed or is currently taking. These should be excluded from recommendations.
    """
    completed_codes = set()

    # Try local file first, then Supabase
    payload = load_parsed_payload(email)
    if not payload:
        try:
            payload = load_parsed_data_from_supabase(email)
        except Exception as e:
            logger.error(f"Error loading completed courses from Supabase: {e}")
            return completed_codes

    if not payload:
        return completed_codes

    parsed_data = payload.get("parsed_data", {})
    courses = parsed_data.get("courses", {})

    # Get completed courses
    completed = courses.get("completed", [])
    for course in completed:
        subject = course.get("subject", "")
        number = course.get("number", "")
        if subject and number:
            code = f"{subject.upper()} {number}"
            completed_codes.add(code)
            logger.debug(f"Marking as completed: {code}")

    # Also exclude in-progress courses
    in_progress = courses.get("in_progress", [])
    for course in in_progress:
        subject = course.get("subject", "")
        number = course.get("number", "")
        if subject and number:
            code = f"{subject.upper()} {number}"
            completed_codes.add(code)
            logger.debug(f"Marking as in-progress: {code}")

    logger.info(f"Found {len(completed_codes)} completed/in-progress courses to exclude: {completed_codes}")
    return completed_codes


def _filter_classes_by_requirements(
    all_classes: List[ClassSection],
    requirements: List[DegreeRequirement],
    is_graduate_student: bool = False,
    completed_courses: set = None,
    program_name: str = ""
) -> List[ClassSection]:
    """
    Filter available classes to only those that could satisfy degree requirements.
    This is the intersection of required courses AND available classes.

    Args:
        all_classes: All available class sections
        requirements: Student's degree requirements
        is_graduate_student: If True, only include graduate-level courses (500+)
        completed_courses: Set of course codes (e.g., "ENGR 520") to exclude
        program_name: Student's degree program name for course-to-program mapping

    Returns a filtered list of classes that are both:
    - Required by the student's degree requirements
    - Actually available in the current class offerings
    - Appropriate for the student's academic level
    - NOT already completed or in-progress
    """
    if completed_courses is None:
        completed_courses = set()

    if not requirements:
        logger.warning("No requirements provided, returning all classes limited to 100")
        return all_classes[:100]

    required_subjects = _extract_required_subjects(requirements)
    required_course_codes = _extract_required_course_codes(requirements)

    # Get valid courses from course-to-program mapping if program name is provided
    program_valid_courses: Set[str] = set()
    if program_name:
        program_valid_courses = _get_valid_courses_for_program(
            program_name,
            is_graduate=is_graduate_student,
        )
        logger.info(
            "Program mapping filter active for '%s' with %d valid courses",
            program_name,
            len(program_valid_courses),
        )
        # Explicitly log whether ENGR 501 is considered valid for this program
        if program_valid_courses:
            logger.info(
                "ENGR 501 in program_valid_courses: %s",
                "ENGR 501" in program_valid_courses,
            )
    else:
        logger.warning(
            "Program mapping filter skipped because program_name is empty; "
            "only subject/code-based filtering will be applied."
        )

    logger.info(f"Required subjects: {required_subjects}")
    logger.info(f"Required specific courses: {list(required_course_codes)[:10]}...")
    logger.info(f"Graduate student filter: {is_graduate_student}")
    logger.info(f"Excluding {len(completed_courses)} completed/in-progress courses")

    # Filter classes that match either:
    # 1. Exact course code match (subject + number)
    # 2. Subject match for elective requirements
    # 3. Course is in the program's valid courses (from catalog mapping)
    filtered_classes = []
    excluded_count = 0
    admin_excluded_count = 0
    program_match_count = 0

    for cls in all_classes:
        course_code = f"{cls.subject} {cls.number}"

        # Skip courses already completed or in-progress
        if course_code in completed_courses:
            logger.debug(f"Excluding completed course: {course_code} ({cls.id})")
            excluded_count += 1
            continue

        # Skip administrative placeholder courses (Extended Enrollment, etc.)
        if _is_administrative_placeholder_course(cls):
            logger.debug(f"Excluding administrative placeholder: {cls.id} - {cls.title}")
            admin_excluded_count += 1
            continue

        # For graduate students, skip undergraduate courses (< 500 level)
        if is_graduate_student and not _is_graduate_level_course(cls.number):
            continue

        # Check exact course code match
        if course_code in required_course_codes:
            filtered_classes.append(cls)
            continue

        # Check subject match (for elective requirements)
        if cls.subject in required_subjects:
            filtered_classes.append(cls)
            continue

        # Check if course is in the program's valid courses from catalog mapping
        if course_code in program_valid_courses:
            filtered_classes.append(cls)
            program_match_count += 1
            continue

    logger.info(f"Filtered from {len(all_classes)} to {len(filtered_classes)} relevant classes")
    logger.info(f"  - Excluded {excluded_count} completed courses")
    logger.info(f"  - Excluded {admin_excluded_count} admin placeholders")
    logger.info(f"  - Added {program_match_count} courses via program mapping")

    # Explicitly log whether ENGR 501 made it through the filter
    eng501_in_filtered = any(f"{cls.subject} {cls.number}" == "ENGR 501" for cls in filtered_classes)
    logger.info(f"ENGR 501 present in filtered_classes: {eng501_in_filtered}")

    # Log the actual filtered classes for debugging
    if filtered_classes:
        logger.info("Filtered classes available for LLM:")
        for cls in filtered_classes[:20]:  # Log up to 20 for brevity
            logger.info(f"  - {cls.id}: {cls.code} - {cls.title} ({cls.credits} cr)")
        if len(filtered_classes) > 20:
            logger.info(f"  ... and {len(filtered_classes) - 20} more classes")

    return filtered_classes


def _build_compact_class_data(classes: List[ClassSection]) -> str:
    """
    Build a compact representation of classes for the LLM prompt.
    Uses a minimal format to reduce token count.
    """
    if not classes:
        return "No matching classes found."

    lines = ["ID | Code | Title | Credits | Days | Time"]
    lines.append("-" * 60)

    for cls in classes:
        # Create compact representation
        line = f"{cls.id} | {cls.code} | {cls.title[:40]} | {cls.credits} | {cls.display_days} | {cls.display_time}"
        lines.append(line)

    return "\n".join(lines)

def _get_user_requirements_list(email: str) -> List[Any]:
    """
    Helper to get requirements list from user's program evaluation.
    Tries local file storage first, then falls back to Supabase database.
    """
    logger.info(f"Loading degree requirements for email: {email}")

    # Try 1: Load from local file storage
    payload = load_parsed_payload(email)
    if payload:
        logger.info(f"Found local parsed payload for {email}")
        parsed_data = payload.get("parsed_data", {})
        if parsed_data:
            logger.info(f"Local parsed_data keys: {list(parsed_data.keys())}")
            requirements = extract_user_requirements(parsed_data)
            if requirements:
                logger.info(f"Extracted {len(requirements)} requirements from local file")
                return requirements
            else:
                logger.warning(f"Local parsed_data exists but no requirements extracted. Data: {list(parsed_data.keys())}")
        else:
            logger.warning(f"Local payload exists but parsed_data is empty or missing")
    else:
        logger.info(f"No local parsed payload found for {email}, trying Supabase...")

    # Try 2: Load from Supabase database
    try:
        supabase_payload = load_parsed_data_from_supabase(email)
        if supabase_payload:
            logger.info(f"Found Supabase parsed payload for {email}")
            parsed_data = supabase_payload.get("parsed_data", {})
            if parsed_data:
                logger.info(f"Supabase parsed_data keys: {list(parsed_data.keys())}")
                requirements = extract_user_requirements(parsed_data)
                if requirements:
                    logger.info(f"Extracted {len(requirements)} requirements from Supabase")
                    return requirements
                else:
                    logger.warning(f"Supabase parsed_data exists but no requirements extracted. Keys: {list(parsed_data.keys())}")
            else:
                logger.warning(f"Supabase payload exists but parsed_data is empty")
        else:
            logger.warning(f"No Supabase parsed payload found for {email}")
    except Exception as e:
        logger.error(f"Error loading from Supabase for {email}: {e}")

    logger.warning(f"No degree requirements found for {email} in any data source")
    return []


def _get_student_program_info(email: str) -> Dict[str, Any]:
    """
    Get the student's program information from their program evaluation.
    Returns a dict with program_name, degree_type, is_graduate, etc.
    """
    # Try local file first
    payload = load_parsed_payload(email)
    if not payload:
        # Fall back to Supabase
        try:
            payload = load_parsed_data_from_supabase(email)
        except Exception as e:
            logger.error(f"Error loading student info from Supabase: {e}")
            return {}

    if not payload:
        return {}

    parsed_data = payload.get("parsed_data", {})
    student_info = parsed_data.get("student_info", {})

    # Extract program name - try multiple fields
    program_name = (
        student_info.get("program_name")
        or student_info.get("major")
        or student_info.get("degree_program")
        or ""
    )

    # Extract degree type
    degree_type = student_info.get("degree_type", "").upper()

    # Determine if graduate
    class_level = student_info.get("class_level", "").lower()
    graduate_degrees = {"M.S.", "M.A.", "MBA", "PH.D.", "PHD", "ED.D.", "J.D."}
    is_graduate = "graduate" in class_level or degree_type in graduate_degrees

    logger.info(
        "Student program info for %s -> program_name='%s', degree_type='%s', class_level='%s', is_graduate=%s",
        email,
        program_name,
        degree_type,
        class_level,
        is_graduate,
    )

    # Extra debug: log which programs in the mapping mention ENGR 501
    try:
        mapping = _load_course_to_program_mapping()
        engr_501_programs = mapping.get("ENGR 501", [])
        program_names = [p.get("program", "") for p in engr_501_programs]
        logger.info("ENGR 501 is associated with programs in mapping: %s", program_names)
    except Exception as e:
        logger.error("Error while debugging ENGR 501 program associations: %s", e)

    return {
        "program_name": program_name,
        "degree_type": degree_type,
        "is_graduate": is_graduate,
        "class_level": class_level,
    }


def _is_graduate_student(email: str) -> bool:
    """
    Check if the student is a graduate student based on their program evaluation.
    Returns True if class_level is 'Graduate' or degree_type indicates graduate program.
    """
    info = _get_student_program_info(email)
    if info.get("is_graduate"):
        logger.info(f"Student {email} identified as graduate level")
        return True
    logger.info(f"Student {email} identified as undergraduate level")
    return False


def generate_schedule(user_id: str, email: str) -> Dict[str, Any]:
    """
    Generates a schedule for the user based on their requirements and preferences.
    Returns a list of class IDs.
    """
    logger.info(f"Starting schedule generation for user {user_id}, email {email}")

    # 1. Load Context with safe defaults
    user_prefs = get_scheduling_preferences(user_id) or {}
    prefs = {**DEFAULT_PREFERENCES, **user_prefs}  # Merge with defaults
    logger.info(f"User preferences: {prefs}")

    # Get student program info (includes graduate status and program name)
    student_info = _get_student_program_info(email)
    is_graduate = student_info.get("is_graduate", False)
    program_name = student_info.get("program_name", "")
    logger.info(f"Student academic level: {'Graduate' if is_graduate else 'Undergraduate'}")
    logger.info(f"Student program: {program_name or 'Unknown'}")

    # Get courses the student has already completed or is taking
    completed_courses = _get_completed_course_codes(email)

    requirements = _get_user_requirements_list(email)
    logger.info(f"Found {len(requirements)} degree requirements")
    for req in requirements:  # Log ALL requirements for debugging
        logger.info(f"  Requirement: {req.type} - {req.label} (subject={req.subject}, number={req.number}, credits={req.credits_needed})")

    all_classes = load_all_classes()
    logger.info(f"Loaded {len(all_classes)} total classes")

    if not all_classes:
        return {"error": "No classes available", "class_ids": []}

    # 2. Filter classes to those that satisfy requirements
    # If no requirements found, we'll select from all classes based on preferences
    if requirements:
        enriched_classes = enrich_classes_with_requirements(all_classes, requirements)
        candidate_classes = [c for c in enriched_classes if c.requirements_satisfied]
        logger.info(f"Found {len(candidate_classes)} classes matching degree requirements")
    else:
        # No requirements: use all classes as candidates
        logger.warning("No degree requirements found - using all classes as candidates")
        candidate_classes = all_classes

    # 3. Apply Preferences Filters (Hard/Soft)
    time_pref = prefs.get("preferred_time_of_day", "flexible")
    days_avoid = set(prefs.get("days_to_avoid") or [])

    filtered_candidates = []
    for cls in candidate_classes:
        # Skip if in avoided days
        if days_avoid and any(d in cls.display_days for d in days_avoid):
            continue
        filtered_candidates.append(cls)

    logger.info(f"After preference filtering: {len(filtered_candidates)} candidates")

    # Handle case where no candidates after filtering
    if not filtered_candidates:
        # Relax the filter - use all candidates
        logger.warning("No candidates after filtering, relaxing constraints")
        filtered_candidates = candidate_classes
    
    # If still no candidates, fall back to all classes
    if not filtered_candidates:
        filtered_candidates = all_classes[:100]  # Limit to prevent huge prompts
        
    # Group by requirement type to ensure diversity
    candidates_by_req: Dict[str, List] = {}
    for cls in filtered_candidates:
        reqs = getattr(cls, 'requirements_satisfied', []) or []
        if reqs:
            for req in reqs:
                # Handle both dict and object forms
                if isinstance(req, dict):
                    key = f"{req.get('type', 'other')}_{req.get('label', 'unknown')}"
                else:
                    key = f"{getattr(req, 'type', 'other')}_{getattr(req, 'label', 'unknown')}"
                if key not in candidates_by_req:
                    candidates_by_req[key] = []
                candidates_by_req[key].append(cls)
        else:
            # Classes without requirements go into a general bucket
            if 'general' not in candidates_by_req:
                candidates_by_req['general'] = []
            candidates_by_req['general'].append(cls)
            
    # Take top N from each requirement to keep context size down
    # Use a dict keyed by class ID to avoid duplicates (ClassSection is not hashable)
    final_candidates: Dict[str, Any] = {}
    for key, classes in candidates_by_req.items():
        # Prefer classes with professor ratings
        sorted_classes = sorted(classes, key=lambda c: c.professor_rating or 0, reverse=True)
        selected = sorted_classes[:5]  # Take top 5 options per requirement
        for c in selected:
            if c.id not in final_candidates:
                final_candidates[c.id] = c

    candidate_list = list(final_candidates.values())
    
    # Ensure we have at least some candidates
    if not candidate_list:
        candidate_list = filtered_candidates[:50]
    
    # 4. Construct Prompt
    # Serialize candidates
    candidates_json = []
    for c in candidate_list:
        # requirements_satisfied is a list of dicts from enrich_classes_with_requirements
        satisfies_labels = []
        for r in c.requirements_satisfied:
            if isinstance(r, dict):
                satisfies_labels.append(r.get('label', ''))
            else:
                satisfies_labels.append(getattr(r, 'label', ''))
        
        candidates_json.append({
            "id": c.id,
            "code": c.code,
            "title": c.title,
            "credits": c.credits,
            "days": c.display_days,
            "time": c.display_time,
            "satisfies": satisfies_labels
        })
        
    reqs_json = [{"type": r.type.value if hasattr(r.type, 'value') else r.type, "label": r.label, "credits_needed": r.credits_needed} for r in requirements]

    logger.info(f"Sending {len(candidates_json)} candidate classes to LLM")
    logger.info(f"Requirements to satisfy: {[r['label'] for r in reqs_json[:10]]}")

    # Include additional context for better schedule generation
    work_status = prefs.get('work_status', 'none')
    planning_mode = prefs.get('planning_mode', 'upcoming_semester')

    work_context = {
        'part_time': 'has a part-time job, so prefers a lighter schedule',
        'full_time': 'works full-time, needs evening/flexible classes and lighter load',
        'none': 'can focus fully on studies'
    }.get(work_status, 'can focus on studies')

    planning_context = {
        'upcoming_semester': 'planning just the next semester',
        'four_year_plan': 'building a 4-year graduation plan',
        'view_progress': 'reviewing progress and planning next steps'
    }.get(planning_mode, 'planning next semester')

    # Build optimized prompt with FILTERED class data only
    # Step 1: Filter classes to only those matching degree requirements, academic level, and not already taken
    # Also uses course-to-program mapping to include courses valid for the student's degree program
    relevant_classes = _filter_classes_by_requirements(
        all_classes,
        requirements,
        is_graduate_student=is_graduate,
        completed_courses=completed_courses,
        program_name=program_name
    )

    # Step 2: Enrich filtered classes with requirement satisfaction info
    if requirements and relevant_classes:
        relevant_classes = enrich_classes_with_requirements(relevant_classes, requirements)

    # Step 3: Build compact class data representation
    compact_class_data = _build_compact_class_data(relevant_classes)

    # Log the filtering results
    logger.info(f"Optimized: Sending {len(relevant_classes)} filtered classes (down from {len(all_classes)} total)")

    # Shuffle the classes to introduce randomness in LLM selection
    # LLMs tend to prefer items listed earlier, so shuffling helps produce variety
    shuffled_classes = list(relevant_classes)
    random.shuffle(shuffled_classes)

    # Generate a random session ID to further encourage different outputs
    session_id = random.randint(1000, 9999)
    logger.info(f"Session ID for randomization: {session_id}")

    # Build a more detailed JSON for candidates that have been enriched
    relevant_json = []
    for cls in shuffled_classes:
        satisfies_labels = []
        for r in getattr(cls, 'requirements_satisfied', []) or []:
            if isinstance(r, dict):
                satisfies_labels.append(r.get('label', ''))
            else:
                satisfies_labels.append(getattr(r, 'label', ''))

        relevant_json.append({
            "id": cls.id,
            "code": cls.code,
            "title": cls.title,
            "credits": cls.credits,
            "days": cls.display_days,
            "time": cls.display_time,
            "satisfies": satisfies_labels
        })

    min_credits = prefs.get('preferred_credits_min', 12)
    max_credits = prefs.get('preferred_credits_max', 15)

    prompt = f"""You are an expert academic schedule builder. Your task is to select classes for a student's upcoming semester.

CRITICAL RULES (MUST FOLLOW):
1. You MUST ONLY select classes from the "AVAILABLE CLASSES" list below - do not invent class IDs
2. You MUST check for TIME CONFLICTS - two classes CANNOT be on the same day at overlapping times
3. You MUST prioritize classes that satisfy the student's degree requirements
4. TOTAL CREDITS REQUIREMENT: The sum of credits MUST be at least {min_credits} and no more than {max_credits}
   - Calculate: Add up the "credits" field for each selected class
   - If total is below {min_credits}, you MUST add more classes
   - If total exceeds {max_credits}, you MUST remove classes
   - This is a HARD REQUIREMENT - do NOT return schedules outside this range

Student Profile:
- Planning Goal: {planning_context}
- Work Status: Student {work_context}
- Time Preference: {time_pref} classes preferred
- Days to Avoid: {', '.join(days_avoid) if days_avoid else 'None'}
- Priority Focus: {prefs.get('priority_focus', 'balanced')}
- REQUIRED Total Credits: {min_credits}-{max_credits}

Student's Remaining Degree Requirements:
{json.dumps(reqs_json, indent=2)}

=== AVAILABLE CLASSES (Pre-filtered to match requirements) - Spring 2026 ===
These classes have been pre-filtered to only include courses relevant to the student's degree requirements.
The "satisfies" field shows which requirements each class fulfills.

{json.dumps(relevant_json, indent=2)}

=== END OF CLASS DATA ===

TIME CONFLICT CHECK:
Before selecting a class, verify it does not conflict with already selected classes:
- Parse the "days" field (e.g., "MWF" or "TuTh")
- Parse the "time" field (e.g., "10:00am - 10:50am")
- If two classes share any day AND their times overlap, they CONFLICT

SELECTION PROCESS:
1. Review the student's remaining degree requirements above
2. Select classes from the AVAILABLE CLASSES list that satisfy those requirements
3. The "satisfies" field tells you which requirements each class fulfills - prioritize classes with matches
4. If the requirements imply a graduate student (500+ level courses needed), ONLY select 500+ level courses
5. Select a diverse set of requirement-satisfying classes without time conflicts
6. IMPORTANT: Keep adding classes until total credits reach at least {min_credits}
7. VERIFY: Before returning, sum up all selected class credits and ensure total is between {min_credits}-{max_credits}
8. Prefer classes matching time preferences if possible

VARIETY (Session #{session_id}): This is generation session #{session_id}. You MUST produce a DIFFERENT schedule than previous sessions.
- When multiple ENGR 698 sections exist, pick DIFFERENT section numbers each time (e.g., -01, -02, -03, -04, -05)
- When multiple Technical Core Electives exist (EENG-511, EENG-514, CS-533, CS-770, CPSC-543), pick DIFFERENT ones each time
- Do NOT always pick the same combination - variety is required
- Consider the classes in the order listed - they have been randomized for you

Return ONLY a JSON object: {{"class_ids": ["SUBJ-NUM-SEC", ...]}}
The IDs must be formatted with dashes (e.g., "CPSC-350-01").

FINAL CHECK: Verify your selection has {min_credits}-{max_credits} total credits before responding."""

    # Check prompt size and warn if still too large
    prompt_chars = len(prompt)
    estimated_tokens = prompt_chars // 4
    logger.info(f"Optimized prompt size: {prompt_chars} chars (~{estimated_tokens} tokens)")

    if prompt_chars > MAX_CHAR_BUDGET:
        logger.warning(f"Prompt exceeds budget of {MAX_CHAR_BUDGET} chars. Consider further filtering.")

    # 5. Call LLM
    try:
        logger.info(f"Calling LLM for schedule generation... Using model: {MODEL}")

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": f"You are a schedule builder API. Return only valid JSON with class_ids array. This is session #{session_id} - you MUST produce a DIFFERENT valid schedule than previous sessions by randomly choosing between equally valid options."},
                {"role": "user", "content": prompt}
            ],
            temperature=1.0,  # Maximum temperature for maximum variety in schedule recommendations
            response_format={"type": "json_object"},
            timeout=120.0,  # Add explicit timeout to prevent hanging
            stream=False  # Explicitly disable streaming to ensure we get a complete response
        )

        # Log immediately after response received
        logger.info("LLM API call completed, processing response...")

        # Log response type and basic info first (in case full log hangs)
        logger.info(f"Response type: {type(response)}")

        # Check if response exists
        if response is None:
            logger.error("LLM returned None response")
            return {"error": "LLM returned None response", "class_ids": []}

        # Log choices existence
        logger.info(f"Response has choices: {hasattr(response, 'choices')}, choices value: {response.choices if hasattr(response, 'choices') else 'N/A'}")

        # Handle potential empty response
        if not response.choices:
            logger.error(f"LLM returned no choices - response: {response}")
            return {"error": "LLM returned empty response - prompt may exceed context limit", "class_ids": []}

        # Log first choice
        first_choice = response.choices[0]
        logger.info(f"First choice type: {type(first_choice)}")
        logger.info(f"First choice message: {first_choice.message if hasattr(first_choice, 'message') else 'N/A'}")

        content = first_choice.message.content
        if not content:
            logger.error(f"LLM returned empty content. Full response: {response}")
            return {"error": "LLM returned empty content", "class_ids": []}

        logger.info(f"LLM response content: {content[:500]}...")  # Log first 500 chars

        result = json.loads(content)
        selected_ids = result.get("class_ids", [])
        logger.info(f"LLM selected {len(selected_ids)} classes: {selected_ids}")

        # 6. Validate - ensure IDs exist in our data
        relevant_id_set = {c.id for c in relevant_classes}
        all_class_id_set = {c.id for c in all_classes}

        valid_ids = []
        for cid in selected_ids:
            if cid in relevant_id_set or cid in all_class_id_set:
                valid_ids.append(cid)
            else:
                logger.warning(f"Discarding invalid class ID from LLM: {cid}")

        if not valid_ids:
            logger.error(f"No valid class IDs from LLM response. Original: {selected_ids}")
            return {"error": "LLM returned no valid class IDs", "class_ids": []}

        # 7. Validate for time conflicts and remove conflicting classes
        valid_ids = _remove_conflicts(valid_ids, all_classes)
        logger.info(f"After conflict removal: {len(valid_ids)} classes: {valid_ids}")

        return {"class_ids": valid_ids}

    except json.JSONDecodeError as e:
        logger.error(f"Schedule Generation JSON Error: {e}")
        return {"error": "Failed to parse AI response", "class_ids": []}
    except AttributeError as e:
        logger.error(f"Schedule Generation AttributeError - unexpected response structure: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Unexpected LLM response format: {e}", "class_ids": []}
    except TimeoutError as e:
        logger.error(f"Schedule Generation Timeout: {e}")
        return {"error": "LLM request timed out", "class_ids": []}
    except Exception as e:
        logger.error(f"Schedule Generation Error ({type(e).__name__}): {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "class_ids": []}


def _remove_conflicts(class_ids: List[str], all_classes: List[Any]) -> List[str]:
    """
    Remove conflicting classes from the list, keeping the first occurrence.
    Returns a list of class IDs with no time conflicts.
    """
    if len(class_ids) <= 1:
        return class_ids

    # Build a map of class ID to class object
    class_map = {c.id: c for c in all_classes}

    valid_ids = []
    selected_classes = []

    for cid in class_ids:
        if cid not in class_map:
            continue

        candidate = class_map[cid]
        has_conflict = False

        # Check against all already-selected classes
        for selected in selected_classes:
            if candidate.has_conflict_with(selected):
                logger.warning(f"Removing {cid} due to conflict with {selected.id}")
                has_conflict = True
                break

        if not has_conflict:
            valid_ids.append(cid)
            selected_classes.append(candidate)

    return valid_ids

