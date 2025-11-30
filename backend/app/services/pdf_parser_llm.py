import json
import os
import re
from typing import Any, Dict, List, Union, IO, Optional

from pypdf import PdfReader
from openai import OpenAI

def extract_text_from_pdf(file_source: Union[str, IO]) -> str:
    """
    Extracts raw text from a PDF file (path or file-like object).
    Uses pypdf for pure text extraction - no images or OCR.
    Returns a clean, word-for-word transcript of the PDF content.
    """
    reader = PdfReader(file_source)
    text_parts: List[str] = []
    
    for page_num, page in enumerate(reader.pages, 1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            text_parts.append(f"--- Page {page_num} ---\n{page_text}")
    
    full_text = "\n\n".join(text_parts)
    
    # Clean up common PDF extraction artifacts
    # Remove excessive whitespace while preserving structure
    full_text = re.sub(r'[ \t]+', ' ', full_text)  # Collapse horizontal whitespace
    full_text = re.sub(r'\n{3,}', '\n\n', full_text)  # Collapse excessive newlines
    
    return full_text.strip()

def clean_json_string(s: str) -> str:
    """
    Removes markdown code blocks and other noise from JSON string.
    """
    # Remove ```json ... ``` or ``` ... ```
    s = re.sub(r'```json\s*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'```\s*', '', s)
    return s.strip()

def compute_gpa_from_courses(courses: List[Dict[str, Any]]) -> Optional[float]:
    """
    Fallback overall GPA computed directly from completed courses.
    """
    grade_points: Dict[str, float] = {
        "A+": 4.0, "A": 4.0, "A-": 3.7,
        "B+": 3.3, "B": 3.0, "B-": 2.7,
        "C+": 2.3, "C": 2.0, "C-": 1.7,
        "D+": 1.3, "D": 1.0, "D-": 0.7,
        "F": 0.0,
    }

    total_points = 0.0
    total_credits = 0.0

    for course in courses:
        grade = course.get("grade")
        try:
            credits = float(course.get("credits") or 0)
        except (ValueError, TypeError):
            credits = 0.0

        if not grade or grade not in grade_points or credits <= 0:
            continue

        total_points += grade_points[grade] * credits
        total_credits += credits

    if total_credits <= 0:
        return None

    return total_points / total_credits

def parse_program_evaluation(file_source: Union[str, IO]) -> Dict[str, Any]:
    """
    Parses a program evaluation PDF using an LLM to extract structured JSON data.
    
    This function:
    1. Extracts pure text from the PDF (no images, no OCR)
    2. Sends the text transcript to an LLM for structured parsing
    3. Returns the parsed data as a dictionary
    """
    # Step 1: Extract text from PDF - pure text, word-for-word
    text = extract_text_from_pdf(file_source)
    
    print(f"DEBUG: Extracted {len(text)} characters of text from PDF")
    print(f"DEBUG: First 500 chars of extracted text:\n{text[:500]}...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("OPENAI_MODEL")

    if not api_key or not base_url or not model:
        print("Missing OpenAI configuration. Falling back to empty parse.")
        return {}

    client = OpenAI(api_key=api_key, base_url=base_url)

    system_prompt = """
You are a precise, deterministic data extraction assistant.
Your ONLY job is to convert the EXACT TEXT of a program evaluation PDF into a strict JSON object.

You are NOT allowed to guess, invent, or hallucinate any values.
If a field is not clearly present in the text, set it to null, an empty string, or an empty array as appropriate.

You receive pure text that was extracted word-for-word from a PDF document.
Carefully parse this text and extract all relevant information into the following JSON schema.

The JSON must strictly follow this schema (all keys must exist):
{
    "student_info": {
        "name": "string (Student Name - usually in format 'Last, First') or empty string if not found",
        "id": "string (Student ID number) or empty string if not found",
        "program": "string (Major/Program name) or empty string if not found",
        "degree_type": "string (e.g., 'B.S.', 'B.A.', 'M.S.', 'Ph.D.') or empty string",
        "college": "string (e.g., 'Fowler School of Engineering') or empty string",
        "catalog_year": "string (e.g., 'Fall 2025', '2023-2024') or empty string if not found",
        "expected_graduation_term": "string (e.g., 'Spring 2026') or empty string if not found",
        "enrollment_status": "string (e.g., 'Full-time', 'Part-time') or empty string",
        "class_level": "string (e.g., 'Senior', 'Junior', 'Graduate') or empty string"
    },
    "academic_status": {
        "standing": "string (e.g., 'Good Standing', 'Academic Probation', 'Dean's List') or empty string",
        "honors": ["array of honors/awards mentioned, e.g., 'Dean's List Fall 2024'"],
        "holds": ["array of any holds mentioned, e.g., 'Registration Hold'"],
        "warnings": ["array of any academic warnings"]
    },
    "gpa": {
        "overall": number or null,
        "major": number or null,
        "cumulative_units": number or null
    },
    "credit_requirements": [
        {
            "label": "string (e.g., 'General Education', 'Major Requirements', 'University Requirements', 'Graduate Policies')",
            "required": number,
            "earned": number,
            "in_progress": number,
            "needed": number
        }
    ],
    "degree_requirements": {
        "general_education": {
            "total_required": number or null,
            "total_earned": number or null,
            "areas": [
                {"name": "string (e.g., 'Written Inquiry', 'Quantitative Inquiry')", "required": number, "earned": number, "status": "complete|in_progress|needed"}
            ]
        },
        "major_requirements": {
            "core_required": number or null,
            "core_earned": number or null,
            "electives_required": number or null,
            "electives_earned": number or null,
            "capstone_status": "string (complete|in_progress|needed|not_required)"
        }
    },
    "additional_programs": [
        {"type": "minor|concentration|certificate", "name": "string", "credits_required": number, "credits_earned": number, "status": "complete|in_progress"}
    ],
    "transfer_credits": {
        "total": number or 0,
        "sources": [
            {"institution": "string (e.g., 'Orange Coast College', 'AP Credit')", "credits": number, "courses": ["array of course names/codes"]}
        ]
    },
    "semester_history": [
        {"term": "string (e.g., 'Fall 2023')", "credits_attempted": number, "credits_earned": number, "term_gpa": number or null, "courses_count": number}
    ],
    "courses": {
        "completed": [
            { "term": "string", "subject": "string", "number": "string", "title": "string", "grade": "string", "credits": number, "requirement_satisfied": "string or empty (e.g., 'Major Core', 'GE Written Inquiry')" }
        ],
        "in_progress": [
            { "term": "string", "subject": "string", "number": "string", "title": "string", "grade": "string", "credits": number, "requirement_satisfied": "string or empty" }
        ],
        "remaining_required": [
            { "subject": "string", "number": "string", "title": "string", "credits": number, "requirement_type": "string (e.g., 'Major Core', 'Major Elective', 'GE')" }
        ],
        "all_found": [
            { "term": "string", "subject": "string", "number": "string", "title": "string", "grade": "string", "credits": number }
        ]
    },
    "advisor": {
        "name": "string or empty",
        "email": "string or empty",
        "department": "string or empty"
    }
}

Parsing Guidelines (adapt to the actual text you see):
- Student name and ID often appear together, e.g.: "Favela,Matt - 2390407" or "Favela, Matt - 2390407".
    - Split on '-' to separate name and ID.
    - Trim whitespace, and normalize the name to have a space after the comma (e.g., "Favela, Matt").
- Program name (major) is usually on a line labeled like "Plan(s)" or similar, followed by the program.
- Degree type (B.S., B.A., M.S., etc.) often appears near the program name.
- College/School name often appears (e.g., "Fowler School of Engineering", "Schmid College of Science").
- Catalog year and expected graduation term often appear as: "Exp Grad Term: Spring 2026 Catalog Year: Fall 2025".
- Class level (Freshman, Sophomore, Junior, Senior, Graduate) may be listed.
- GPA values appear in sections labeled like "Overall GPA" or "Major GPA".
- Credit requirement rows often list required/earned/in-progress/needed credits for things like "Graduate Policies", "Residency", etc.

Academic Status extraction:
- Look for phrases like "Good Standing", "Academic Probation", "Academic Warning".
- Dean's List or honors mentions should go in the honors array.
- Registration holds, financial holds, etc. go in the holds array.

Transfer Credits extraction:
- Look for sections labeled "Transfer Credit", "External Credit", "AP Credit", etc.
- Note the institution name and credits transferred.

Semester History extraction:
- Group courses by term and calculate per-term statistics.
- Terms usually look like "Fall 2023", "Spring 2024", "Summer 2024".

Remaining/Required Courses:
- Look for sections showing courses still needed for the degree.
- These may be labeled "Courses Needed", "Requirements Not Yet Met", "Still Required", etc.

Minor/Concentration/Certificate extraction:
- Look for additional program declarations beyond the main major.
- May appear as "Minor:", "Concentration:", "Certificate:", etc.

Course extraction rules:
1. Extract ALL courses found in the document; do not skip any.
2. Put courses with final grades (A, A-, B+, B, B-, C+, C, C-, D+, D, D-, F, P, CR, etc.) into courses.completed.
3. Put courses that are clearly in progress (grade like "IP" or in an "In Progress" section/term) into courses.in_progress.
4. Put courses listed as still needed/required into courses.remaining_required.
5. Every course you detect MUST also be included in courses.all_found.
6. Credits must be numbers (e.g., 3, 4.0); if credits are not clearly given, use 0.
7. If a course satisfies a specific requirement, note it in requirement_satisfied field.

Rules for uncertainty:
- NEVER invent courses, GPAs, or credit totals that are not clearly supported by the text.
- If you are unsure about a numeric value, set it to 0 or null rather than guessing.
- If a section (like credit_requirements) is not present, use an empty array for it.
- If a new section like academic_status, transfer_credits, etc. has no data, use empty objects/arrays.

JSON formatting rules:
- Output ONLY valid JSON. NO markdown, NO code fences, NO comments, NO trailing commas.
- All numbers must be valid JSON numbers (not strings like "3.7").
- All keys listed in the schema must be present, even if the values are empty, 0, null, or empty arrays.
"""

    try:
        # Step 2: Send text to LLM for structured parsing
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Below is the EXACT TEXT extracted word-for-word from the program evaluation PDF. Parse this into the required JSON structure:\n\n{text}"}
            ],
            "temperature": 0
        }
        
        # Only add response_format if likely supported (or let it fail and retry)
        # For safety with diverse OpenRouter models, we might omit it or try/catch
        # But 'json_object' is widely supported now.
        kwargs["response_format"] = {"type": "json_object"}

        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as api_err:
            print(f"API call with json_object failed ({api_err}), retrying without...")
            del kwargs["response_format"]
            response = client.chat.completions.create(**kwargs)
        
        content = response.choices[0].message.content
        print(f"DEBUG: LLM Raw Response: {content[:500]}...")
        
        # Clean the content (remove markdown code blocks if present)
        cleaned_content = content.strip()
        if cleaned_content.startswith("```json"):
            cleaned_content = cleaned_content[7:]
        if cleaned_content.startswith("```"):
            cleaned_content = cleaned_content[3:]
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content[:-3]
            
        cleaned_content = cleaned_content.strip()
        
        try:
            parsed = json.loads(cleaned_content)
            print(f"DEBUG: Successfully parsed JSON. Keys: {list(parsed.keys())}")

            # --- Normalize structure to ensure robustness across models ---
            # Ensure top-level keys exist
            if not isinstance(parsed, dict):
                print("DEBUG: Parsed JSON is not a dict, returning minimal structure")
                return {
                    "student_info": {},
                    "gpa": {},
                    "courses": {"completed": [], "in_progress": [], "remaining_required": [], "all_found": []},
                    "credit_requirements": [],
                    "academic_status": {"standing": "", "honors": [], "holds": [], "warnings": []},
                    "degree_requirements": {"general_education": {"areas": []}, "major_requirements": {}},
                    "additional_programs": [],
                    "transfer_credits": {"total": 0, "sources": []},
                    "semester_history": [],
                    "advisor": {"name": "", "email": "", "department": ""}
                }

            parsed.setdefault("student_info", {})
            parsed.setdefault("gpa", {})
            parsed.setdefault("credit_requirements", [])
            parsed.setdefault("courses", {})
            parsed.setdefault("academic_status", {"standing": "", "honors": [], "holds": [], "warnings": []})
            parsed.setdefault("degree_requirements", {"general_education": {"areas": []}, "major_requirements": {}})
            parsed.setdefault("additional_programs", [])
            parsed.setdefault("transfer_credits", {"total": 0, "sources": []})
            parsed.setdefault("semester_history", [])
            parsed.setdefault("advisor", {"name": "", "email": "", "department": ""})

            # Ensure course arrays exist
            courses = parsed["courses"] if isinstance(parsed["courses"], dict) else {}
            courses.setdefault("completed", [])
            courses.setdefault("in_progress", [])
            courses.setdefault("remaining_required", [])
            courses.setdefault("all_found", [])
            parsed["courses"] = courses

            # Normalize GPA values to floats when possible
            gpa = parsed["gpa"] if isinstance(parsed["gpa"], dict) else {}
            for key in ["overall", "major"]:
                if key in gpa and gpa[key] is not None:
                    try:
                        gpa[key] = float(gpa[key])
                    except (TypeError, ValueError):
                        # If cannot parse as float, drop value so fallback can run
                        gpa.pop(key, None)
            parsed["gpa"] = gpa

            # Basic course normalization: ensure credits are numeric and drop non-dict entries
            def _normalize_course_list(items: Any) -> List[Dict[str, Any]]:
                norm: List[Dict[str, Any]] = []
                if not isinstance(items, list):
                    return []
                for c in items:
                    if not isinstance(c, dict):
                        continue
                    # Normalize credits
                    try:
                        c["credits"] = float(c.get("credits") or 0)
                    except (TypeError, ValueError):
                        c["credits"] = 0.0
                    norm.append(c)
                return norm

            courses["completed"] = _normalize_course_list(courses.get("completed", []))
            courses["in_progress"] = _normalize_course_list(courses.get("in_progress", []))
            courses["remaining_required"] = _normalize_course_list(courses.get("remaining_required", []))
            courses["all_found"] = _normalize_course_list(courses.get("all_found", []))
            parsed["courses"] = courses

            # Normalize transfer_credits
            transfer = parsed.get("transfer_credits", {})
            if not isinstance(transfer, dict):
                transfer = {"total": 0, "sources": []}
            try:
                transfer["total"] = int(transfer.get("total") or 0)
            except (ValueError, TypeError):
                transfer["total"] = 0
            parsed["transfer_credits"] = transfer

            # Normalize semester_history
            history = parsed.get("semester_history", [])
            if not isinstance(history, list):
                history = []
            parsed["semester_history"] = history

            # Fallback: If GPA is missing or 0, calculate it from courses
            gpa = parsed.get("gpa", {})
            if not gpa.get("overall") or gpa.get("overall") == 0:
                print("DEBUG: GPA missing or 0, calculating from courses...")
                courses_list = parsed.get("courses", {}).get("completed", [])
                # If completed list is empty, try all_found
                if not courses_list:
                    courses_list = parsed.get("courses", {}).get("all_found", [])

                calculated_overall = compute_gpa_from_courses(courses_list)
                if calculated_overall is not None:
                    gpa["overall"] = calculated_overall
                    parsed["gpa"] = gpa
                    print(f"DEBUG: Calculated GPA: {calculated_overall}")

            return parsed
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            print(f"Failed Content: {cleaned_content}")
            return {}
    except Exception as e:
        print(f"LLM Parsing failed: {e}")
        # Return a minimal structure so downstream code doesn't crash
        return {
            "student_info": {},
            "gpa": {},
            "courses": {"completed": [], "in_progress": [], "remaining_required": [], "all_found": []},
            "credit_requirements": [],
            "academic_status": {"standing": "", "honors": [], "holds": [], "warnings": []},
            "degree_requirements": {"general_education": {"areas": []}, "major_requirements": {}},
            "additional_programs": [],
            "transfer_credits": {"total": 0, "sources": []},
            "semester_history": [],
            "advisor": {"name": "", "email": "", "department": ""}
        }
