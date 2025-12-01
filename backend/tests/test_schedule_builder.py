"""
Unit tests for the schedule builder feature.
Tests classes service, degree requirements matcher, and schedule routes.
"""
import pytest
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock

from app.services.classes_service import (
    load_all_classes,
    search_classes,
    get_class_by_id,
    get_classes_by_ids,
    validate_schedule,
    _parse_class_code,
    _parse_occurrence_data,
    _minutes_to_time,
    clear_cache,
)
from app.services.degree_requirements_matcher import (
    extract_user_requirements,
    match_class_to_requirements,
    enrich_classes_with_requirements,
    get_requirement_summary,
    _normalize_course_code,
    _get_short_label,
    _is_ge_course,
)
from app.models.schedule_types import (
    ClassSection,
    DegreeRequirement,
    RequirementType,
    ScheduleSnapshot,
    TimeSlot,
    DaysOccurring,
    OccurrenceData,
)
from app.services.schedule_snapshot_service import (
    save_snapshot,
    list_snapshots,
    get_snapshot,
    delete_snapshot,
    update_snapshot,
    DuplicateNameError,
    SnapshotError,
)


class TestClassCodeParsing:
    """Tests for class code parsing functions."""
    
    def test_parse_standard_code(self):
        """Test parsing standard class codes like 'CPSC 350-03'."""
        subject, number, section = _parse_class_code("CPSC 350-03")
        assert subject == "CPSC"
        assert number == "350"
        assert section == "03"
    
    def test_parse_code_with_letter(self):
        """Test parsing codes with letters like 'BIOL 205L-01'."""
        subject, number, section = _parse_class_code("BIOL 205L-01")
        assert subject == "BIOL"
        assert number == "205L"
        assert section == "01"
    
    def test_parse_code_no_section(self):
        """Test parsing codes without section numbers."""
        subject, number, section = _parse_class_code("MATH 110")
        assert subject == "MATH"
        assert number == "110"
    
    def test_normalize_course_code(self):
        """Test course code normalization."""
        assert _normalize_course_code("CPSC 350") == ("CPSC", "350")
        assert _normalize_course_code("cpsc350") == ("CPSC", "350")
        assert _normalize_course_code("CPSC 350-03") == ("CPSC", "350")


class TestOccurrenceDataParsing:
    """Tests for occurrence data parsing."""
    
    def test_parse_valid_occurrence_data(self):
        """Test parsing valid occurrence data string."""
        raw = "{'starts': 1769155200, 'ends': 1778310000, 'daysOccurring': {'M': [{'startTime': 540, 'endTime': 590}], 'Tu': [], 'W': [{'startTime': 540, 'endTime': 590}], 'Th': [], 'F': [{'startTime': 540, 'endTime': 590}], 'Sa': [], 'Su': []}}"
        result = _parse_occurrence_data(raw)
        
        assert result.starts == 1769155200
        assert result.ends == 1778310000
        assert len(result.days_occurring.M) == 1
        assert result.days_occurring.M[0].start_time == 540
        assert result.days_occurring.M[0].end_time == 590
    
    def test_parse_empty_occurrence_data(self):
        """Test parsing empty occurrence data."""
        result = _parse_occurrence_data("{}")
        assert result.starts == 0
        assert result.ends == 0
    
    def test_parse_invalid_occurrence_data(self):
        """Test parsing invalid occurrence data."""
        result = _parse_occurrence_data("invalid")
        assert result.starts == 0


class TestMinutesToTime:
    """Tests for time conversion."""
    
    def test_morning_time(self):
        """Test converting morning times."""
        assert _minutes_to_time(540) == "9:00 AM"
        assert _minutes_to_time(600) == "10:00 AM"
    
    def test_afternoon_time(self):
        """Test converting afternoon times."""
        assert _minutes_to_time(780) == "1:00 PM"
        assert _minutes_to_time(870) == "2:30 PM"
    
    def test_noon(self):
        """Test noon conversion."""
        assert _minutes_to_time(720) == "12:00 PM"
    
    def test_midnight(self):
        """Test midnight conversion."""
        assert _minutes_to_time(0) == "12:00 AM"


class TestClassesService:
    """Tests for the classes service."""
    
    @pytest.fixture(autouse=True)
    def clear_class_cache(self):
        """Clear the class cache before each test."""
        clear_cache()
        yield
        clear_cache()
    
    def test_load_all_classes(self):
        """Test loading all classes from CSV."""
        classes = load_all_classes()
        assert len(classes) > 0
        
        # Check first class has required fields
        first = classes[0]
        assert first.id
        assert first.code
        assert first.subject
        assert first.title
    
    def test_search_by_query(self):
        """Test searching classes by text query."""
        results, total = search_classes(query="computer science")
        # Should find some results
        assert total >= 0
    
    def test_search_by_subject(self):
        """Test filtering classes by subject."""
        results, total = search_classes(subject="CPSC", limit=100)
        # All results should be CPSC
        for cls in results:
            assert cls.subject == "CPSC"
    
    def test_search_pagination(self):
        """Test search pagination."""
        results1, total1 = search_classes(limit=10, offset=0)
        results2, total2 = search_classes(limit=10, offset=10)
        
        assert total1 == total2  # Total should be same
        assert len(results1) <= 10
        assert len(results2) <= 10
        
        # Results should be different
        if len(results1) > 0 and len(results2) > 0:
            assert results1[0].id != results2[0].id
    
    def test_get_class_by_id(self):
        """Test getting a single class by ID."""
        classes = load_all_classes()
        if len(classes) > 0:
            first_id = classes[0].id
            result = get_class_by_id(first_id)
            assert result is not None
            assert result.id == first_id
    
    def test_get_nonexistent_class(self):
        """Test getting a class that doesn't exist."""
        result = get_class_by_id("NONEXISTENT-999-99")
        assert result is None


class TestTimeSlotConflicts:
    """Tests for time slot conflict detection."""
    
    def test_overlapping_slots(self):
        """Test detection of overlapping time slots."""
        slot1 = TimeSlot(start_time=540, end_time=630)  # 9:00-10:30
        slot2 = TimeSlot(start_time=600, end_time=690)  # 10:00-11:30
        
        assert slot1.overlaps(slot2)
        assert slot2.overlaps(slot1)
    
    def test_non_overlapping_slots(self):
        """Test non-overlapping time slots."""
        slot1 = TimeSlot(start_time=540, end_time=590)  # 9:00-9:50
        slot2 = TimeSlot(start_time=600, end_time=650)  # 10:00-10:50
        
        assert not slot1.overlaps(slot2)
        assert not slot2.overlaps(slot1)
    
    def test_adjacent_slots_no_overlap(self):
        """Test that adjacent slots don't overlap."""
        slot1 = TimeSlot(start_time=540, end_time=600)  # 9:00-10:00
        slot2 = TimeSlot(start_time=600, end_time=660)  # 10:00-11:00
        
        assert not slot1.overlaps(slot2)


class TestScheduleValidation:
    """Tests for schedule validation."""
    
    def test_validate_empty_schedule(self):
        """Test validating an empty schedule."""
        result = validate_schedule([])
        assert result["valid"] is True
        assert result["totalCredits"] == 0
        assert len(result["conflicts"]) == 0


class TestDegreeRequirementsMatcher:
    """Tests for degree requirements matching."""
    
    def test_extract_requirements_from_empty_evaluation(self):
        """Test extracting requirements from empty evaluation."""
        requirements = extract_user_requirements({})
        assert isinstance(requirements, list)
    
    def test_extract_remaining_required_courses(self):
        """Test extracting requirements from remaining_required courses."""
        parsed_data = {
            "courses": {
                "remaining_required": [
                    {"subject": "CPSC", "number": "350", "title": "Data Structures", "credits": 3, "requirement_type": "major_core"},
                    {"subject": "MATH", "number": "210", "title": "Calculus III", "credits": 4, "requirement_type": "major_core"},
                ]
            }
        }
        
        requirements = extract_user_requirements(parsed_data)
        assert len(requirements) >= 2
        
        # Check that subjects are extracted
        subjects = [req.subject for req in requirements if req.subject]
        assert "CPSC" in subjects
        assert "MATH" in subjects
    
    def test_get_short_label(self):
        """Test getting short labels for requirement badges."""
        assert _get_short_label(RequirementType.MAJOR_CORE, "Core") == "Core"
        assert _get_short_label(RequirementType.MAJOR_ELECTIVE, "Elective") == "Elective"
        assert _get_short_label(RequirementType.GENERAL_EDUCATION, "Written Inquiry") == "GE-WI"
        assert _get_short_label(RequirementType.GENERAL_EDUCATION, "Quantitative Inquiry") == "GE-QI"
    
    def test_is_ge_course(self):
        """Test GE course identification."""
        assert _is_ge_course("ENG", "103", "Written Inquiry") is True
        assert _is_ge_course("MATH", "110", "Quantitative Inquiry") is True
        assert _is_ge_course("BIOL", "101", "Scientific Inquiry") is True
        assert _is_ge_course("CPSC", "350", "Written Inquiry") is False
    
    def test_match_direct_course(self):
        """Test matching a class directly to a requirement."""
        # Create a mock class
        class_section = ClassSection(
            id="CPSC-350-01",
            code="CPSC 350-01",
            subject="CPSC",
            number="350",
            section="01",
            title="Data Structures",
            credits=3,
            display_days="MWF",
            display_time="10:00am - 10:50am",
            location="TBA",
            professor="TBA",
            professor_rating=None,
            semester="spring2026",
            semesters_offered=["Spring"],
            occurrence_data=OccurrenceData(starts=0, ends=0, days_occurring=DaysOccurring()),
        )
        
        requirements = [
            DegreeRequirement(
                type=RequirementType.MAJOR_CORE,
                label="CPSC 350",
                subject="CPSC",
                number="350",
                credits_needed=3,
            )
        ]
        
        badges = match_class_to_requirements(class_section, requirements)
        assert len(badges) == 1
        assert badges[0].type == RequirementType.MAJOR_CORE
    
    def test_match_graduate_course(self):
        """Test matching a graduate-level class (500+) to a graduate requirement."""
        # Create a 500-level graduate class
        grad_class = ClassSection(
            id="CPSC-510-01",
            code="CPSC 510-01",
            subject="CPSC",
            number="510",
            section="01",
            title="Advanced Algorithms",
            credits=3,
            display_days="TuTh",
            display_time="5:30pm - 6:45pm",
            location="TBA",
            professor="TBA",
            professor_rating=None,
            semester="spring2026",
            semesters_offered=["Spring"],
            occurrence_data=OccurrenceData(starts=0, ends=0, days_occurring=DaysOccurring()),
        )
        
        # Create a 200-level undergrad class
        undergrad_class = ClassSection(
            id="CPSC-230-01",
            code="CPSC 230-01",
            subject="CPSC",
            number="230",
            section="01",
            title="Data Structures",
            credits=3,
            display_days="MWF",
            display_time="10:00am - 10:50am",
            location="TBA",
            professor="TBA",
            professor_rating=None,
            semester="spring2026",
            semesters_offered=["Spring"],
            occurrence_data=OccurrenceData(starts=0, ends=0, days_occurring=DaysOccurring()),
        )
        
        # Graduate requirement (e.g., "Graduate CPSC 500-level Elective")
        grad_requirements = [
            DegreeRequirement(
                type=RequirementType.MAJOR_ELECTIVE,
                label="Graduate CPSC 500",
                subject="CPSC",
                credits_needed=3,
            )
        ]
        
        # Graduate class should match graduate requirement
        grad_badges = match_class_to_requirements(grad_class, grad_requirements)
        assert len(grad_badges) == 1
        assert grad_badges[0].type == RequirementType.MAJOR_ELECTIVE
        
        # Undergrad class should NOT match graduate requirement
        undergrad_badges = match_class_to_requirements(undergrad_class, grad_requirements)
        assert len(undergrad_badges) == 0
    
    def test_match_subject_elective(self):
        """Test matching classes to subject-only elective requirements."""
        # 1-credit seminar class
        seminar_class = ClassSection(
            id="CPSC-590-01",
            code="CPSC 590-01",
            subject="CPSC",
            number="590",
            section="01",
            title="Graduate Seminar",
            credits=1,
            display_days="F",
            display_time="3:00pm - 3:50pm",
            location="TBA",
            professor="TBA",
            professor_rating=None,
            semester="spring2026",
            semesters_offered=["Spring"],
            occurrence_data=OccurrenceData(starts=0, ends=0, days_occurring=DaysOccurring()),
        )
        
        # Subject elective requirement for any CPSC 500-level
        requirements = [
            DegreeRequirement(
                type=RequirementType.MAJOR_ELECTIVE,
                label="CPSC 500 Elective",
                subject="CPSC",
                credits_needed=1,
            )
        ]
        
        badges = match_class_to_requirements(seminar_class, requirements)
        assert len(badges) == 1
    
    def test_requirement_summary(self):
        """Test requirement summary generation."""
        requirements = [
            DegreeRequirement(type=RequirementType.MAJOR_CORE, label="Course 1"),
            DegreeRequirement(type=RequirementType.MAJOR_CORE, label="Course 2"),
            DegreeRequirement(type=RequirementType.GENERAL_EDUCATION, label="GE Course"),
        ]
        
        summary = get_requirement_summary(requirements)
        assert summary["total"] == 3
        assert summary["byType"]["major_core"] == 2
        assert summary["byType"]["ge"] == 1


class TestScheduleRoutes:
    """Integration tests for schedule API routes."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        from app.main import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_get_classes_endpoint(self, client):
        """Test the GET /api/schedule/classes endpoint."""
        response = client.get('/schedule/classes')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'classes' in data
        assert 'total' in data
        assert isinstance(data['classes'], list)
    
    def test_get_classes_with_search(self, client):
        """Test searching classes via API."""
        response = client.get('/schedule/classes?search=accounting')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'classes' in data
    
    def test_get_classes_with_filters(self, client):
        """Test filtering classes via API."""
        response = client.get('/schedule/classes?days=M,W,F&credits_min=3')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'classes' in data
    
    def test_get_subjects_endpoint(self, client):
        """Test the GET /api/schedule/subjects endpoint."""
        response = client.get('/schedule/subjects')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'subjects' in data
        assert isinstance(data['subjects'], list)
    
    def test_get_stats_endpoint(self, client):
        """Test the GET /api/schedule/stats endpoint."""
        response = client.get('/schedule/stats')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'totalClasses' in data
        assert 'subjects' in data
        assert 'avgCredits' in data
    
    def test_validate_schedule_endpoint(self, client):
        """Test the POST /api/schedule/validate endpoint."""
        response = client.post(
            '/schedule/validate',
            json={'classes': []},
            content_type='application/json'
        )
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['valid'] is True
        assert data['totalCredits'] == 0
    
    def test_get_nonexistent_class(self, client):
        """Test getting a class that doesn't exist."""
        response = client.get('/schedule/classes/NONEXISTENT-999-99')
        assert response.status_code == 404


# ============================================================================
# Schedule Snapshot Tests
# ============================================================================

class TestScheduleSnapshotModel:
    """Tests for the ScheduleSnapshot dataclass."""

    def test_to_dict_returns_camel_case_keys(self):
        """Test that to_dict() returns camelCase keys for API responses."""
        snapshot = ScheduleSnapshot(
            id="test-uuid-123",
            user_id="user-uuid-456",
            name="My Test Schedule",
            class_ids=["CPSC-350-01", "MATH-210-02"],
            total_credits=6.0,
            class_count=2,
            created_at="2024-01-15T10:30:00Z",
            updated_at="2024-01-15T10:30:00Z",
        )

        result = snapshot.to_dict()

        assert result["id"] == "test-uuid-123"
        assert result["userId"] == "user-uuid-456"
        assert result["name"] == "My Test Schedule"
        assert result["classIds"] == ["CPSC-350-01", "MATH-210-02"]
        assert result["totalCredits"] == 6.0
        assert result["classCount"] == 2
        assert result["createdAt"] == "2024-01-15T10:30:00Z"
        assert result["updatedAt"] == "2024-01-15T10:30:00Z"

    def test_from_db_row_parses_correctly(self):
        """Test that from_db_row() correctly parses database rows."""
        db_row = {
            "id": "db-uuid-789",
            "user_id": "user-uuid-abc",
            "name": "Spring 2024",
            "schedule_data": {
                "class_ids": ["BIOL-101-01"],
                "total_credits": 4.0,
                "class_count": 1,
            },
            "created_at": "2024-02-01T08:00:00Z",
            "updated_at": "2024-02-01T09:00:00Z",
        }

        snapshot = ScheduleSnapshot.from_db_row(db_row)

        assert snapshot.id == "db-uuid-789"
        assert snapshot.user_id == "user-uuid-abc"
        assert snapshot.name == "Spring 2024"
        assert snapshot.class_ids == ["BIOL-101-01"]
        assert snapshot.total_credits == 4.0
        assert snapshot.class_count == 1

    def test_from_db_row_handles_string_json(self):
        """Test that from_db_row() handles schedule_data as JSON string."""
        import json
        db_row = {
            "id": "test-id",
            "user_id": "test-user",
            "name": "Test",
            "schedule_data": json.dumps({
                "class_ids": ["A", "B"],
                "total_credits": 8.0,
                "class_count": 2,
            }),
            "created_at": "",
            "updated_at": "",
        }

        snapshot = ScheduleSnapshot.from_db_row(db_row)

        assert snapshot.class_ids == ["A", "B"]
        assert snapshot.total_credits == 8.0


class TestScheduleSnapshotService:
    """Tests for the schedule snapshot service functions."""

    @patch('app.services.schedule_snapshot_service.supabase_request')
    def test_save_snapshot_success(self, mock_request):
        """Test saving a snapshot successfully."""
        # Mock user lookup
        mock_request.side_effect = [
            MagicMock(status_code=200, json=lambda: [{"id": "user-123"}]),
            MagicMock(status_code=201, json=lambda: [{
                "id": "snap-456",
                "user_id": "user-123",
                "name": "Test Schedule",
                "schedule_data": {
                    "class_ids": ["CPSC-350-01"],
                    "total_credits": 3.0,
                    "class_count": 1,
                },
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }]),
        ]

        result = save_snapshot("test@example.com", "Test Schedule", ["CPSC-350-01"], 3.0)

        assert result.id == "snap-456"
        assert result.name == "Test Schedule"
        assert result.class_ids == ["CPSC-350-01"]

    @patch('app.services.schedule_snapshot_service.supabase_request')
    def test_save_snapshot_duplicate_name_error(self, mock_request):
        """Test that duplicate name raises DuplicateNameError."""
        mock_request.side_effect = [
            MagicMock(status_code=200, json=lambda: [{"id": "user-123"}]),
            MagicMock(status_code=409, text="duplicate key"),
        ]

        with pytest.raises(DuplicateNameError):
            save_snapshot("test@example.com", "Existing Name", [], 0)

    @patch('app.services.schedule_snapshot_service.supabase_request')
    def test_list_snapshots_returns_list(self, mock_request):
        """Test listing snapshots returns a list of ScheduleSnapshot objects."""
        mock_request.side_effect = [
            MagicMock(status_code=200, json=lambda: [{"id": "user-123"}]),
            MagicMock(status_code=200, json=lambda: [
                {
                    "id": "snap-1",
                    "user_id": "user-123",
                    "name": "Schedule A",
                    "schedule_data": {"class_ids": [], "total_credits": 0, "class_count": 0},
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                },
                {
                    "id": "snap-2",
                    "user_id": "user-123",
                    "name": "Schedule B",
                    "schedule_data": {"class_ids": ["X"], "total_credits": 3, "class_count": 1},
                    "created_at": "2024-01-02T00:00:00Z",
                    "updated_at": "2024-01-02T00:00:00Z",
                },
            ]),
        ]

        result = list_snapshots("test@example.com")

        assert len(result) == 2
        assert result[0].name == "Schedule A"
        assert result[1].name == "Schedule B"

    @patch('app.services.schedule_snapshot_service.supabase_request')
    def test_delete_snapshot_success(self, mock_request):
        """Test deleting a snapshot returns True on success."""
        mock_request.side_effect = [
            MagicMock(status_code=200, json=lambda: [{"id": "user-123"}]),
            MagicMock(status_code=204),
        ]

        result = delete_snapshot("test@example.com", "snap-to-delete")

        assert result is True


class TestScheduleSnapshotRoutes:
    """Tests for the schedule snapshot API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the Flask app."""
        from app.main import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_create_snapshot_requires_auth(self, client):
        """Test that POST /schedule/snapshots requires authentication."""
        response = client.post(
            '/schedule/snapshots',
            json={'name': 'Test', 'class_ids': [], 'total_credits': 0},
            content_type='application/json'
        )
        assert response.status_code == 401

    def test_list_snapshots_requires_auth(self, client):
        """Test that GET /schedule/snapshots requires authentication."""
        response = client.get('/schedule/snapshots')
        assert response.status_code == 401

    def test_get_snapshot_requires_auth(self, client):
        """Test that GET /schedule/snapshots/<id> requires authentication."""
        response = client.get('/schedule/snapshots/some-uuid')
        assert response.status_code == 401

    def test_delete_snapshot_requires_auth(self, client):
        """Test that DELETE /schedule/snapshots/<id> requires authentication."""
        response = client.delete('/schedule/snapshots/some-uuid')
        assert response.status_code == 401

    def test_update_snapshot_requires_auth(self, client):
        """Test that PATCH /schedule/snapshots/<id> requires authentication."""
        response = client.patch(
            '/schedule/snapshots/some-uuid',
            json={'name': 'New Name'},
            content_type='application/json'
        )
        assert response.status_code == 401


class TestEecsRequirementBadges:
    """Tests for EECS-specific requirement badge matching."""

    def test_ethics_core_badge(self):
        """ENGR 501 should get Ethics Core badge."""
        from app.services.degree_requirements_matcher import get_eecs_requirement_badge
        
        badge = get_eecs_requirement_badge("ENGR 501")
        assert badge is not None
        assert badge.label == "Ethics Core"
        assert badge.short_label == "Ethics"
        assert badge.type == RequirementType.MAJOR_CORE

    def test_leadership_core_badge(self):
        """ENGR 520 should get Leadership Core badge."""
        from app.services.degree_requirements_matcher import get_eecs_requirement_badge
        
        badge = get_eecs_requirement_badge("ENGR 520")
        assert badge is not None
        assert badge.label == "Leadership Core"
        assert badge.short_label == "Lead"
        assert badge.type == RequirementType.MAJOR_CORE

    def test_technical_core_ds_badge(self):
        """CPSC 542 should get Technical Core - Data Science badge."""
        from app.services.degree_requirements_matcher import get_eecs_requirement_badge
        
        badge = get_eecs_requirement_badge("CPSC 542")
        assert badge is not None
        assert badge.label == "Technical Core - Data Science & AI"
        assert badge.short_label == "Tech-DS"
        assert badge.type == RequirementType.MAJOR_ELECTIVE

    def test_technical_core_cs_badge(self):
        """CPSC 510 should get Technical Core - Computing Systems badge."""
        from app.services.degree_requirements_matcher import get_eecs_requirement_badge
        
        badge = get_eecs_requirement_badge("CPSC 510")
        assert badge is not None
        assert badge.label == "Technical Core - Computing Systems"
        assert badge.short_label == "Tech-CS"
        assert badge.type == RequirementType.MAJOR_ELECTIVE

    def test_technical_core_ee_badge(self):
        """EENG 514 should get Technical Core - Electrical Systems badge."""
        from app.services.degree_requirements_matcher import get_eecs_requirement_badge
        
        badge = get_eecs_requirement_badge("EENG 514")
        assert badge is not None
        assert badge.label == "Technical Core - Electrical Systems"
        assert badge.short_label == "Tech-EE"
        assert badge.type == RequirementType.MAJOR_ELECTIVE

    def test_non_eecs_course_no_badge(self):
        """CS 533 (Computational Science, not EECS) should NOT get a badge."""
        from app.services.degree_requirements_matcher import get_eecs_requirement_badge
        
        badge = get_eecs_requirement_badge("CS 533")
        assert badge is None

    def test_non_eecs_course_cs_770_no_badge(self):
        """CS 770 (Computational Science, not EECS) should NOT get a badge."""
        from app.services.degree_requirements_matcher import get_eecs_requirement_badge
        
        badge = get_eecs_requirement_badge("CS 770")
        assert badge is None

    def test_enrich_classes_with_eecs_requirements(self):
        """Test that EECS classes get enriched with badges."""
        from app.services.degree_requirements_matcher import enrich_classes_with_eecs_requirements
        from app.models.schedule_types import DaysOccurring, OccurrenceData
        
        # Create test class section
        cls = ClassSection(
            id="ENGR-501-01",
            code="ENGR 501-01",
            subject="ENGR",
            number="501",
            section="01",
            title="Engineering Ethics",
            credits=3.0,
            display_days="MW",
            display_time="10:00am - 10:50am",
            location="HAR 101",
            professor="Smith",
            professor_rating=4.5,
            semester="spring2026",
            semesters_offered=["Spring"],
            occurrence_data=OccurrenceData(
                starts=600,  # 10:00am in minutes
                ends=650,    # 10:50am in minutes
                days_occurring=DaysOccurring(),
            ),
        )
        
        classes = [cls]
        result = enrich_classes_with_eecs_requirements(classes, "M.S. Electrical Engineering and Computer Science")
        
        assert len(result) == 1
        assert result[0].requirements_satisfied is not None
        assert len(result[0].requirements_satisfied) == 1
        assert result[0].requirements_satisfied[0]["label"] == "Ethics Core"

    def test_enrich_non_eecs_program_no_badges(self):
        """Test that non-EECS program doesn't get EECS badges."""
        from app.services.degree_requirements_matcher import enrich_classes_with_eecs_requirements
        from app.models.schedule_types import DaysOccurring, OccurrenceData
        
        cls = ClassSection(
            id="ENGR-501-01",
            code="ENGR 501-01",
            subject="ENGR",
            number="501",
            section="01",
            title="Engineering Ethics",
            credits=3.0,
            display_days="MW",
            display_time="10:00am - 10:50am",
            location="HAR 101",
            professor="Smith",
            professor_rating=4.5,
            semester="spring2026",
            semesters_offered=["Spring"],
            occurrence_data=OccurrenceData(
                starts=600,  # 10:00am in minutes
                ends=650,    # 10:50am in minutes
                days_occurring=DaysOccurring(),
            ),
        )
        
        classes = [cls]
        result = enrich_classes_with_eecs_requirements(classes, "M.S. Computer Science")
        
        assert len(result) == 1
        # Should not have EECS badges for non-EECS program
        assert result[0].requirements_satisfied is None or len(result[0].requirements_satisfied) == 0

    def test_get_eecs_degree_requirements(self):
        """Test that EECS degree requirements are returned correctly."""
        from app.services.degree_requirements_matcher import get_eecs_degree_requirements
        
        reqs = get_eecs_degree_requirements()
        
        # Should have all core areas
        labels = [req.label for req in reqs]
        assert "Ethics Core" in labels
        assert "Leadership Core" in labels
        assert "Technical Core - Computing Systems" in labels
        assert "Technical Core - Data Science & AI" in labels
        assert "Technical Core - Electrical Systems" in labels
        assert "Mastery Demonstration" in labels
        
        # Check credits
        ethics = next(r for r in reqs if r.label == "Ethics Core")
        assert ethics.credits_needed == 3.0
        assert ethics.type == RequirementType.MAJOR_CORE
        
        leadership = next(r for r in reqs if r.label == "Leadership Core")
        assert leadership.credits_needed == 6.0
