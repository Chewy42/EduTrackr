"""
Classes Service - Handles loading and searching available classes from CSV data.
Provides efficient search, filtering, and caching for the schedule builder.
"""
import ast
import csv
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.models.schedule_types import (
    ClassSection,
    DaysOccurring,
    OccurrenceData,
    TimeSlot,
)

# Path to the available classes CSV
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CLASSES_CSV_PATH = DATA_DIR / "available_classes_spring_2026.csv"


def _parse_time_slot(slot_dict: Dict[str, int]) -> TimeSlot:
    """Parse a time slot dictionary into a TimeSlot object."""
    return TimeSlot(
        start_time=slot_dict.get("startTime", 0),
        end_time=slot_dict.get("endTime", 0),
    )


def _parse_days_occurring(days_dict: Dict[str, List]) -> DaysOccurring:
    """Parse days occurring dictionary into a DaysOccurring object."""
    return DaysOccurring(
        M=[_parse_time_slot(s) for s in days_dict.get("M", [])],
        Tu=[_parse_time_slot(s) for s in days_dict.get("Tu", [])],
        W=[_parse_time_slot(s) for s in days_dict.get("W", [])],
        Th=[_parse_time_slot(s) for s in days_dict.get("Th", [])],
        F=[_parse_time_slot(s) for s in days_dict.get("F", [])],
        Sa=[_parse_time_slot(s) for s in days_dict.get("Sa", [])],
        Su=[_parse_time_slot(s) for s in days_dict.get("Su", [])],
    )


def _parse_occurrence_data(raw: str) -> OccurrenceData:
    """
    Parse the occurrenceData string from CSV into an OccurrenceData object.
    The CSV stores Python dict literals, so we use ast.literal_eval for safe parsing.
    """
    if not raw or raw.strip() == "":
        return OccurrenceData(starts=0, ends=0, days_occurring=DaysOccurring())
    
    try:
        data = ast.literal_eval(raw)
        if data is None or not isinstance(data, dict):
            return OccurrenceData(starts=0, ends=0, days_occurring=DaysOccurring())
        return OccurrenceData(
            starts=data.get("starts", 0) or 0,
            ends=data.get("ends", 0) or 0,
            days_occurring=_parse_days_occurring(data.get("daysOccurring") or {}),
        )
    except (ValueError, SyntaxError) as e:
        # Silently return empty occurrence data for unparseable entries
        return OccurrenceData(starts=0, ends=0, days_occurring=DaysOccurring())


def _parse_semesters_offered(raw: str) -> List[str]:
    """Parse the semestersOffered string into a list."""
    try:
        return ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return []


def _parse_credits(raw: str) -> float:
    """Parse credits, handling variable credit courses like '1-3'."""
    if not raw:
        return 0.0
    # Handle variable credits (e.g., "1-3") by taking the max
    if "-" in raw:
        parts = raw.split("-")
        try:
            return float(parts[-1])
        except ValueError:
            return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _parse_professor_rating(raw: str) -> Optional[float]:
    """Parse professor rating, returning None if not available."""
    if not raw or raw.strip() == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_class_code(class_code: str) -> Tuple[str, str, str]:
    """
    Parse a class code like 'CPSC 350-03' into subject, number, section.
    Returns (subject, number, section).
    """
    # Match patterns like "CPSC 350-03" or "CPSC 350L-01"
    match = re.match(r"([A-Z]+)\s*(\d+[A-Z]?)[-_](\d+)", class_code)
    if match:
        return match.group(1), match.group(2), match.group(3)
    
    # Fallback: try splitting by space and dash
    parts = class_code.replace("-", " ").split()
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    elif len(parts) == 2:
        return parts[0], parts[1], "01"
    
    return class_code, "", ""


def _row_to_class_section(row: Dict[str, str]) -> ClassSection:
    """Convert a CSV row dictionary to a ClassSection object."""
    class_code = row.get("class", "")
    subject, number, section = _parse_class_code(class_code)
    
    # Create a unique ID from the class code
    class_id = class_code.replace(" ", "-").replace("/", "-")
    
    return ClassSection(
        id=class_id,
        code=class_code,
        subject=subject,
        number=number,
        section=section,
        title=row.get("title", ""),
        credits=_parse_credits(row.get("credits", "0")),
        display_days=row.get("displayDays", ""),
        display_time=row.get("displayTime", ""),
        location=row.get("location", ""),
        professor=row.get("professor", "TBA"),
        professor_rating=_parse_professor_rating(row.get("professorRating", "")),
        semester=row.get("semester", ""),
        semesters_offered=_parse_semesters_offered(row.get("semestersOffered", "[]")),
        occurrence_data=_parse_occurrence_data(row.get("occurrenceData", "{}")),
        requirements_satisfied=[],
    )


@lru_cache(maxsize=1)
def load_all_classes() -> List[ClassSection]:
    """
    Load all classes from the CSV file.
    Results are cached for performance.
    """
    classes_map: Dict[str, ClassSection] = {}
    
    if not CLASSES_CSV_PATH.exists():
        print(f"Warning: Classes CSV not found at {CLASSES_CSV_PATH}")
        return []
    
    with open(CLASSES_CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                class_section = _row_to_class_section(row)
                # Use ID as key to deduplicate
                if class_section.id not in classes_map:
                    classes_map[class_section.id] = class_section
            except Exception:
                # Silently skip rows that can't be parsed
                continue
    
    return list(classes_map.values())


def clear_cache() -> None:
    """Clear the classes cache to force reload from CSV."""
    load_all_classes.cache_clear()


def get_class_by_id(class_id: str) -> Optional[ClassSection]:
    """Get a single class by its ID."""
    classes = load_all_classes()
    for cls in classes:
        if cls.id == class_id:
            return cls
    return None


def get_classes_by_ids(class_ids: List[str]) -> List[ClassSection]:
    """Get multiple classes by their IDs."""
    classes = load_all_classes()
    id_set = set(class_ids)
    return [cls for cls in classes if cls.id in id_set]


def search_classes(
    query: Optional[str] = None,
    days: Optional[List[str]] = None,
    time_start: Optional[int] = None,  # Minutes from midnight
    time_end: Optional[int] = None,    # Minutes from midnight
    credits_min: Optional[float] = None,
    credits_max: Optional[float] = None,
    subject: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[ClassSection], int]:
    """
    Search and filter classes based on various criteria.
    
    Args:
        query: Text search (matches code, title, professor)
        days: Filter by days (e.g., ["M", "W", "F"])
        time_start: Minimum start time in minutes from midnight
        time_end: Maximum end time in minutes from midnight
        credits_min: Minimum credits
        credits_max: Maximum credits
        subject: Filter by subject (e.g., "CPSC")
        limit: Maximum results to return
        offset: Pagination offset
    
    Returns:
        Tuple of (matching classes, total count)
    """
    all_classes = load_all_classes()
    filtered: List[ClassSection] = []
    
    query_lower = query.lower().strip() if query else None
    days_set = set(days) if days else None
    subject_upper = subject.upper() if subject else None
    
    for cls in all_classes:
        # Text search filter
        if query_lower:
            searchable = f"{cls.code} {cls.title} {cls.professor}".lower()
            if query_lower not in searchable:
                continue
        
        # Subject filter
        if subject_upper and cls.subject != subject_upper:
            continue
        
        # Credits filter
        if credits_min is not None and cls.credits < credits_min:
            continue
        if credits_max is not None and cls.credits > credits_max:
            continue
        
        # Days filter
        if days_set:
            class_days = set(cls.occurrence_data.days_occurring.get_active_days())
            if not class_days.intersection(days_set):
                continue
        
        # Time filter
        if time_start is not None or time_end is not None:
            class_matches_time = False
            days_data = cls.occurrence_data.days_occurring
            
            for day in ["M", "Tu", "W", "Th", "F", "Sa", "Su"]:
                slots = getattr(days_data, day)
                for slot in slots:
                    slot_ok = True
                    if time_start is not None and slot.start_time < time_start:
                        slot_ok = False
                    if time_end is not None and slot.end_time > time_end:
                        slot_ok = False
                    if slot_ok:
                        class_matches_time = True
                        break
                if class_matches_time:
                    break
            
            if not class_matches_time:
                continue
        
        filtered.append(cls)
    
    total = len(filtered)
    
    # Apply pagination
    paginated = filtered[offset:offset + limit]
    
    return paginated, total


def get_unique_subjects() -> List[str]:
    """Get a list of unique subjects from all classes."""
    classes = load_all_classes()
    subjects = sorted(set(cls.subject for cls in classes if cls.subject))
    return subjects


def get_classes_by_subject(subject: str) -> List[ClassSection]:
    """Get all classes for a specific subject."""
    classes = load_all_classes()
    subject_upper = subject.upper()
    return [cls for cls in classes if cls.subject == subject_upper]


def validate_schedule(class_ids: List[str]) -> Dict[str, Any]:
    """
    Validate a schedule for conflicts and credit totals.
    
    Args:
        class_ids: List of class IDs in the schedule
    
    Returns:
        Dictionary with validation results
    """
    classes = get_classes_by_ids(class_ids)
    conflicts = []
    total_credits = sum(cls.credits for cls in classes)
    warnings = []
    
    # Check for time conflicts
    for i, cls1 in enumerate(classes):
        for cls2 in classes[i + 1:]:
            if cls1.has_conflict_with(cls2):
                # Find the conflicting day and time
                conflict_day = ""
                conflict_time = ""
                
                days_data1 = cls1.occurrence_data.days_occurring
                days_data2 = cls2.occurrence_data.days_occurring
                
                for day in ["M", "Tu", "W", "Th", "F", "Sa", "Su"]:
                    slots1 = getattr(days_data1, day)
                    slots2 = getattr(days_data2, day)
                    
                    for slot1 in slots1:
                        for slot2 in slots2:
                            if slot1.overlaps(slot2):
                                conflict_day = day
                                conflict_time = f"{_minutes_to_time(max(slot1.start_time, slot2.start_time))} - {_minutes_to_time(min(slot1.end_time, slot2.end_time))}"
                                break
                        if conflict_day:
                            break
                    if conflict_day:
                        break
                
                conflicts.append({
                    "classId1": cls1.id,
                    "classId2": cls2.id,
                    "day": conflict_day,
                    "timeRange": conflict_time,
                    "message": f"{cls1.code} conflicts with {cls2.code} on {conflict_day}",
                })
    
    # Add warnings
    if total_credits > 18:
        warnings.append(f"Schedule has {total_credits} credits, which exceeds the typical maximum of 18.")
    elif total_credits < 12:
        warnings.append(f"Schedule has {total_credits} credits, which may be below full-time status (12 credits).")
    
    return {
        "valid": len(conflicts) == 0,
        "conflicts": conflicts,
        "totalCredits": total_credits,
        "warnings": warnings,
    }


def _minutes_to_time(minutes: int) -> str:
    """Convert minutes from midnight to a time string like '10:30 AM'."""
    hours = minutes // 60
    mins = minutes % 60
    period = "AM" if hours < 12 else "PM"
    if hours == 0:
        hours = 12
    elif hours > 12:
        hours -= 12
    return f"{hours}:{mins:02d} {period}"
