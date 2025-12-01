"""
Models package for EduTrackr backend.
Contains data models and type definitions.
"""
from app.models.schedule_types import (
    ClassSection,
    ConflictInfo,
    DaysOccurring,
    DayOfWeek,
    DegreeRequirement,
    OccurrenceData,
    RequirementBadge,
    RequirementType,
    ScheduleValidation,
    TimeSlot,
    REQUIREMENT_COLORS,
)

__all__ = [
    "ClassSection",
    "ConflictInfo",
    "DaysOccurring",
    "DayOfWeek",
    "DegreeRequirement",
    "OccurrenceData",
    "RequirementBadge",
    "RequirementType",
    "ScheduleValidation",
    "TimeSlot",
    "REQUIREMENT_COLORS",
]
