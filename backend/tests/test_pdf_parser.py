import pytest
from unittest.mock import patch, MagicMock
from app.services.pdf_parser import parse_program_evaluation

# Mock text that simulates the content of a program evaluation PDF
MOCK_PDF_TEXT = """
Name: John Doe
ID: 123456789
Program: Computer Science
Catalog Year: 2024-2025

Minimum 30 credits
Credits: 30.00 required, 14.00 earned, 12.00 in progress, 4.00 needed

Overall GPA: 3.85
Major GPA: 3.90

Courses:
Fall 2023 CPSC 230 Computer Science I A 3.00 EN
Spring 2024 MATH 110 Single Variable Calculus A- 3.00 EN
Fall 2024 CPSC 231 Computer Science II IP 3.00 IP

Mastery Demonstration:
Thesis Defense: Not Satisfied
"""

@patch('app.services.pdf_parser.extract_text_from_pdf')
def test_parse_program_evaluation(mock_extract_text):
    mock_extract_text.return_value = MOCK_PDF_TEXT
    
    data = parse_program_evaluation("dummy_path.pdf")
    
    # Verify Student Info
    assert data["student_info"]["name"] == "John Doe"
    assert data["student_info"]["id"] == "123456789"
    assert data["student_info"]["program"] == "Computer Science"
    assert data["student_info"]["catalog_year"] == "2024-2025"
    
    # Verify GPA
    assert data["gpa"]["overall"] == 3.85
    assert data["gpa"]["major"] == 3.90
    
    # Verify Courses
    courses = data["courses"]["all_found"]
    assert len(courses) == 3
    
    assert courses[0]["subject"] == "CPSC"
    assert courses[0]["number"] == "230"
    assert courses[0]["grade"] == "A"
    assert courses[0]["credits"] == 3.0
    
    assert courses[1]["subject"] == "MATH"
    assert courses[1]["number"] == "110"
    assert courses[1]["grade"] == "A-"
    
    assert courses[2]["subject"] == "CPSC"
    assert courses[2]["number"] == "231"
    assert courses[2]["grade"] == "IP"

    credit_reqs = data["credit_requirements"]
    assert any(req["label"].startswith("Minimum 30 credits") for req in credit_reqs)
    found_req = next(req for req in credit_reqs if req["label"].startswith("Minimum 30 credits"))
    assert found_req["required"] == 30.0
    assert found_req["earned"] == 14.0
    assert found_req["in_progress"] == 12.0
    assert found_req["needed"] == 4.0
    
    # Verify Mastery Demonstration (based on the mock text having "Thesis Defense")
    assert data["mastery_demonstration"]["type"] == "Thesis"

