"""
Unit tests for M.S. EECS requirements module and schedule generation.

These tests verify:
1. MS EECS requirements data integrity
2. Course-to-program mapping accuracy
3. Spring 2026 available classes for EECS students
4. Schedule generator EECS-specific handling
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Module under test
from app.services.ms_eecs_requirements import (
    load_ms_eecs_requirements,
    get_valid_course_codes,
    get_spring_2026_courses,
    get_technical_core_areas,
    get_core_courses,
    is_eecs_program,
    get_categorized_courses_for_eecs,
    get_eecs_curriculum_prompt_context,
    get_spring_2026_eecs_courses_prompt,
)


# Path to the data directory
DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class TestMsEecsRequirementsDataIntegrity:
    """Tests to verify the MS EECS requirements data is complete and accurate."""

    def test_requirements_file_exists(self):
        """Verify the ms_eecs_requirements.json file exists."""
        requirements_path = DATA_DIR / "ms_eecs_requirements.json"
        assert requirements_path.exists(), f"MS EECS requirements file not found at {requirements_path}"

    def test_requirements_is_valid_json(self):
        """Verify the requirements file is valid JSON."""
        requirements_path = DATA_DIR / "ms_eecs_requirements.json"
        with open(requirements_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert data is not None
        assert isinstance(data, dict)

    def test_requirements_has_required_fields(self):
        """Verify the requirements file has all required top-level fields."""
        requirements = load_ms_eecs_requirements()
        
        required_fields = [
            "program_name",
            "program_code",
            "catalog_year",
            "total_credits_required",
            "requirements",
            "valid_course_codes"
        ]
        
        for field in required_fields:
            assert field in requirements, f"Missing required field: {field}"

    def test_total_credits_is_30(self):
        """Verify the total credits required is 30 (per catalog)."""
        requirements = load_ms_eecs_requirements()
        assert requirements.get("total_credits_required") == 30

    def test_ethics_core_requirements(self):
        """Verify Ethics Core is 3 credits of ENGR 501."""
        requirements = load_ms_eecs_requirements()
        ethics_core = requirements.get("requirements", {}).get("ethics_core", {})
        
        assert ethics_core.get("credits_required") == 3
        assert ethics_core.get("name") == "Ethics Core"
        
        courses = ethics_core.get("courses", [])
        assert len(courses) == 1
        assert courses[0]["course_code"] == "ENGR 501"
        assert courses[0]["credits"] == 1

    def test_leadership_core_requirements(self):
        """Verify Leadership Core includes ENGR 510 and ENGR 520 for 6 credits."""
        requirements = load_ms_eecs_requirements()
        leadership_core = requirements.get("requirements", {}).get("leadership_core", {})
        
        assert leadership_core.get("credits_required") == 6
        assert leadership_core.get("name") == "Leadership Core"
        
        courses = leadership_core.get("courses", [])
        course_codes = [c["course_code"] for c in courses]
        
        assert "ENGR 510" in course_codes
        assert "ENGR 520" in course_codes

    def test_technical_core_has_three_areas(self):
        """Verify Technical Core has 3 areas: Computing, Data Science, Electrical."""
        areas = get_technical_core_areas()
        
        assert "computing_systems" in areas
        assert "data_science_intelligent_systems" in areas
        assert "electrical_systems" in areas

    def test_technical_core_computing_systems_courses(self):
        """Verify Computing Systems area contains the correct courses from catalog."""
        areas = get_technical_core_areas()
        computing = areas.get("computing_systems", {})
        courses = [c["course_code"] for c in computing.get("courses", [])]
        
        # Key Computing Systems courses from catalog
        expected_courses = ["CPSC 510", "CPSC 511", "CPSC 512", "CPSC 513", 
                          "CPSC 514", "CPSC 515", "CPSC 516", "CPSC 570", "CS 616"]
        
        for course in expected_courses:
            assert course in courses, f"Computing Systems missing course: {course}"

    def test_technical_core_data_science_courses(self):
        """Verify Data Science/Intelligent Systems area contains the correct courses."""
        areas = get_technical_core_areas()
        data_science = areas.get("data_science_intelligent_systems", {})
        courses = [c["course_code"] for c in data_science.get("courses", [])]
        
        # Key Data Science courses from catalog
        expected_courses = ["CPSC 530", "CPSC 531", "CPSC 542", "CPSC 543", 
                          "CPSC 544", "CS 611", "CS 614", "CS 635", "CS 685"]
        
        for course in expected_courses:
            assert course in courses, f"Data Science missing course: {course}"

    def test_technical_core_electrical_systems_courses(self):
        """Verify Electrical Systems area contains the correct courses."""
        areas = get_technical_core_areas()
        electrical = areas.get("electrical_systems", {})
        courses = [c["course_code"] for c in electrical.get("courses", [])]
        
        # Key Electrical Systems courses from catalog
        expected_courses = ["EENG 510", "EENG 511", "EENG 512", "EENG 513",
                          "EENG 514", "EENG 515", "EENG 516", "EENG 570"]
        
        for course in expected_courses:
            assert course in courses, f"Electrical Systems missing course: {course}"

    def test_mastery_demonstration_options(self):
        """Verify Mastery Demonstration has thesis and non-thesis tracks."""
        requirements = load_ms_eecs_requirements()
        mastery = requirements.get("requirements", {}).get("mastery_demonstration", {})
        
        assert mastery.get("credits_required") == 6
        
        tracks = mastery.get("tracks", {})
        assert "thesis" in tracks
        assert "non_thesis" in tracks
        
        # Thesis track should include ENGR 698
        thesis_courses = tracks["thesis"].get("courses", [])
        assert any(c["course_code"] == "ENGR 698" for c in thesis_courses)


class TestValidCourseCodes:
    """Tests for the valid course codes list."""

    def test_valid_course_codes_not_empty(self):
        """Verify valid_course_codes is not empty."""
        codes = get_valid_course_codes()
        assert len(codes) > 0

    def test_ethics_course_in_valid_codes(self):
        """Verify ENGR 501 is in valid course codes."""
        codes = get_valid_course_codes()
        assert "ENGR 501" in codes

    def test_leadership_courses_in_valid_codes(self):
        """Verify ENGR 510 and ENGR 520 are in valid course codes."""
        codes = get_valid_course_codes()
        assert "ENGR 510" in codes
        assert "ENGR 520" in codes

    def test_thesis_course_in_valid_codes(self):
        """Verify ENGR 698 is in valid course codes."""
        codes = get_valid_course_codes()
        assert "ENGR 698" in codes

    def test_technical_core_courses_in_valid_codes(self):
        """Verify key Technical Core courses are in valid codes."""
        codes = get_valid_course_codes()
        
        expected = ["CPSC 542", "CPSC 543", "CPSC 570", "EENG 511", "EENG 514", "CS 611"]
        for course in expected:
            assert course in codes, f"Missing expected course: {course}"


class TestSpring2026Courses:
    """Tests for Spring 2026 available courses."""

    def test_spring_2026_courses_not_empty(self):
        """Verify Spring 2026 courses list is not empty."""
        courses = get_spring_2026_courses()
        assert len(courses) > 0

    def test_spring_2026_has_ethics_core(self):
        """Verify Spring 2026 has ENGR 501 sections."""
        courses = get_spring_2026_courses()
        engr_501_courses = [c for c in courses if c["course_code"].startswith("ENGR 501")]
        assert len(engr_501_courses) >= 2, "Expected at least 2 ENGR 501 sections"

    def test_spring_2026_has_leadership_core(self):
        """Verify Spring 2026 has ENGR 520 sections."""
        courses = get_spring_2026_courses()
        engr_520_courses = [c for c in courses if c["course_code"].startswith("ENGR 520")]
        assert len(engr_520_courses) >= 1, "Expected at least 1 ENGR 520 section"

    def test_spring_2026_has_technical_electives(self):
        """Verify Spring 2026 has technical elective options."""
        courses = get_spring_2026_courses()
        tech_courses = [c for c in courses if c.get("category") == "technical_core"]
        assert len(tech_courses) >= 4, "Expected at least 4 technical core courses"

    def test_spring_2026_key_courses_available(self):
        """Verify specific key courses are available for Spring 2026."""
        courses = get_spring_2026_courses()
        course_codes = [c["course_code"] for c in courses]
        
        # Key courses that should be available
        expected = ["CPSC 542-01", "CPSC 543-01", "CPSC 570-01", 
                   "EENG 511-01", "EENG 514-01", "CS 611-01"]
        
        for course in expected:
            assert course in course_codes, f"Expected Spring 2026 course not found: {course}"


class TestIsEecsProgram:
    """Tests for the is_eecs_program function."""

    def test_exact_program_name(self):
        """Test detection with exact program name."""
        assert is_eecs_program("Electrical Engineering and Computer Science, M.S.")

    def test_partial_match_lowercase(self):
        """Test detection with partial lowercase match."""
        assert is_eecs_program("electrical engineering and computer science")

    def test_eecs_abbreviation(self):
        """Test detection with EECS abbreviation."""
        assert is_eecs_program("EECS")
        assert is_eecs_program("eecs")

    def test_ms_electrical_variation(self):
        """Test detection with M.S. in Electrical variation."""
        assert is_eecs_program("M.S. in Electrical Engineering")
        assert is_eecs_program("MS Electrical Engineering")

    def test_non_eecs_programs(self):
        """Test that non-EECS programs return False."""
        assert not is_eecs_program("Computer Science, B.S.")
        assert not is_eecs_program("Business Administration, MBA")
        assert not is_eecs_program("")
        assert not is_eecs_program(None)


class TestCategorizedCourses:
    """Tests for the get_categorized_courses_for_eecs function."""

    def test_categorized_has_all_categories(self):
        """Verify all expected categories are present."""
        categorized = get_categorized_courses_for_eecs()
        
        expected_categories = [
            "ethics_core",
            "leadership_core",
            "computing_systems",
            "data_science_intelligent_systems",
            "electrical_systems",
            "mastery"
        ]
        
        for category in expected_categories:
            assert category in categorized, f"Missing category: {category}"

    def test_categorized_ethics_core(self):
        """Verify Ethics Core category contains ENGR 501."""
        categorized = get_categorized_courses_for_eecs()
        assert "ENGR 501" in categorized["ethics_core"]

    def test_categorized_leadership_core(self):
        """Verify Leadership Core category contains ENGR 510 and ENGR 520."""
        categorized = get_categorized_courses_for_eecs()
        assert "ENGR 510" in categorized["leadership_core"]
        assert "ENGR 520" in categorized["leadership_core"]


class TestPromptContext:
    """Tests for the LLM prompt context generators."""

    def test_curriculum_prompt_not_empty(self):
        """Verify curriculum prompt context is not empty."""
        context = get_eecs_curriculum_prompt_context()
        assert len(context) > 0

    def test_curriculum_prompt_contains_key_info(self):
        """Verify curriculum prompt contains key information."""
        context = get_eecs_curriculum_prompt_context()
        
        assert "M.S. in Electrical Engineering and Computer Science" in context
        assert "Ethics Core" in context
        assert "Leadership Core" in context
        assert "Technical Core" in context
        assert "ENGR 501" in context
        assert "30" in context  # Total credits

    def test_spring_2026_prompt_not_empty(self):
        """Verify Spring 2026 prompt is not empty."""
        prompt = get_spring_2026_eecs_courses_prompt()
        assert len(prompt) > 0

    def test_spring_2026_prompt_contains_courses(self):
        """Verify Spring 2026 prompt contains course information."""
        prompt = get_spring_2026_eecs_courses_prompt()
        
        assert "Spring 2026" in prompt
        assert "ENGR 501" in prompt or "ENGR 520" in prompt


class TestCourseMappingIntegrity:
    """Tests to verify course-to-program mapping for EECS."""

    def test_course_mapping_file_exists(self):
        """Verify the course mapping file exists."""
        mapping_path = DATA_DIR / "course_to_program_mapping.json"
        assert mapping_path.exists()

    def test_engr_501_mapped_to_eecs(self):
        """Verify ENGR 501 is mapped to EECS M.S. program."""
        mapping_path = DATA_DIR / "course_to_program_mapping.json"
        with open(mapping_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        
        engr_501 = mapping.get("ENGR 501", [])
        eecs_entries = [p for p in engr_501 
                       if "Electrical Engineering and Computer Science, M.S." in p.get("program", "")]
        
        assert len(eecs_entries) > 0, "ENGR 501 not mapped to EECS"
        
        # Verify it's marked as core (not program_requirement)
        for entry in eecs_entries:
            if entry.get("year") == "2025-2026":
                assert entry.get("requirement_type") == "core", \
                    f"ENGR 501 should be 'core' requirement, got: {entry.get('requirement_type')}"

    def test_engr_520_mapped_as_core(self):
        """Verify ENGR 520 is mapped as 'core' (not 'program_requirement')."""
        mapping_path = DATA_DIR / "course_to_program_mapping.json"
        with open(mapping_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        
        engr_520 = mapping.get("ENGR 520", [])
        eecs_entries = [p for p in engr_520 
                       if "Electrical Engineering and Computer Science, M.S." in p.get("program", "")]
        
        assert len(eecs_entries) > 0, "ENGR 520 not mapped to EECS"
        
        for entry in eecs_entries:
            if entry.get("year") == "2025-2026":
                assert entry.get("requirement_type") == "core", \
                    f"ENGR 520 should be 'core' (Leadership Core), got: {entry.get('requirement_type')}"


class TestAvailableClassesCsv:
    """Tests to verify available_classes_spring_2026.csv has EECS courses."""

    def test_available_classes_file_exists(self):
        """Verify the available classes CSV exists."""
        csv_path = DATA_DIR / "available_classes_spring_2026.csv"
        assert csv_path.exists()

    def test_csv_has_engr_501_sections(self):
        """Verify CSV has ENGR 501 sections."""
        csv_path = DATA_DIR / "available_classes_spring_2026.csv"
        with open(csv_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "ENGR 501-01" in content
        assert "ENGR 501-02" in content

    def test_csv_has_engr_520_sections(self):
        """Verify CSV has ENGR 520 sections."""
        csv_path = DATA_DIR / "available_classes_spring_2026.csv"
        with open(csv_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "ENGR 520-01" in content

    def test_csv_has_technical_electives(self):
        """Verify CSV has key technical elective courses."""
        csv_path = DATA_DIR / "available_classes_spring_2026.csv"
        with open(csv_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for technical electives
        assert "CPSC 542-01" in content, "Missing CPSC 542-01 (Deep Learning)"
        assert "CPSC 543-01" in content, "Missing CPSC 543-01 (NLP)"
        assert "CPSC 570-01" in content, "Missing CPSC 570-01 (AI)"
        assert "EENG 511-01" in content, "Missing EENG 511-01 (Control Systems)"
        assert "EENG 514-01" in content, "Missing EENG 514-01 (IC Design)"
        assert "CS 611-01" in content, "Missing CS 611-01 (Advanced AI)"
