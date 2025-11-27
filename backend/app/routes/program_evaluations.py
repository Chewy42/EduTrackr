from datetime import datetime, date, timezone
from typing import Any, Dict, Optional

import jwt as pyjwt
from flask import Blueprint, jsonify, request, send_file

from app.services.auth_tokens import decode_app_token_from_request
from app.services.pdf_parser import parse_program_evaluation
from app.services.program_evaluation_store import (
    has_program_evaluation,
    load_parsed_payload,
    persist_parsed_payload,
    program_evaluation_path_for_email,
    save_uploaded_pdf,
)
from app.services.supabase_client import supabase_configured, supabase_request
from app.services.chat_service import reset_onboarding_session

program_evaluations_bp = Blueprint("program_evaluations", __name__)


def _require_email_from_token() -> str:
    payload = decode_app_token_from_request()
    email = payload.get("email", "")
    if not email:
        raise pyjwt.InvalidTokenError("Invalid token payload")
    return email


def _sync_supabase_records(
    email: str,
    filename: str,
    size_bytes: int,
    parsed_data: Dict[str, Any],
) -> None:
    if not supabase_configured():
        return

    try:
        user_response = supabase_request(
            "GET", f"/rest/v1/app_users?email=eq.{email}&select=id"
        )
        if user_response.status_code != 200:
            return

        users = user_response.json()
        if not users:
            return

        user_id = users[0]["id"]

        # Reset onboarding status and chat history for new evaluation
        try:
            reset_onboarding_session(user_id)
            supabase_request(
                "PATCH",
                f"/rest/v1/user_preferences?user_id=eq.{user_id}",
                json={"onboarding_complete": False}
            )
        except Exception as e:
            print(f"Failed to reset onboarding state: {e}")

        eval_payload = {
            "user_id": user_id,
            "storage_path": f"program-evaluations/{email}",
            "original_filename": filename,
            "mime_type": "application/pdf",
            "file_size_bytes": size_bytes,
            "parsing_status": "completed",
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }

        eval_resp = supabase_request(
            "POST",
            "/rest/v1/program_evaluations",
            json=eval_payload,
            headers={"Prefer": "return=representation"},
        )
        if eval_resp.status_code not in (200, 201):
            return

        evaluation_id = eval_resp.json()[0]["id"]
        sections = [
            {
                "evaluation_id": evaluation_id,
                "section_name": "student_info",
                "section_order": 0,
                "content": parsed_data.get("student_info"),
            },
            {
                "evaluation_id": evaluation_id,
                "section_name": "gpa",
                "section_order": 1,
                "content": parsed_data.get("gpa"),
            },
            {
                "evaluation_id": evaluation_id,
                "section_name": "credit_requirements",
                "section_order": 2,
                "content": parsed_data.get("credit_requirements"),
            },
            {
                "evaluation_id": evaluation_id,
                "section_name": "courses",
                "section_order": 3,
                "content": parsed_data.get("courses"),
            },
        ]
        supabase_request(
            "POST",
            "/rest/v1/program_evaluation_sections",
            json=sections,
        )

        snapshots = []
        gpa = parsed_data.get("gpa", {})
        if "overall" in gpa:
            snapshots.append(
                {
                    "user_id": user_id,
                    "evaluation_id": evaluation_id,
                    "snapshot_date": date.today().isoformat(),
                    "metric_key": "gpa_overall",
                    "metric_value": gpa["overall"],
                }
            )
        if "major" in gpa:
            snapshots.append(
                {
                    "user_id": user_id,
                    "evaluation_id": evaluation_id,
                    "snapshot_date": date.today().isoformat(),
                    "metric_key": "gpa_major",
                    "metric_value": gpa["major"],
                }
            )
        if snapshots:
            supabase_request(
                "POST",
                "/rest/v1/student_progress_snapshots",
                json=snapshots,
            )
    except Exception as exc:  # noqa: BLE001
        print(f"Supabase sync skipped: {exc}")


def _parsed_payload(
    email: str, filename: str, parsed_data: Dict[str, Any]
) -> Dict[str, Any]:
    return {
        "email": email,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "original_filename": filename,
        "parsed_data": parsed_data,
    }


@program_evaluations_bp.route("/program-evaluations", methods=["POST"])
def upload_program_evaluation():
    try:
        email = _require_email_from_token()
    except pyjwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except Exception:
        return jsonify({"error": "Unauthorized"}), 401

    if "file" not in request.files:
        return jsonify({"error": "File is required."}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "File is required."}), 400

    filename = file.filename
    if not filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported."}), 400

    pdf_path, size_bytes = save_uploaded_pdf(file, email)

    parsed_data: Dict[str, Any] = {}
    try:
        parsed_data = parse_program_evaluation(str(pdf_path))
    except Exception as exc:  # noqa: BLE001
        print(f"Parsing skipped due to error: {exc}")

    payload = _parsed_payload(email, filename, parsed_data)
    persist_parsed_payload(email, payload)
    _sync_supabase_records(email, filename, size_bytes, parsed_data)

    return (
        jsonify(
            {
                "status": "ok",
                "filename": filename,
                "parsed": parsed_data,
                "hasProgramEvaluation": True,
            }
        ),
        201,
    )


@program_evaluations_bp.route("/program-evaluations", methods=["GET"])
def get_program_evaluation():
    try:
        email = _require_email_from_token()
    except pyjwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except Exception:
        return jsonify({"error": "Unauthorized"}), 401

    pdf_path = program_evaluation_path_for_email(email)
    if not pdf_path.exists():
        return jsonify({"error": "No program evaluation on file."}), 404

    return send_file(pdf_path, mimetype="application/pdf")


@program_evaluations_bp.route("/program-evaluations/parsed", methods=["GET"])
def get_parsed_program_evaluation():
    try:
        email = _require_email_from_token()
    except pyjwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except Exception:
        return jsonify({"error": "Unauthorized"}), 401

    payload: Optional[Dict[str, Any]] = load_parsed_payload(email)
    if not payload and has_program_evaluation(email):
        pdf_path = program_evaluation_path_for_email(email)
        parsed_data: Dict[str, Any] = {}
        try:
            parsed_data = parse_program_evaluation(str(pdf_path))
        except Exception as exc:  # noqa: BLE001
            print(f"Parsing skipped due to error: {exc}")
        payload = _parsed_payload(email, pdf_path.name, parsed_data)
        persist_parsed_payload(email, payload)
    if not payload:
        return jsonify({"error": "No parsed evaluation found."}), 404

    return jsonify(payload), 200
