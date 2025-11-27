import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, IO

from pypdf import PdfReader

COURSE_LINE_START = re.compile(
    r"^(Fall|Spring|Spr|Summer|Winter)\s+\d{4}\s+[A-Z]{2,5}\b"
)
COURSE_PATTERN = re.compile(
    r"(?P<term>(Fall|Spring|Spr|Summer|Winter)\s+\d{4})\s+"
    r"(?P<subject>[A-Z]{2,5})\s+"
    r"(?P<number>\d{3}[A-Z]?)\s+"
    r"(?P<title>.+?)\s+"
    r"(?:(?P<grade>[A-F][+-]?|IP|CR|P|NP|TI)\s+)?"
    r"(?P<credits>\d+\.\d{2})"
    r"(?:\s+(?P<course_type>[A-Z]{2,3}|IP))?$"
)
CREDIT_LINE_PATTERN = re.compile(
    r"Credits:\s*(?P<required>\d+\.\d+)\s*required,\s*"
    r"(?P<earned>\d+\.\d+)\s*earned,\s*"
    r"(?P<in_progress>\d+\.\d+)\s*in progress,\s*"
    r"(?P<needed>\d+\.\d+)\s*needed",
    flags=re.IGNORECASE,
)
GPA_LINE_PATTERN = re.compile(
    r"GPA:\s*(?P<required>\d+\.\d+)\s*required,\s*(?P<completed>\d+\.\d+)\s*(?:completed|earned)",
    flags=re.IGNORECASE,
)


def extract_text_from_pdf(file_source: Union[str, IO]) -> str:
    reader = PdfReader(file_source)
    text_parts: List[str] = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def _split_lines(text: str) -> List[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _looks_like_heading(line: str) -> bool:
    if not line:
        return False
    if line.isupper():
        return True
    if re.match(r"^[A-Z].*\[RQ\s*\d+\]$", line):
        return True
    if line.startswith(("Option", "Minimum", "MASTER", "GRADUATE")):
        return True
    return False


def _parse_student_info(lines: List[str], text: str) -> Dict[str, Any]:
    info: Dict[str, Any] = {}

    combined_line = next((line for line in lines if " - " in line), "")
    match = re.search(r"(?P<name>[A-Za-z,\s]+)\s+-\s+(?P<id>\d+)", combined_line)
    if match:
        info["name"] = match.group("name").strip()
        info["id"] = match.group("id").strip()

    name_match = re.search(r"Name:\s*(.+)", text)
    if name_match and "name" not in info:
        info["name"] = name_match.group(1).strip()

    id_match = re.search(r"ID:\s*([A-Za-z0-9]+)", text)
    if id_match and "id" not in info:
        info["id"] = id_match.group(1).strip()

    exp_grad_match = re.search(
        r"Exp Grad Term:\s*(?P<grad>.+?)\s+Catalog Year:\s*(?P<catalog>.+)",
        text,
    )
    if exp_grad_match:
        info["expected_graduation_term"] = exp_grad_match.group("grad").strip()
        info["catalog_year"] = exp_grad_match.group("catalog").strip()

    catalog_match = re.search(r"Catalog Year:\s*(.+)", text)
    if catalog_match and "catalog_year" not in info:
        info["catalog_year"] = catalog_match.group(1).strip()

    program_match = re.search(r"Program:\s*(.+)", text)
    if program_match:
        info["program"] = program_match.group(1).strip()

    return info


def _coalesce_course_lines(lines: List[str]) -> List[str]:
    aggregated: List[str] = []
    buffer: Optional[str] = None

    for line in lines:
        if COURSE_LINE_START.match(line):
            if buffer:
                aggregated.append(buffer.strip())
            buffer = line
            continue

        if buffer:
            buffer = f"{buffer} {line}"
            if re.search(r"\d+\.\d{2}\s+[A-Z]{2,3}$", buffer) or re.search(
                r"\d+\.\d{2}\s+IP$", buffer
            ):
                aggregated.append(buffer.strip())
                buffer = None

    if buffer:
        aggregated.append(buffer.strip())

    return aggregated


def _parse_courses(lines: List[str]) -> List[Dict[str, Any]]:
    courses: List[Dict[str, Any]] = []
    seen_keys = set()

    def add_course(entry: Dict[str, str]) -> None:
        course = {
            "term": entry.get("term"),
            "subject": entry.get("subject"),
            "number": entry.get("number"),
            "title": (entry.get("title") or "").strip(),
            "grade": entry.get("grade") or None,
            "credits": float(entry.get("credits") or 0),
            "type": entry.get("course_type") or None,
        }
        key = (
            course["term"],
            course["subject"],
            course["number"],
            course["title"],
            course["grade"],
            course["credits"],
            course["type"],
        )
        if key not in seen_keys:
            seen_keys.add(key)
            courses.append(course)

    for course_line in _coalesce_course_lines(lines):
        match = COURSE_PATTERN.match(course_line)
        if match:
            add_course(match.groupdict())

    for line in lines:
        match = COURSE_PATTERN.match(line)
        if match:
            add_course(match.groupdict())

    return courses


def _parse_credit_requirements(lines: List[str]) -> List[Dict[str, Any]]:
    requirements: List[Dict[str, Any]] = []
    current_heading: Optional[str] = None

    for line in lines:
        if _looks_like_heading(line):
            current_heading = line
            continue

        match = CREDIT_LINE_PATTERN.search(line)
        if match:
            requirements.append(
                {
                    "label": current_heading or "General",
                    "required": float(match.group("required")),
                    "earned": float(match.group("earned")),
                    "in_progress": float(match.group("in_progress")),
                    "needed": float(match.group("needed")),
                }
            )
    return requirements


def _compute_overall_gpa_from_courses(courses: List[Dict[str, Any]]) -> Optional[float]:
    """Fallback overall GPA computed directly from completed courses.

    Uses the same 4.0 scale mapping as the frontend GPA trend chart.
    Returns None if there are no graded, credit-bearing courses.
    """

    grade_points: Dict[str, float] = {
        "A+": 4.0,
        "A": 4.0,
        "A-": 3.7,
        "B+": 3.3,
        "B": 3.0,
        "B-": 2.7,
        "C+": 2.3,
        "C": 2.0,
        "C-": 1.7,
        "D+": 1.3,
        "D": 1.0,
        "D-": 0.7,
        "F": 0.0,
    }

    total_points = 0.0
    total_credits = 0.0

    for course in courses:
        grade = course.get("grade")
        credits = float(course.get("credits") or 0)
        if not grade or grade not in grade_points or credits <= 0:
            continue
        total_points += grade_points[grade] * credits
        total_credits += credits

    if total_credits <= 0:
        return None

    return total_points / total_credits


def _parse_gpa(lines: List[str], text: str, courses: List[Dict[str, Any]]) -> Dict[str, Any]:
    gpa: Dict[str, Any] = {}

    overall_match = re.search(r"Overall GPA[:\s]*([\d\.]+)", text)
    if overall_match:
        gpa["overall"] = float(overall_match.group(1))

    major_match = re.search(r"Major GPA[:\s]*([\d\.]+)", text)
    if major_match:
        gpa["major"] = float(major_match.group(1))

    current_heading: Optional[str] = None
    for line in lines:
        if _looks_like_heading(line):
            current_heading = line
            continue
        gpa_line = GPA_LINE_PATTERN.search(line)
        if gpa_line:
            completed = float(gpa_line.group("completed"))
            if current_heading and "Major GPA" in current_heading:
                gpa["major"] = completed
            elif "Cumulative GPA" in (current_heading or ""):
                gpa["overall"] = completed
            elif "overall" not in gpa:
                gpa["overall"] = completed

    # Fallback: if we still don't have an overall GPA, derive it directly
    # from the completed course list so the dashboard always has a value.
    if "overall" not in gpa:
        computed_overall = _compute_overall_gpa_from_courses(courses)
        if computed_overall is not None:
            gpa["overall"] = computed_overall

    return gpa


def parse_program_evaluation(file_source: Union[str, IO]) -> Dict[str, Any]:
    text = extract_text_from_pdf(file_source)
    lines = _split_lines(text)

    student_info = _parse_student_info(lines, text)
    courses = _parse_courses(lines)
    credit_requirements = _parse_credit_requirements(lines)
    gpa = _parse_gpa(lines, text, courses)

    mastery: Dict[str, str] = {}
    if "Thesis Defense" in text:
        mastery["type"] = "Thesis"
    elif "Capstone Project" in text:
        mastery["type"] = "Project"

    return {
        "student_info": student_info,
        "gpa": gpa,
        "courses": {
            "all_found": courses,
            "in_progress": [
                course
                for course in courses
                if course.get("grade") == "IP" or course.get("type") == "IP"
            ],
            "completed": [
                course
                for course in courses
                if course.get("grade") not in (None, "", "IP")
            ],
        },
        "credit_requirements": credit_requirements,
        "mastery_demonstration": mastery,
        "metadata": {
            "parsed_at": datetime.now(timezone.utc).isoformat(),
            "source_length": len(text),
        },
    }
