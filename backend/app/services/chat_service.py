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

    The LLM is instructed to respond in a simple XML envelope that we
    parse server‑side, so the user never sees any internal reasoning.
    """

    # 1. Get PDF Context (student-specific)
    parsed_data = load_parsed_data(email)
    context_str = ""
    parsed_fields: Dict[str, Any] = {}
    if parsed_data and "parsed_data" in parsed_data:
        parsed_fields = parsed_data["parsed_data"] or {}
        context_str = json.dumps(parsed_fields, indent=2)
        print(f"DEBUG: Chat Context Loaded ({len(context_str)} chars)", flush=True)
    else:
        print("DEBUG: Chat Context is EMPTY", flush=True)

    # 1b. Attach official catalog program requirements, if we can match them.
    catalog_context = _build_catalog_context(parsed_fields) if parsed_fields else None
    catalog_str = json.dumps(catalog_context, indent=2) if catalog_context else "null"

    # 1c. Compute requirement status from transcript + catalog requirements.
    degree_status = _compute_degree_status(parsed_fields, catalog_context)
    degree_status_str = json.dumps(degree_status, indent=2) if degree_status else "[]"

    normalized_mode = (mode or "").strip().lower()
    if normalized_mode not in ("upcoming_semester", "four_year_plan", "view_progress"):
        normalized_mode = "undecided"

    # Extract student name if available
    student_info = parsed_fields.get("student_info", {})
    student_name = student_info.get("name", "").split()[0] if student_info.get("name") else ""
    student_name = student_name.replace(",", "").strip()

    if context == "explore":
        system_prompt = f"""
You are a helpful and knowledgeable academic advisor assistant for Chapman University students.
Your goal is to help the student explore their academic options, understand their degree progress, and plan their future.

Student: {student_name or 'Student'}
Current Context:
- Program: {student_info.get('program', 'Unknown')}
- Catalog Year: {student_info.get('catalog_year', 'Unknown')}

**DEGREE STATUS**:
{degree_status_str}

**CATALOG REQUIREMENTS**:
{catalog_str}

**INSTRUCTIONS**:
- Be encouraging, reflective, and helpful.
- Answer questions about their specific degree progress using the provided data.
- If they ask about courses, use the catalog requirements to guide them.
- Keep responses concise (under 150 words) unless a detailed explanation is needed.
- Use markdown for formatting (lists, bolding).

**OUTPUT FORMAT (XML)**:
<response>
  <message>Your response here (markdown supported)</message>
  <suggestions>
    <suggestion>Follow-up question 1</suggestion>
    <suggestion>Follow-up question 2</suggestion>
    <suggestion>Follow-up question 3</suggestion>
  </suggestions>
</response>
"""
    else:
        # Default Onboarding Prompt
        system_prompt = f"""
You are a friendly academic advisor helping onboard a student to EduTrackr.

**YOUR ONLY GOAL**: Quickly gather key information so we can build their schedule AFTER this chat. Do NOT draft schedules or list courses.

Student: {student_name or 'Student'}
Current mode: {normalized_mode}

**FORMATTING RULES** (CRITICAL):
- Use emojis to make questions clear and scannable
- Put each question on its OWN line with a blank line between them
- Use **bold** for key options
- Keep total response under 80 words

**EMOJI GUIDE**:
- 📚 for credit load questions
- ⏰ for schedule/time questions  
- 💼 for work/job questions
- 🌴 for summer questions
- 🎯 for goals/focus questions
- ✅ for confirmations
- 📋 for planning mode choice

**EXAMPLE FORMAT** (follow this structure):
✅ Got it — next semester planning!

📚 **Credit load**: Light (9-12), Standard (12-15), or Heavy (15-18)?

⏰ **Schedule**: Any days to avoid or time preferences?

**WHAT TO COLLECT** (1-2 questions per message):
1. Planning goal (semester/4-year/progress)
2. Credit load preference
3. Schedule constraints (work, time preferences)
4. Summer availability
5. Focus areas (if any)

**FIRST MESSAGE** (if mode is undecided):
Hi {student_name or 'there'}! 👋 I'll ask a few quick questions to personalize your experience.

📋 What would you like to focus on?
- **Next semester** planning
- **Full 4-year** path  
- **View progress** so far

**COMPLETION**: After 3-4 exchanges, say:
✅ Perfect! I have what I need. Click **Go to Dashboard** to see your personalized plan!

**SUGGESTIONS RULES** (CRITICAL):
The 3 suggestions MUST directly answer the question you just asked. Match them to YOUR question:

If you asked about PLANNING MODE → suggestions: "Next semester", "Full 4-year plan", "View my progress"
If you asked about CREDIT LOAD → suggestions: "9-12 credits (Light)", "12-15 credits", "15-18 credits (Heavy)"
If you asked about SCHEDULE → suggestions: "Mornings only", "No Fridays", "Flexible schedule"
If you asked about SUMMER → suggestions: "Yes to summer", "No summer classes", "Maybe one course"
If you asked about WORK/JOBS → suggestions: "I work part-time", "Full-time job", "No work commitments"

OUTPUT FORMAT (XML):
<response>
  <message>Your formatted message with emojis and line breaks</message>
  <suggestions>
    <suggestion>Answer matching your question</suggestion>
    <suggestion>Another valid answer</suggestion>
    <suggestion>Third option</suggestion>
  </suggestions>
</response>

Example for first message (asking about planning mode):
<suggestions>
  <suggestion>Next semester</suggestion>
  <suggestion>Full 4-year plan</suggestion>
  <suggestion>View my progress</suggestion>
</suggestions>
"""

    # 2. Get History
    history = get_chat_history(session_id)

    messages = [{"role": "system", "content": system_prompt}] + history

    if user_message:
        messages.append({"role": "user", "content": user_message})
        save_message(session_id, "user", user_message)

    def _parse_xml_envelope(raw: str) -> (str, List[str]):
        # Trim any accidental markdown fences
        text = raw.strip()
        if text.startswith("```"):
            # remove leading ``` or ```xml
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # If there's any junk before <response>, cut it off
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

        # Ensure max 3 suggestions
        suggestions_local = suggestions_local[:3]
        return reply_text_local, suggestions_local

    # 3. Call LLM
    try:
        if not client.api_key:
            print("Warning: OPENAI_API_KEY not set. Using mock reply.")
            reply_text = "I'm ready to help, but my brain (OpenAI Key) is missing."
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
        reply_text = "I'm having a moment - let me help you another way. What would you like to focus on?"
        suggestions = ["Plan my next semester", "Show my degree progress", "What courses do I need?"]

    # 4. Save Reply (only the text part shown to the user)
    save_message(session_id, "assistant", reply_text)

    return {
        "reply": reply_text,
        "suggestions": suggestions,
    }


def generate_reply_stream(
    user_id: str,
    email: str,
    session_id: str,
    user_message: Optional[str],
    mode: Optional[str] = None,
    context: str = "onboarding"
):
    """Generator that yields streaming chunks for the chat response.
    
    Yields dictionaries with keys:
    - 'type': 'chunk' | 'suggestions' | 'done' | 'error'
    - 'content': the text chunk or suggestions list
    """
    
    # 1. Get PDF Context (student-specific)
    parsed_data = load_parsed_data(email)
    context_str = ""
    parsed_fields: Dict[str, Any] = {}
    if parsed_data and "parsed_data" in parsed_data:
        parsed_fields = parsed_data["parsed_data"] or {}
        context_str = json.dumps(parsed_fields, indent=2)
    
    # 1b. Attach official catalog program requirements
    catalog_context = _build_catalog_context(parsed_fields) if parsed_fields else None
    catalog_str = json.dumps(catalog_context, indent=2) if catalog_context else "null"
    
    # 1c. Compute requirement status
    degree_status = _compute_degree_status(parsed_fields, catalog_context)
    degree_status_str = json.dumps(degree_status, indent=2) if degree_status else "[]"
    
    normalized_mode = (mode or "").strip().lower()
    if normalized_mode not in ("upcoming_semester", "four_year_plan", "view_progress"):
        normalized_mode = "undecided"
    
    # Extract student name if available
    student_info = parsed_fields.get("student_info", {})
    student_name = student_info.get("name", "").split()[0] if student_info.get("name") else ""
    student_name = student_name.replace(",", "").strip()
    
    # 1d. Get current preferences and parse user's response
    current_prefs = get_scheduling_preferences(user_id)
    if user_message and context == "onboarding":
        current_prefs, field_saved = parse_and_save_user_response(user_id, user_message, current_prefs)
    
    # Check if we have enough info
    is_complete, missing_fields = check_onboarding_completeness(current_prefs)
    next_topic = get_next_question_topic(current_prefs)
    collected_summary = get_collected_summary(current_prefs)
    
    if context == "explore":
        system_prompt = f"""
You are a helpful and knowledgeable academic advisor assistant for Chapman University students.
Your goal is to help the student explore their academic options, understand their degree progress, and plan their future.

Student: {student_name or 'Student'}
Current Context:
- Program: {student_info.get('program', 'Unknown')}
- Catalog Year: {student_info.get('catalog_year', 'Unknown')}

**DEGREE STATUS**:
{degree_status_str}

**CATALOG REQUIREMENTS**:
{catalog_str}

**INSTRUCTIONS**:
- Be encouraging, reflective, and helpful.
- Answer questions about their specific degree progress using the provided data.
- If they ask about courses, use the catalog requirements to guide them.
- Keep responses concise (under 150 words) unless a detailed explanation is needed.
- Use markdown for formatting (lists, bolding).
- Do NOT ask the onboarding questions (credit load, work status, etc.) unless relevant to the user's query.

**OUTPUT FORMAT**:
Just respond with your message directly. Do NOT use any special markers like [RESPONSE START] or [RESPONSE END].
You may optionally include follow-up suggestions at the very end using this format:
[SUGGESTIONS]
Suggestion 1
Suggestion 2
Suggestion 3
[/SUGGESTIONS]

If no suggestions, just provide the response text with no special markers.
"""
    else:
        # Build the system prompt - ONE question at a time
        system_prompt = f"""
You are a friendly academic advisor helping onboard a student to EduTrackr.

**YOUR ONLY GOAL**: Collect ONE piece of information at a time. Ask only ONE question per message.

Student: {student_name or 'Student'}
Current mode: {normalized_mode}

**ALREADY COLLECTED** (DO NOT ask about these again):
{collected_summary}

**NEXT TOPIC TO ASK**: {next_topic}
**ONBOARDING COMPLETE**: {is_complete}

**CRITICAL RULES**:
1. Ask only ONE question per message - never two or more
2. Keep responses under 60 words
3. Use emojis for visual clarity
4. Use **bold** for options
5. Be friendly and conversational, not robotic

**EMOJI GUIDE**:
- 📋 planning mode | 📚 credits | ⏰ schedule | 💼 work | 🌴 summer | 🎯 focus | ✅ confirmations

**QUESTION TEMPLATES** (use the one matching next_topic):

If next_topic is "planning_mode":
Hi {student_name or 'there'}! 👋 I'm your academic advisor. I'll ask a few quick questions to personalize your plan.

📋 First, what's your main focus right now?
- **Next semester** planning
- **Full 4-year** path
- **View progress** so far

If next_topic is "credits":
✅ Got it.

📚 How about **credit load**? **Light** (9-12), **Standard** (12-15), or **Heavy** (15-18)?

If next_topic is "time_preference":
✅ Noted.

⏰ When do you prefer classes? **Mornings**, **Afternoons**, **Evenings**, or **Flexible**?

If next_topic is "work_status":
✅ Perfect.

💼 Do you have **work** commitments? **Part-time**, **Full-time**, or **No work**?

If next_topic is "summer":
✅ Great.

🌴 Are you open to **Summer** classes? **Yes**, **No**, or **Maybe one course**?

If next_topic is "focus":
✅ Almost done.

🎯 What's your top **priority**? **Major requirements**, **Electives/interests**, or **Graduate on time**?

If next_topic is "complete" OR is_complete is True:
✅ **All set, {student_name or 'there'}!** I've saved your preferences:

📝 {collected_summary}

I'm ready to help you explore! You can ask me anything about your degree, or click the **Go to Dashboard** button above to see your full plan.

**SUGGESTIONS** (MUST match your question):
- planning_mode: ["Next semester", "Full 4-year plan", "View my progress"]
- credits: ["Light (9-12)", "Standard (12-15)", "Heavy (15-18)"]
- time_preference: ["Mornings", "Afternoons", "Flexible"]
- work_status: ["Part-time work", "Full-time job", "No work"]
- summer: ["Yes to summer", "No summer", "Maybe one course"]
- focus: ["Major requirements", "Electives", "Graduate on time"]
- complete: ["Show my degree progress", "What courses do I need?", "Change preferences"]

OUTPUT: Plain markdown, then on a NEW LINE at the very end:
[SUGGESTIONS: "answer1", "answer2", "answer3"]
"""

    # 2. Get History
    history = get_chat_history(session_id)
    messages = [{"role": "system", "content": system_prompt}] + history

    if user_message:
        messages.append({"role": "user", "content": user_message})
        save_message(session_id, "user", user_message)

    # 3. Stream from LLM
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
                
                # Check if we've hit the suggestions marker
                if "[SUGGESTIONS:" not in full_response:
                    yield {"type": "chunk", "content": text}
        
        # Parse suggestions from the end of the response
        if "[SUGGESTIONS:" in full_response:
            parts = full_response.split("[SUGGESTIONS:")
            clean_response = parts[0].strip()
            suggestions_part = parts[1] if len(parts) > 1 else ""
            
            # Extract suggestions (re is already imported at top of file)
            matches = re.findall(r'"([^"]+)"', suggestions_part)
            suggestions = matches[:3]
            
            # If we streamed the suggestions marker, we need to not save it
            full_response = clean_response
        
        # Save the clean response
        save_message(session_id, "assistant", full_response)
        
        # Send suggestions
        if suggestions:
            yield {"type": "suggestions", "content": suggestions}
        else:
            yield {"type": "suggestions", "content": ["Plan my next semester", "Show my degree progress", "What courses do I need?"]}
            
    except Exception as e:
        print(f"OpenAI Streaming Error: {e}")
        yield {"type": "chunk", "content": "I'm having a moment - let me help you another way. What would you like to focus on?"}
        yield {"type": "suggestions", "content": ["Plan my next semester", "Show my degree progress", "What courses do I need?"]}
