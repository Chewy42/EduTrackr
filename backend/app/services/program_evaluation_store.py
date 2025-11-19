import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from werkzeug.datastructures import FileStorage

BASE_DIR = Path(__file__).resolve().parents[2]
PROGRAM_EVALUATION_DIR = BASE_DIR / "tmp" / "program_evaluations"
PARSED_DIR = PROGRAM_EVALUATION_DIR / "parsed"


def _sanitize_email(email: str) -> str:
    return email.replace("@", "_at_").replace("/", "_")


def program_evaluation_path_for_email(email: str) -> Path:
    PROGRAM_EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    safe_email = _sanitize_email(email)
    return PROGRAM_EVALUATION_DIR / f"{safe_email}.pdf"


def parsed_payload_path_for_email(email: str) -> Path:
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    safe_email = _sanitize_email(email)
    return PARSED_DIR / f"{safe_email}.json"


def has_program_evaluation(email: str) -> bool:
    return program_evaluation_path_for_email(email).exists()


def save_uploaded_pdf(file: FileStorage, email: str) -> Tuple[Path, int]:
    target_path = program_evaluation_path_for_email(email)
    file.save(target_path)
    size_bytes = target_path.stat().st_size
    return target_path, size_bytes


def persist_parsed_payload(email: str, data: Dict[str, Any]) -> Path:
    target_path = parsed_payload_path_for_email(email)
    target_path.write_text(json.dumps(data, indent=2))
    return target_path


def load_parsed_payload(email: str) -> Optional[Dict[str, Any]]:
    target_path = parsed_payload_path_for_email(email)
    if not target_path.exists():
        return None
    try:
        return json.loads(target_path.read_text())
    except json.JSONDecodeError:
        return None
