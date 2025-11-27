import json
import os
import re
from typing import Any, Dict, List, Union, IO

from pypdf import PdfReader
from openai import OpenAI

def extract_text_from_pdf(file_source: Union[str, IO]) -> str:
    """
    Extracts raw text from a PDF file (path or file-like object).
    """
    reader = PdfReader(file_source)
    text_parts: List[str] = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)

def clean_json_string(s: str) -> str:
    """
    Removes markdown code blocks and other noise from JSON string.
    """
    # Remove ```json ... ``` or ``` ... ```
    s = re.sub(r'```json\s*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'```\s*', '', s)
    return s.strip()

def parse_program_evaluation(file_source: Union[str, IO]) -> Dict[str, Any]:
    """
    Parses a program evaluation PDF using an LLM to extract structured JSON data.
    """
    text = extract_text_from_pdf(file_source)
    
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("OPENAI_MODEL")

    if not api_key or not base_url or not model:
        print("Missing OpenAI configuration. Falling back to empty parse.")
        return {}

    client = OpenAI(api_key=api_key, base_url=base_url)

    system_prompt = """
    You are a precise data extraction assistant. Your task is to parse academic program evaluation text into a structured JSON object.
    
    The JSON must strictly follow this schema:
    {
      "student_info": {
        "name": "string (Student Name)",
        "id": "string (Student ID)",
        "program": "string (Major/Program)",
        "catalog_year": "string",
        "expected_graduation_term": "string"
      },
      "gpa": {
        "overall": number (float),
        "major": number (float, optional)
      },
      "credit_requirements": [
        {
          "label": "string (e.g., 'General Education', 'Major Requirements')",
          "required": number,
          "earned": number,
          "in_progress": number,
          "needed": number
        }
      ],
      "courses": {
        "completed": [
          { "term": "string", "subject": "string (e.g. CPSC)", "number": "string (e.g. 350)", "title": "string", "grade": "string", "credits": number }
        ],
        "in_progress": [
          { "term": "string", "subject": "string", "number": "string", "title": "string", "grade": "IP", "credits": number }
        ],
        "all_found": [] 
      }
    }
    
    Instructions:
    - Extract all courses found.
    - 'in_progress' courses usually have grade 'IP' or are listed in a current/future term.
    - 'completed' courses have a final grade (A, B, C, P, etc.).
    - Populate 'all_found' with every course found.
    - Ensure numerical values are numbers, not strings.
    - OUTPUT ONLY VALID JSON. NO MARKDOWN.
    """

    try:
        # Try with response_format first (best for newer models)
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here is the program evaluation text:\n\n{text}"}
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
            "courses": {"completed": [], "in_progress": [], "all_found": []},
            "credit_requirements": []
        }
