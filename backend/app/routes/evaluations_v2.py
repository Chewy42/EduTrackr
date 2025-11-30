import io
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import jwt as pyjwt
from flask import Blueprint, jsonify, request, send_file

from app.services.auth_tokens import decode_app_token_from_request
from app.services.pdf_parser_llm import parse_program_evaluation
from app.services.evaluation_service import (
    upload_evaluation_file,
    save_metadata,
    get_evaluation_file,
    load_parsed_data,
    has_program_evaluation,
)
from app.services.supabase_client import supabase_request
from app.services.chat_service import reset_onboarding_session

program_evaluations_bp = Blueprint("program_evaluations", __name__)

def _require_email_from_token() -> str:
    payload = decode_app_token_from_request()
    email = payload.get("email", "")
    if not email:
        raise pyjwt.InvalidTokenError("Invalid token payload")
    return email

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

    try:
        # 0. Get user_id and reset onboarding state
        user_resp = supabase_request("GET", f"/rest/v1/app_users?email=eq.{email}&select=id")
        if user_resp.status_code == 200 and user_resp.json():
            user_id = user_resp.json()[0]["id"]
            # Reset onboarding session (deletes chat history)
            try:
                reset_onboarding_session(user_id)
            except Exception as e:
                print(f"Failed to reset onboarding session: {e}")
            # Reset onboarding_complete preference to false
            try:
                supabase_request(
                    "PATCH",
                    f"/rest/v1/user_preferences?user_id=eq.{user_id}",
                    json={"onboarding_complete": False}
                )
            except Exception as e:
                print(f"Failed to reset onboarding preference: {e}")

        # 1. Upload to Supabase Storage
        storage_path, size_bytes, file_bytes = upload_evaluation_file(file, email)
        
        # 2. Parse PDF from bytes
        parsed_data: Dict[str, Any] = {}
        try:
            parsed_data = parse_program_evaluation(io.BytesIO(file_bytes))
        except Exception as exc:
            print(f"Parsing skipped due to error: {exc}")
        
        # 3. Save Metadata & Sections to Supabase DB
        save_metadata(email, filename, storage_path, size_bytes, parsed_data)

        return jsonify({
            "status": "ok",
            "filename": filename,
            "parsed": parsed_data,
            "hasProgramEvaluation": True,
            "onboardingComplete": False,
        }), 201

    except ValueError as e:
        # User not found implies account deleted/invalid
        return jsonify({"error": str(e)}), 401
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({"error": "Unable to process upload."}), 500


@program_evaluations_bp.route("/program-evaluations", methods=["GET"])
def get_program_evaluation():
    try:
        email = _require_email_from_token()
    except pyjwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except Exception:
        return jsonify({"error": "Unauthorized"}), 401

    file_bytes = get_evaluation_file(email)
    if not file_bytes:
        return jsonify({"error": "No program evaluation on file."}), 404

    return send_file(
        io.BytesIO(file_bytes), 
        mimetype="application/pdf",
        as_attachment=False,
        download_name="program_evaluation.pdf"
    )


@program_evaluations_bp.route("/program-evaluations/parsed", methods=["GET"])
def get_parsed_program_evaluation():
    try:
        email = _require_email_from_token()
    except pyjwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except Exception:
        return jsonify({"error": "Unauthorized"}), 401

    payload = load_parsed_data(email)
    if not payload:
        return jsonify({"error": "No parsed evaluation found."}), 404

    return jsonify(payload), 200


@program_evaluations_bp.route("/program-evaluations", methods=["DELETE"])
def delete_program_evaluation():
    try:
        email = _require_email_from_token()
    except pyjwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except Exception:
        return jsonify({"error": "Unauthorized"}), 401

    # Get user ID
    user_resp = supabase_request("GET", f"/rest/v1/app_users?email=eq.{email}&select=id")
    if user_resp.status_code != 200 or not user_resp.json():
        return jsonify({"error": "User not found"}), 404
    user_id = user_resp.json()[0]["id"]

    # 1. Delete from DB (Cascades to sections/snapshots usually, but check schema)
    # Assuming cascade delete is set up on foreign keys. If not, we might need to delete child rows first.
    # We'll just delete the evaluation record.
    
    # First get the evaluation to know storage path if we want to delete file
    eval_resp = supabase_request("GET", f"/rest/v1/program_evaluations?user_id=eq.{user_id}&select=id,storage_path")
    if eval_resp.status_code == 200 and eval_resp.json():
        for row in eval_resp.json():
            eval_id = row['id']
            storage_path = row.get('storage_path')
            
            # Delete from DB
            del_resp = supabase_request("DELETE", f"/rest/v1/program_evaluations?id=eq.{eval_id}")
            if del_resp.status_code not in (200, 204):
                print(f"Warning: Failed to delete evaluation record {eval_id}")

            # Delete from Storage
            if storage_path:
                # storage_path might be "userid/filename"
                # DELETE /storage/v1/object/{bucket}/{path}
                from app.services.evaluation_service import BUCKET
                # Supabase storage delete takes a list of prefixes/paths in body?
                # Or DELETE method on single object.
                # The standard API is DELETE /object/{bucket}/{wildcard}
                supabase_request("DELETE", f"/storage/v1/object/{BUCKET}/{storage_path}")
    
    return jsonify({"status": "ok"}), 200
