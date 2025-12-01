import os
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from pathlib import Path

from openai import OpenAI
from app.services.supabase_client import supabase_request
from app.services.evaluation_service import load_parsed_data

# Initialize OpenAI Client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

_CATALOG_CACHE: Optional[List[Dict[str, Any]]] = None


def _extract_first_name(full_name: str) -> str:
    """
    Extract the first name from various name formats.
    Handles: "Last, First", "Last,First", "First Last", or just "First"
    """
    if not full_name:
        return ""
    
    full_name = full_name.strip()
    
    # Handle "Last, First" or "Last,First" format (common in academic records)
    if "," in full_name:
        parts = full_name.split(",")
        if len(parts) >= 2:
            # Take the part after the comma (first name)
            first_name = parts[1].strip()
            # Remove any trailing ID like " - 2390407" (note: space-hyphen-space pattern)
            if " - " in first_name:
                first_name = first_name.split(" - ")[0].strip()
            # If first name has multiple parts, take just the first word (first name, not middle)
            return first_name.split()[0] if first_name else ""
    
    # Handle "First Last" format - take the first word
    parts = full_name.split()
    return parts[0] if parts else ""


def create_onboarding_session(user_id: str, email: str) -> str:
    """Always create a fresh onboarding session for a user."""
    # We can link the latest evaluation_id if we want, but for now user_id is enough
    payload = {
        "user_id": user_id,
        "title": "Onboarding",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    create_resp = supabase_request(
        "POST",
        "/rest/v1/chat_sessions",
        json=payload,
        headers={"Prefer": "return=representation"}
    )
    
    if create_resp.status_code not in (200, 201):
        raise RuntimeError("Failed to create chat session")
        
    session_id = create_resp.json()[0]['id']
    return session_id


def create_explore_session(user_id: str, email: str) -> str:
    """Create a new Explore session."""
    payload = {
        "user_id": user_id,
        "title": "Explore My Options",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    create_resp = supabase_request(
        "POST",
        "/rest/v1/chat_sessions",
        json=payload,
        headers={"Prefer": "return=representation"}
    )
    
    if create_resp.status_code not in (200, 201):
        raise RuntimeError("Failed to create explore session")
        
    session_id = create_resp.json()[0]['id']
    return session_id


def list_user_sessions(user_id: str) -> List[Dict[str, Any]]:
    """List all chat sessions for a user, ordered by most recent."""
    resp = supabase_request(
        "GET",
        f"/rest/v1/chat_sessions?user_id=eq.{user_id}&select=id,title,created_at&order=created_at.desc"
    )
    if resp.status_code == 200 and resp.json():
        return resp.json()
    return []


def get_or_create_onboarding_session(user_id: str, email: str) -> str:
    """Finds an existing onboarding session or creates a new one.

    For the updated UX we want a fresh chat whenever the user
    reloads the onboarding page, so callers that need that behavior
    should call create_onboarding_session directly instead.
    """
    resp = supabase_request(
        "GET",
        f"/rest/v1/chat_sessions?user_id=eq.{user_id}&title=eq.Onboarding&select=id&limit=1"
    )
    if resp.status_code == 200 and resp.json():
        return resp.json()[0]["id"]
    return create_onboarding_session(user_id, email)

def reset_onboarding_session(user_id: str):
    """
    Deletes any existing 'Onboarding' session for the user so they can start over.
    Also clears their scheduling preferences so they can re-answer questions.
    """
    # Find and delete onboarding session
    resp = supabase_request(
        "GET", 
        f"/rest/v1/chat_sessions?user_id=eq.{user_id}&title=eq.Onboarding&select=id"
    )
    if resp.status_code == 200 and resp.json():
        for sess in resp.json():
            # Delete session (cascade deletes messages)
            supabase_request(
                "DELETE",
                f"/rest/v1/chat_sessions?id=eq.{sess['id']}"
            )
    
    # Clear scheduling preferences so user can start fresh
    supabase_request(
        "DELETE",
        f"/rest/v1/scheduling_preferences?user_id=eq.{user_id}"
    )

def save_message(session_id: str, sender: str, text: str):
    payload = {
        "session_id": session_id,
        "sender": sender, # 'user' or 'assistant'
        "message_text": text
    }
    supabase_request("POST", "/rest/v1/chat_messages", json=payload)


# ============ SCHEDULING PREFERENCES PERSISTENCE ============

def get_scheduling_preferences(user_id: str) -> Dict[str, Any]:
    """Load user's scheduling preferences from Supabase."""
    resp = supabase_request(
        "GET",
        f"/rest/v1/scheduling_preferences?user_id=eq.{user_id}&select=*"
    )
    if resp.status_code == 200 and resp.json():
        return resp.json()[0]
    return {}


def save_scheduling_preference(user_id: str, field: str, value: Any, collected_name: str = None) -> Dict[str, Any]:
    """
    Save or update a single scheduling preference field.
    Uses upsert to create row if not exists.
    
    Args:
        user_id: The user's ID
        field: The database column name to save to
        value: The value to save
        collected_name: Optional semantic name to add to collected_fields array.
                       If not provided, uses the field name.
    """
    # First check if row exists
    existing = get_scheduling_preferences(user_id)
    
    # Build update payload
    collected = existing.get('collected_fields', []) or []
    name_to_add = collected_name if collected_name else field
    if name_to_add not in collected:
        collected.append(name_to_add)
    
    payload = {
        "user_id": user_id,
        field: value,
        "collected_fields": collected,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    print(f"DEBUG save_scheduling_preference: user={user_id}, field={field}, value={value}, collected_name={name_to_add}")
    print(f"DEBUG save_scheduling_preference: existing={bool(existing)}, collected_fields will be={collected}")
    
    if existing:
        # Update existing row
        resp = supabase_request(
            "PATCH",
            f"/rest/v1/scheduling_preferences?user_id=eq.{user_id}",
            json=payload,
            headers={"Prefer": "return=representation"}
        )
    else:
        # Insert new row
        resp = supabase_request(
            "POST",
            "/rest/v1/scheduling_preferences",
            json=payload,
            headers={"Prefer": "return=representation"}
        )
    
    print(f"DEBUG save_scheduling_preference: response status={resp.status_code}, body={resp.text[:200] if resp.text else 'empty'}")
    
    if resp.status_code in (200, 201) and resp.json():
        return resp.json()[0] if isinstance(resp.json(), list) else resp.json()
    return {}


def parse_and_save_user_response(user_id: str, user_message: str, current_prefs: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """
    Parse user's response and save relevant preferences.
    Returns (updated_prefs, field_saved).
    """
    msg_lower = user_message.lower().strip()
    field_saved = ""
    
    print(f"DEBUG parse_and_save: Parsing message '{msg_lower}' for user {user_id}")
    print(f"DEBUG parse_and_save: Current prefs collected_fields: {current_prefs.get('collected_fields', [])}")
    
    # Detect planning mode - be more flexible with matching
    # Include exact button text variations
    planning_next_semester = ["next semester", "upcoming", "this semester", "next sem", "semester planning", "plan my next semester"]
    planning_four_year = ["4-year", "four year", "4 year", "full plan", "full 4", "4-year path", "full path", "map out my 4-year", "4-year plan"]
    planning_progress = ["progress", "view progress", "view my progress", "my progress", "show progress", "degree progress", "show my degree"]
    
    if any(x in msg_lower for x in planning_next_semester):
        save_scheduling_preference(user_id, "planning_mode", "upcoming_semester")
        field_saved = "planning_mode"
        print(f"DEBUG parse_and_save: Detected planning_mode = upcoming_semester")
    elif any(x in msg_lower for x in planning_four_year):
        save_scheduling_preference(user_id, "planning_mode", "four_year_plan")
        field_saved = "planning_mode"
        print(f"DEBUG parse_and_save: Detected planning_mode = four_year_plan")
    elif any(x in msg_lower for x in planning_progress):
        save_scheduling_preference(user_id, "planning_mode", "view_progress")
        field_saved = "planning_mode"
        print(f"DEBUG parse_and_save: Detected planning_mode = view_progress")
    
    # Detect credit load
    elif any(x in msg_lower for x in ["9-12", "9 to 12", "light", "9 12"]):
        save_scheduling_preference(user_id, "preferred_credits_min", 9, collected_name="credits")
        save_scheduling_preference(user_id, "preferred_credits_max", 12, collected_name="credits")
        field_saved = "credits"
    elif any(x in msg_lower for x in [
        "12-15", "12 to 15", "standard", "12 15", "12-15 credits",
        "i want 12-15", "i want 12 to 15", "12 to 15 credits", "12-15 credits load"
    ]):
        save_scheduling_preference(user_id, "preferred_credits_min", 12, collected_name="credits")
        save_scheduling_preference(user_id, "preferred_credits_max", 15, collected_name="credits")
        field_saved = "credits"
    elif any(x in msg_lower for x in ["15-18", "15 to 18", "heavy", "15 18", "heavy load", "take a heavy load"]):
        save_scheduling_preference(user_id, "preferred_credits_min", 15, collected_name="credits")
        save_scheduling_preference(user_id, "preferred_credits_max", 18, collected_name="credits")
        field_saved = "credits"
    
    # Detect schedule/time preferences
    elif any(x in msg_lower for x in ["morning", "mornings only", "am classes"]):
        save_scheduling_preference(user_id, "preferred_time_of_day", "morning", collected_name="time_preference")
        field_saved = "time_preference"
    elif any(x in msg_lower for x in ["afternoon"]):
        save_scheduling_preference(user_id, "preferred_time_of_day", "afternoon", collected_name="time_preference")
        field_saved = "time_preference"
    elif any(x in msg_lower for x in ["evening", "night", "after 5"]):
        save_scheduling_preference(user_id, "preferred_time_of_day", "evening", collected_name="time_preference")
        field_saved = "time_preference"
    elif any(x in msg_lower for x in ["flexible", "any time", "no preference"]):
        save_scheduling_preference(user_id, "preferred_time_of_day", "flexible", collected_name="time_preference")
        field_saved = "time_preference"
    elif "no friday" in msg_lower or "no fridays" in msg_lower:
        save_scheduling_preference(user_id, "days_to_avoid", ["Friday"], collected_name="days_to_avoid")
        field_saved = "days_to_avoid"
    
    # Detect work status
    elif any(x in msg_lower for x in ["part-time", "part time", "work part"]):
        save_scheduling_preference(user_id, "work_status", "part_time", collected_name="work_status")
        field_saved = "work_status"
    elif any(x in msg_lower for x in ["full-time job", "full time job", "work full"]):
        save_scheduling_preference(user_id, "work_status", "full_time", collected_name="work_status")
        field_saved = "work_status"
    elif any(x in msg_lower for x in ["no work", "don't work", "no job", "no commitments", "no work commitments"]):
        save_scheduling_preference(user_id, "work_status", "none", collected_name="work_status")
        field_saved = "work_status"
    
    # Detect summer availability
    elif any(x in msg_lower for x in ["yes to summer", "yes summer", "take summer"]):
        save_scheduling_preference(user_id, "summer_availability", "yes", collected_name="summer")
        field_saved = "summer"
    elif any(x in msg_lower for x in ["no summer", "not summer"]):
        save_scheduling_preference(user_id, "summer_availability", "no", collected_name="summer")
        field_saved = "summer"
    elif any(x in msg_lower for x in ["maybe", "one course", "maybe summer"]):
        save_scheduling_preference(user_id, "summer_availability", "maybe", collected_name="summer")
        field_saved = "summer"
    
    # Detect priority focus
    elif any(x in msg_lower for x in ["major req", "major requirements", "requirements first"]):
        save_scheduling_preference(user_id, "priority_focus", "major_requirements", collected_name="focus")
        field_saved = "focus"
    elif any(x in msg_lower for x in ["elective", "interests", "fun classes"]):
        save_scheduling_preference(user_id, "priority_focus", "electives", collected_name="focus")
        field_saved = "focus"
    elif any(x in msg_lower for x in ["graduat", "on time", "finish"]):
        save_scheduling_preference(user_id, "priority_focus", "graduation_timeline", collected_name="focus")
        field_saved = "focus"
    
    # Log result
    if field_saved:
        print(f"DEBUG parse_and_save: Saved field '{field_saved}' for user {user_id}")
    else:
        print(f"DEBUG parse_and_save: No field matched for message '{msg_lower}'")
    
    # Return updated preferences
    updated_prefs = get_scheduling_preferences(user_id)
    print(f"DEBUG parse_and_save: Updated prefs collected_fields: {updated_prefs.get('collected_fields', [])}")
    return updated_prefs, field_saved


def check_onboarding_completeness(prefs: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Check if we have collected enough core preferences.
    Returns (is_complete, list_of_missing_fields).
    """
    required_fields = ['planning_mode', 'preferred_credits_min', 'work_status', 'summer_availability']
    collected = prefs.get('collected_fields', []) or []
    
    # Map collected field names to required fields
    field_mapping = {
        'planning_mode': 'planning_mode',
        'credits': 'preferred_credits_min',
        'time_preference': 'preferred_time_of_day',
        'days_to_avoid': 'days_to_avoid',
        'work_status': 'work_status',
        'summer': 'summer_availability',
        'focus': 'priority_focus'
    }
    
    # Check what's been collected
    collected_mapped = set()
    for f in collected:
        if f in field_mapping:
            collected_mapped.add(field_mapping[f])
        else:
            collected_mapped.add(f)
    
    missing = [f for f in required_fields if f not in collected_mapped and not prefs.get(f)]
    is_complete = len(missing) == 0
    
    return is_complete, missing


def get_next_question_topic(prefs: Dict[str, Any]) -> str:
    """
    Determine which question to ask next based on what's been collected.
    """
    collected = prefs.get('collected_fields', []) or []
    
    print(f"DEBUG get_next_question_topic: collected_fields = {collected}")
    print(f"DEBUG get_next_question_topic: prefs keys = {list(prefs.keys())}")
    
    # Order of questions to ask
    question_order = [
        ('planning_mode', 'planning_mode'),
        ('credits', 'preferred_credits_min'),
        ('time_preference', 'preferred_time_of_day'),
        ('work_status', 'work_status'),
        ('summer', 'summer_availability'),
        ('focus', 'priority_focus'),
    ]
    
    for field_name, db_field in question_order:
        # Check both the collected_fields array AND the actual field value
        if field_name not in collected and not prefs.get(db_field):
            print(f"DEBUG get_next_question_topic: Next topic = {field_name} (not in collected and no value)")
            return field_name
    
    print(f"DEBUG get_next_question_topic: All topics complete!")
    return 'complete'


def get_collected_summary(prefs: Dict[str, Any]) -> str:
    """Generate a summary of what we've collected so far."""
    parts = []
    
    if prefs.get('planning_mode'):
        mode_display = {
            'upcoming_semester': 'Next semester planning',
            'four_year_plan': '4-year path planning',
            'view_progress': 'Progress viewing'
        }.get(prefs['planning_mode'], prefs['planning_mode'])
        parts.append(f"Mode: {mode_display}")
    
    if prefs.get('preferred_credits_min') and prefs.get('preferred_credits_max'):
        parts.append(f"Credits: {prefs['preferred_credits_min']}-{prefs['preferred_credits_max']}")
    
    if prefs.get('preferred_time_of_day'):
        parts.append(f"Time: {prefs['preferred_time_of_day'].capitalize()}")
    
    if prefs.get('work_status'):
        status_display = {'none': 'No work', 'part_time': 'Part-time', 'full_time': 'Full-time'}
        parts.append(f"Work: {status_display.get(prefs['work_status'], prefs['work_status'])}")
    
    if prefs.get('summer_availability'):
        parts.append(f"Summer: {prefs['summer_availability'].capitalize()}")
    
    if prefs.get('priority_focus'):
        focus_display = {
            'major_requirements': 'Major requirements',
            'electives': 'Electives/Interests',
            'graduation_timeline': 'Graduate on time'
        }
        parts.append(f"Focus: {focus_display.get(prefs['priority_focus'], prefs['priority_focus'])}")
    
    return ", ".join(parts) if parts else "Nothing collected yet"


def get_chat_history(session_id: str) -> List[Dict[str, str]]:
    resp = supabase_request(
        "GET",
        f"/rest/v1/chat_messages?session_id=eq.{session_id}&select=sender,message_text&order=created_at.asc"
    )
    if resp.status_code != 200:
        return []
        
    # Map to OpenAI format
    messages = []
    for row in resp.json():
        role = "user" if row['sender'] == 'user' else "assistant"
        messages.append({"role": role, "content": row['message_text']})
    return messages


def _load_catalog_data() -> List[Dict[str, Any]]:
    """Load scraped catalog JSON once and cache it.

    File path: backend/data/chapman_catalogs_full.json (relative to backend root).
    """
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE

    try:
        backend_root = Path(__file__).resolve().parents[2]
        path = backend_root / "data" / "chapman_catalogs_full.json"
        if not path.exists():
            print(f"Catalog JSON not found at {path}, skipping catalog context.")
            _CATALOG_CACHE = []
            return _CATALOG_CACHE
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            print("Catalog JSON was not a list; ignoring.")
            _CATALOG_CACHE = []
        else:
            _CATALOG_CACHE = data
    except Exception as e:
        print(f"Failed to load catalog JSON: {e}")
        _CATALOG_CACHE = []
    return _CATALOG_CACHE or []


def _normalize_prog_name(name: str) -> str:
    s = name.lower()
    # Strip common degree suffixes
    s = re.sub(r"\b(b\.a\.?|b\.s\.?|b\.f\.a\.?|b\.m\.?|ba|bs|bfa|bm)\b", "", s)
    # Collapse non-alphanumeric
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def _choose_catalog_for_year(catalogs: List[Dict[str, Any]], catalog_year: str) -> Optional[Dict[str, Any]]:
    if not catalogs:
        return None

    # Normalize catalog_year like "2024-2025" or just a single year
    target_span = None
    target_year = None
    m = re.search(r"(\d{4}-\d{4})", catalog_year or "")
    if m:
        target_span = m.group(1)
    else:
        m = re.search(r"(\d{4})", catalog_year or "")
        if m:
            target_year = m.group(1)

    # Prefer exact span match, then prefix match, else latest catalog
    # Sort catalogs newest->oldest by year string
    sorted_cats = sorted(catalogs, key=lambda c: str(c.get("year", "")), reverse=True)

    if target_span:
        for c in sorted_cats:
            if str(c.get("year", "")) == target_span:
                return c
    if target_year:
        for c in sorted_cats:
            year_str = str(c.get("year", ""))
            if year_str.startswith(target_year):
                return c

    return sorted_cats[0]


def _find_best_program_match(parsed_fields: Dict[str, Any], catalogs: List[Dict[str, Any]]) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """Given parsed student info and all catalogs, pick the best matching program.

    Returns (catalog_entry, program_entry) or None.
    """
    student_info = parsed_fields.get("student_info") or {}
    program_name = (student_info.get("program") or "").strip()
    if not program_name:
        return None

    catalog_year = (student_info.get("catalog_year") or "").strip()
    catalogs_data = catalogs or _load_catalog_data()
    if not catalogs_data:
        return None

    catalog_entry = _choose_catalog_for_year(catalogs_data, catalog_year)
    if not catalog_entry:
        return None

    programs = catalog_entry.get("programs") or []
    target_norm = _normalize_prog_name(program_name)
    if not target_norm:
        return None
    target_tokens = set(target_norm.split())

    best_prog: Optional[Dict[str, Any]] = None
    best_score = 0

    for prog in programs:
        name = prog.get("name") or ""
        prog_norm = _normalize_prog_name(name)
        if not prog_norm:
            continue
        prog_tokens = set(prog_norm.split())

        score = 0
        if prog_norm == target_norm:
            score = 100
        elif target_norm in prog_norm or prog_norm in target_norm:
            score = 80
        else:
            overlap = len(target_tokens & prog_tokens)
            if overlap >= 2:
                score = 50 + overlap

        if score > best_score:
            best_score = score
            best_prog = prog

    if best_prog is None or best_score == 0:
        print(f"DEBUG: No strong catalog match for program '{program_name}'")
        return None

    print(f"DEBUG: Matched student program '{program_name}' to catalog entry '{best_prog.get('name')}' in {catalog_entry.get('year')}")
    return catalog_entry, best_prog


def _build_catalog_context(parsed_fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build a compact catalog-context object for the LLM.

    Includes year, program name, degree type, school, and full scraped requirements.
    """
    catalogs = _load_catalog_data()
    match = _find_best_program_match(parsed_fields, catalogs)
    if not match:
        return None

    catalog_entry, program_entry = match
    return {
        "catalog_year": catalog_entry.get("year"),
        "program_name": program_entry.get("name"),
        "degree_type": program_entry.get("type"),
        "school": program_entry.get("school"),
        "requirements": program_entry.get("requirements", []),
    }


def _extract_transcript_course_codes(parsed_fields: Dict[str, Any]) -> Tuple[set, set]:
    """Return (completed_codes, in_progress_codes) from parsed transcript data.

    Codes are normalized like "CPSC 350" to match catalog course codes.
    """
    completed: set = set()
    in_prog: set = set()

    courses = parsed_fields.get("courses") or {}

    def _norm_from_course(c: Dict[str, Any]) -> Optional[str]:
        subj = (c.get("subject") or "").strip()
        num = (c.get("number") or "").strip()
        if subj and num:
            return f"{subj.upper()} {num.upper()}"
        # Fallback: try to parse from title if subject/number missing
        title = (c.get("title") or "").strip()
        m = re.match(r"([A-Z]{3,4})\s*(\d+[A-Z]?)", title)
        if m:
            return f"{m.group(1)} {m.group(2)}".upper()
        return None

    for c in courses.get("completed", []) or []:
        code = _norm_from_course(c)
        if code:
            completed.add(code)
    for c in courses.get("in_progress", []) or []:
        code = _norm_from_course(c)
        if code:
            in_prog.add(code)

    return completed, in_prog


def _compute_degree_status(parsed_fields: Dict[str, Any], catalog_context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compute a simple status per catalog requirement section.

    Status values: "complete", "in_progress", "not_started".
    We look at each requirement section's courses (if any) and see whether
    they appear in completed or in_progress transcript courses.
    """
    if not catalog_context:
        return []

    requirements = catalog_context.get("requirements") or []
    if not requirements:
        return []

    completed, in_prog = _extract_transcript_course_codes(parsed_fields)

    def _section_status(section: Dict[str, Any]) -> Optional[str]:
        content = section.get("content") or []
        codes: List[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "course":
                raw_code = (item.get("code") or item.get("course_code") or "").strip()
                if raw_code:
                    m = re.match(r"([A-Z]{3,4})\s*(\d+[A-Z]?)", raw_code.upper())
                    if m:
                        codes.append(f"{m.group(1)} {m.group(2)}")

        if not codes:
            return None

        any_completed = any(c in completed for c in codes)
        any_in_prog = any(c in in_prog for c in codes)
        all_completed = all(c in completed for c in codes)

        if all_completed:
            return "complete"
        if any_in_prog or any_completed:
            return "in_progress"
        return "not_started"

    status_list: List[Dict[str, Any]] = []
    for section in requirements:
        title = section.get("title") or "Untitled requirement block"
        status = _section_status(section)
        if not status:
            continue
        status_list.append({
            "title": title,
            "status": status,
        })

    return status_list

def generate_reply(
    user_id: str,
    email: str,
    session_id: str,
    user_message: Optional[str],
    mode: Optional[str] = None,
    context: str = "onboarding"
) -> Dict[str, Any]:
    """Generate a reply plus up to 3 suggested follow‑up messages.
    
    For onboarding: Uses deterministic responses for reliable flow.
    For explore: Uses LLM for open-ended conversation.
    """

    # 1. Get PDF Context (student-specific)
    parsed_data = load_parsed_data(email)
    parsed_fields: Dict[str, Any] = {}
    if parsed_data and "parsed_data" in parsed_data:
        parsed_fields = parsed_data["parsed_data"] or {}

    # Extract student first name
    student_info = parsed_fields.get("student_info", {})
    student_name = _extract_first_name(student_info.get("name", ""))
    name_greeting = student_name or "there"

    # Get current preferences and parse user's response
    current_prefs = get_scheduling_preferences(user_id)
    if user_message and context == "onboarding":
        current_prefs, field_saved = parse_and_save_user_response(user_id, user_message, current_prefs)

    # Check status
    is_complete, missing_fields = check_onboarding_completeness(current_prefs)
    next_topic = get_next_question_topic(current_prefs)
    collected_summary = get_collected_summary(current_prefs)

    # Save user message to history
    if user_message:
        save_message(session_id, "user", user_message)

    # ========== ONBOARDING: Use deterministic responses ==========
    if context == "onboarding":
        reply_text, suggestions = _get_onboarding_response(
            next_topic, is_complete, name_greeting, collected_summary
        )
        
        # Guard against race conditions for initial greeting
        if not user_message:
            current_history = get_chat_history(session_id)
            has_assistant_msg = any(m.get("role") == "assistant" for m in current_history)
            if not has_assistant_msg:
                save_message(session_id, "assistant", reply_text)
            else:
                # Return existing message
                for m in current_history:
                    if m.get("role") == "assistant":
                        reply_text = m.get("content", reply_text)
                        break
        else:
            save_message(session_id, "assistant", reply_text)
        
        return {"reply": reply_text, "suggestions": suggestions}

    # ========== EXPLORE: Use LLM for open-ended conversation ==========
    catalog_context = _build_catalog_context(parsed_fields) if parsed_fields else None
    catalog_str = json.dumps(catalog_context, indent=2) if catalog_context else "null"
    degree_status = _compute_degree_status(parsed_fields, catalog_context)
    degree_status_str = json.dumps(degree_status, indent=2) if degree_status else "[]"

    system_prompt = f"""
You are a helpful academic advisor for Chapman University students.

Student: {student_name or 'Student'}
Program: {student_info.get('program', 'Unknown')}
Catalog Year: {student_info.get('catalog_year', 'Unknown')}

**DEGREE STATUS**:
{degree_status_str}

**CATALOG REQUIREMENTS**:
{catalog_str}

**INSTRUCTIONS**:
- Be helpful and encouraging
- Answer questions about their degree progress
- Keep responses concise (under 150 words)
- Use markdown for formatting

**OUTPUT FORMAT (XML)**:
<response>
  <message>Your response here</message>
  <suggestions>
    <suggestion>Follow-up 1</suggestion>
    <suggestion>Follow-up 2</suggestion>
    <suggestion>Follow-up 3</suggestion>
  </suggestions>
</response>
"""

    history = get_chat_history(session_id)
    messages = [{"role": "system", "content": system_prompt}] + history
    if user_message:
        messages.append({"role": "user", "content": user_message})

    def _parse_xml_envelope(raw: str) -> Tuple[str, List[str]]:
        text = raw.strip()
        if text.startswith("```"):
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        idx = text.find("<response")
        if idx > 0:
            text = text[idx:]

        try:
            root = ET.fromstring(text)
        except ET.ParseError as e:
            print(f"Failed to parse XML envelope: {e} :: {text[:200]}")
            return text.strip(), []

        msg_el = root.find("message")
        reply_text_local = (msg_el.text or "").strip() if msg_el is not None else ""
        if not reply_text_local:
            reply_text_local = text.strip()

        suggestions_local: List[str] = []
        for s_el in root.findall("./suggestions/suggestion"):
            if s_el.text:
                candidate = s_el.text.strip()
                if candidate:
                    suggestions_local.append(candidate)

        return reply_text_local, suggestions_local[:3]

    try:
        if not client.api_key:
            reply_text = "I'm ready to help, but my configuration needs attention."
            suggestions: List[str] = []
        else:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.7,
            )
            content = response.choices[0].message.content or ""
            reply_text, suggestions = _parse_xml_envelope(content)

    except Exception as e:
        print(f"OpenAI API Error: {e}")
        reply_text = "I'm having trouble right now. What would you like help with?"
        suggestions = ["Plan my next semester", "Show my degree progress", "What courses do I need?"]

    save_message(session_id, "assistant", reply_text)

    return {"reply": reply_text, "suggestions": suggestions}


def generate_reply_stream(
    user_id: str,
    email: str,
    session_id: str,
    user_message: Optional[str],
    mode: Optional[str] = None,
    context: str = "onboarding"
):
    """Generator that yields streaming chunks for the chat response.
    
    For onboarding context: Uses deterministic responses for reliable flow.
    For explore context: Uses LLM for open-ended conversation.
    
    Yields dictionaries with keys:
    - 'type': 'chunk' | 'suggestions' | 'done' | 'error'
    - 'content': the text chunk or suggestions list
    """
    
    # 1. Get PDF Context (student-specific)
    parsed_data = load_parsed_data(email)
    parsed_fields: Dict[str, Any] = {}
    if parsed_data and "parsed_data" in parsed_data:
        parsed_fields = parsed_data["parsed_data"] or {}
    
    # Extract student first name from "Last, First" format
    student_info = parsed_fields.get("student_info", {})
    student_name = _extract_first_name(student_info.get("name", ""))
    name_greeting = student_name or "there"
    
    # 1d. Get current preferences and parse user's response
    current_prefs = get_scheduling_preferences(user_id)
    if user_message and context == "onboarding":
        current_prefs, field_saved = parse_and_save_user_response(user_id, user_message, current_prefs)
    
    # Check status
    is_complete, missing_fields = check_onboarding_completeness(current_prefs)
    next_topic = get_next_question_topic(current_prefs)
    collected_summary = get_collected_summary(current_prefs)
    
    # Save user message to history
    if user_message:
        save_message(session_id, "user", user_message)
    
    # ========== ONBOARDING: Use deterministic responses ==========
    if context == "onboarding":
        response, suggestions = _get_onboarding_response(
            next_topic, is_complete, name_greeting, collected_summary
        )
        
        # Stream the response character by character (simulate typing)
        for char in response:
            yield {"type": "chunk", "content": char}
        
        # Save the response
        save_message(session_id, "assistant", response)
        
        # Send suggestions
        yield {"type": "suggestions", "content": suggestions}
        return
    
    # ========== EXPLORE: Use LLM for open-ended conversation ==========
    catalog_context = _build_catalog_context(parsed_fields) if parsed_fields else None
    catalog_str = json.dumps(catalog_context, indent=2) if catalog_context else "null"
    degree_status = _compute_degree_status(parsed_fields, catalog_context)
    degree_status_str = json.dumps(degree_status, indent=2) if degree_status else "[]"
    
    system_prompt = f"""
You are a helpful academic advisor for Chapman University students.

Student: {student_name or 'Student'}
Program: {student_info.get('program', 'Unknown')}
Catalog Year: {student_info.get('catalog_year', 'Unknown')}

**DEGREE STATUS**:
{degree_status_str}

**CATALOG REQUIREMENTS**:
{catalog_str}

**INSTRUCTIONS**:
- Be helpful and encouraging
- Answer questions about their degree progress
- Keep responses concise (under 150 words)
- Use markdown for formatting

Respond naturally. At the end, optionally add:
[SUGGESTIONS]
Suggestion 1
Suggestion 2
Suggestion 3
[/SUGGESTIONS]
"""

    history = get_chat_history(session_id)
    messages = [{"role": "system", "content": system_prompt}] + history
    if user_message:
        messages.append({"role": "user", "content": user_message})

    full_response = ""
    suggestions: List[str] = []
    
    try:
        if not client.api_key:
            yield {"type": "chunk", "content": "I'm ready to help, but my configuration needs attention."}
            yield {"type": "suggestions", "content": ["Plan my next semester", "Show my degree progress", "What courses do I need?"]}
            return
            
        stream = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            stream=True,
        )
        
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_response += text
                
                # Don't stream the suggestions marker
                if "[SUGGESTIONS]" not in full_response:
                    yield {"type": "chunk", "content": text}
        
        # Parse suggestions from the response
        if "[SUGGESTIONS]" in full_response:
            parts = full_response.split("[SUGGESTIONS]")
            clean_response = parts[0].strip()
            suggestions_part = parts[1].split("[/SUGGESTIONS]")[0] if len(parts) > 1 else ""
            suggestions = [s.strip() for s in suggestions_part.strip().split("\n") if s.strip()][:3]
            full_response = clean_response
        
        save_message(session_id, "assistant", full_response)
        
        if suggestions:
            yield {"type": "suggestions", "content": suggestions}
        else:
            yield {"type": "suggestions", "content": ["What courses do I need?", "Show my progress", "Help me plan"]}
            
    except Exception as e:
        print(f"OpenAI Streaming Error: {e}")
        yield {"type": "chunk", "content": "I'm having trouble right now. What would you like help with?"}
        yield {"type": "suggestions", "content": ["Plan my next semester", "Show my degree progress", "What courses do I need?"]}


def _get_onboarding_response(next_topic: str, is_complete: bool, name: str, summary: str) -> Tuple[str, List[str]]:
    """
    Returns deterministic (response, suggestions) for onboarding flow.
    This ensures consistent, predictable behavior without LLM variability.
    """
    
    if next_topic == "planning_mode":
        response = f"""Hi {name}! 👋 I'll ask a few quick questions to personalize your plan.

📋 What would you like to focus on?
• **Next semester** planning
• **Full 4-year** path
• **View progress** so far"""
        suggestions = ["Next semester", "Full 4-year plan", "View my progress"]
    
    elif next_topic == "credits":
        response = """✅ Got it!

📚 How many **credits** do you want to take?
• **Light** (9-12 credits)
• **Standard** (12-15 credits)
• **Heavy** (15-18 credits)"""
        suggestions = ["Light (9-12)", "Standard (12-15)", "Heavy (15-18)"]
    
    elif next_topic == "time_preference":
        response = """✅ Noted!

⏰ When do you prefer classes?
• **Mornings**
• **Afternoons**
• **Flexible**"""
        suggestions = ["Mornings", "Afternoons", "Flexible"]
    
    elif next_topic == "work_status":
        response = """✅ Perfect!

💼 Do you have work commitments?
• **Part-time** job
• **Full-time** job
• **No work**"""
        suggestions = ["Part-time", "Full-time job", "No work"]
    
    elif next_topic == "summer":
        response = """✅ Great!

🌴 Are you open to **summer** classes?
• **Yes**
• **No**
• **Maybe one course**"""
        suggestions = ["Yes to summer", "No summer", "Maybe one course"]
    
    elif next_topic == "focus":
        response = """✅ Almost done!

🎯 What's your top priority?
• **Major requirements** first
• **Electives/interests**
• **Graduate on time**"""
        suggestions = ["Major requirements", "Electives", "Graduate on time"]
    
    else:  # complete
        response = f"""✅ **All set, {name}!** I've saved your preferences.

📝 {summary}

Click **Go to Dashboard** above to see your personalized schedule, or ask me anything about your degree!"""
        suggestions = ["Show my degree progress", "What courses do I need?", "Go to Dashboard"]
    
    return response, suggestions
