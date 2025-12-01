"""
Type definitions for the schedule builder feature.
Provides strict typing for classes, time slots, and degree requirements.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class DayOfWeek(str, Enum):
    """Days of the week for class scheduling."""
    MONDAY = "M"
    TUESDAY = "Tu"
    WEDNESDAY = "W"
    THURSDAY = "Th"
    FRIDAY = "F"
    SATURDAY = "Sa"
    SUNDAY = "Su"


class RequirementType(str, Enum):
    """Types of degree requirements."""
    MAJOR_CORE = "major_core"
    MAJOR_ELECTIVE = "major_elective"
    GENERAL_EDUCATION = "ge"
    MINOR = "minor"
    CONCENTRATION = "concentration"
    OTHER = "other"


@dataclass
class TimeSlot:
    """A single time slot within a day."""
    start_time: int  # Minutes from midnight (e.g., 540 = 9:00 AM)
    end_time: int    # Minutes from midnight (e.g., 590 = 9:50 AM)
    
    def overlaps(self, other: "TimeSlot") -> bool:
        """Check if this time slot overlaps with another."""
        return self.start_time < other.end_time and self.end_time > other.start_time
    
    def to_dict(self) -> Dict[str, int]:
        return {"startTime": self.start_time, "endTime": self.end_time}


@dataclass
class DaysOccurring:
    """Time slots for each day of the week."""
    M: List[TimeSlot] = field(default_factory=list)
    Tu: List[TimeSlot] = field(default_factory=list)
    W: List[TimeSlot] = field(default_factory=list)
    Th: List[TimeSlot] = field(default_factory=list)
    F: List[TimeSlot] = field(default_factory=list)
    Sa: List[TimeSlot] = field(default_factory=list)
    Su: List[TimeSlot] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, List[Dict[str, int]]]:
        return {
            "M": [slot.to_dict() for slot in self.M],
            "Tu": [slot.to_dict() for slot in self.Tu],
            "W": [slot.to_dict() for slot in self.W],
            "Th": [slot.to_dict() for slot in self.Th],
            "F": [slot.to_dict() for slot in self.F],
            "Sa": [slot.to_dict() for slot in self.Sa],
            "Su": [slot.to_dict() for slot in self.Su],
        }
    
    def get_active_days(self) -> List[str]:
        """Get list of days that have time slots."""
        active = []
        if self.M: active.append("M")
        if self.Tu: active.append("Tu")
        if self.W: active.append("W")
        if self.Th: active.append("Th")
        if self.F: active.append("F")
        if self.Sa: active.append("Sa")
        if self.Su: active.append("Su")
        return active


@dataclass
class OccurrenceData:
    """Full occurrence data for a class section."""
    starts: int  # Unix timestamp
    ends: int    # Unix timestamp
    days_occurring: DaysOccurring = field(default_factory=DaysOccurring)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "starts": self.starts,
            "ends": self.ends,
            "daysOccurring": self.days_occurring.to_dict(),
        }


@dataclass
class ClassSection:
    """
    A single class section from the available classes CSV.
    This represents one specific offering of a course (e.g., CPSC 350-03).
    """
    id: str                          # Unique ID: "CPSC-350-03"
    code: str                        # Display code: "CPSC 350-03"
    subject: str                     # Subject: "CPSC"
    number: str                      # Course number: "350"
    section: str                     # Section: "03"
    title: str                       # Course title
    credits: float                   # Credit hours
    display_days: str                # e.g., "MWF", "TuTh"
    display_time: str                # e.g., "10:00am - 10:50am"
    location: str                    # Room/building
    professor: str                   # Instructor name
    professor_rating: Optional[float]  # RateMyProfessor rating
    semester: str                    # e.g., "spring2026"
    semesters_offered: List[str]     # e.g., ["Spring", "Fall"]
    occurrence_data: OccurrenceData  # Time slot data
    requirements_satisfied: List[str] = field(default_factory=list)  # Matched requirements
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "subject": self.subject,
            "number": self.number,
            "section": self.section,
            "title": self.title,
            "credits": self.credits,
            "displayDays": self.display_days,
            "displayTime": self.display_time,
            "location": self.location,
            "professor": self.professor,
            "professorRating": self.professor_rating,
            "semester": self.semester,
            "semestersOffered": self.semesters_offered,
            "occurrenceData": self.occurrence_data.to_dict(),
            "requirementsSatisfied": self.requirements_satisfied,
        }
    
    def has_conflict_with(self, other: "ClassSection") -> bool:
        """Check if this class has a time conflict with another."""
        my_days = self.occurrence_data.days_occurring
        other_days = other.occurrence_data.days_occurring
        
        for day in ["M", "Tu", "W", "Th", "F", "Sa", "Su"]:
            my_slots = getattr(my_days, day)
            other_slots = getattr(other_days, day)
            
            for my_slot in my_slots:
                for other_slot in other_slots:
                    if my_slot.overlaps(other_slot):
                        return True
        
        return False


@dataclass
class DegreeRequirement:
    """A single degree requirement that the student still needs."""
    type: RequirementType
    label: str                       # Display label
    subject: Optional[str] = None    # Required subject (for specific courses)
    number: Optional[str] = None     # Required course number
    title: Optional[str] = None      # Course title hint
    credits_needed: float = 0        # Credits still needed
    area: Optional[str] = None       # GE area (e.g., "Written Inquiry")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "label": self.label,
            "subject": self.subject,
            "number": self.number,
            "title": self.title,
            "creditsNeeded": self.credits_needed,
            "area": self.area,
        }


@dataclass
class RequirementBadge:
    """A badge to display on a class card showing what requirement it satisfies."""
    type: RequirementType
    label: str
    short_label: str  # e.g., "Core", "GE-WI"
    color: str        # CSS color class
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "type": self.type.value,
            "label": self.label,
            "shortLabel": self.short_label,
            "color": self.color,
        }


@dataclass
class ConflictInfo:
    """Information about a schedule conflict."""
    class_id_1: str
    class_id_2: str
    day: str
    time_range: str  # e.g., "10:00 AM - 11:00 AM"
    message: str
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "classId1": self.class_id_1,
            "classId2": self.class_id_2,
            "day": self.day,
            "timeRange": self.time_range,
            "message": self.message,
        }


@dataclass
class ScheduleValidation:
    """Result of schedule validation."""
    valid: bool
    conflicts: List[ConflictInfo]
    total_credits: float
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "totalCredits": self.total_credits,
            "warnings": self.warnings,
        }


# Color mapping for requirement badges
REQUIREMENT_COLORS = {
    RequirementType.MAJOR_CORE: "blue",
    RequirementType.MAJOR_ELECTIVE: "indigo",
    RequirementType.GENERAL_EDUCATION: "green",
    RequirementType.MINOR: "purple",
    RequirementType.CONCENTRATION: "orange",
    RequirementType.OTHER: "gray",
}
