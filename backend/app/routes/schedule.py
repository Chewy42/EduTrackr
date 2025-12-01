"""
Schedule API Routes - Endpoints for the class calendar/schedule builder.
Provides class search, filtering, requirement matching, and schedule validation.
"""
from typing import Any, Dict, List, Optional

import jwt as pyjwt
from flask import Blueprint, jsonify, request

from app.services.auth_tokens import decode_app_token_from_request
from app.services.classes_service import (
    get_class_by_id,
    get_classes_by_ids,
    get_unique_subjects,
    load_all_classes,
    search_classes,
    validate_schedule,
)
from app.services.degree_requirements_matcher import (
    enrich_classes_with_requirements,
    enrich_classes_with_eecs_requirements,
    extract_user_requirements,
    get_eecs_degree_requirements,
    get_requirement_summary,
)
from app.services.program_evaluation_store import load_parsed_payload
from app.services.ms_eecs_requirements import is_eecs_program
from app.services.schedule_generator import generate_schedule
from app.services.schedule_snapshot_service import (
    save_snapshot,
    list_snapshots,
    get_snapshot,
    delete_snapshot,
    update_snapshot,
    DuplicateNameError,
    SnapshotError,
)
from app.services.supabase_client import supabase_request

schedule_bp = Blueprint("schedule", __name__)


def _get_user_requirements(email: str) -> List:
    """
    Get user's remaining degree requirements from their parsed evaluation.
    Returns empty list if no evaluation found.
    """
    payload = load_parsed_payload(email)
    if not payload:
        return []
    
    parsed_data = payload.get("parsed_data", {})
    if not parsed_data:
        return []
    
    return extract_user_requirements(parsed_data)


def _get_user_program_name(email: str) -> Optional[str]:
    """
    Get user's program name from their parsed evaluation.
    Returns None if no evaluation found.
    """
    payload = load_parsed_payload(email)
    if not payload:
        return None
    
    parsed_data = payload.get("parsed_data", {})
    if not parsed_data:
        return None
    
    return parsed_data.get("program_name", None)


@schedule_bp.route("/schedule/generate", methods=["POST"])
def generate_auto_schedule():
    """
    Auto-generate a schedule based on user preferences and requirements.
    Requires authentication.

    Returns:
        { "class_ids": ["CPSC-350-01", ...] }
    """
    try:
        payload = decode_app_token_from_request()
        email = payload.get("email", "")

        if not email:
            return jsonify({"error": "Invalid token - missing email"}), 401

        # Fetch user_id from database using email
        user_resp = supabase_request("GET", f"/rest/v1/app_users?email=eq.{email}&select=id")
        if user_resp.status_code != 200 or not user_resp.json():
            return jsonify({"error": "User not found"}), 404
        user_id = user_resp.json()[0]['id']

        result = generate_schedule(user_id, email)

        # Check for errors but still return class_ids if present
        if "error" in result and not result.get("class_ids"):
            return jsonify(result), 500

        # Success - return the generated schedule
        return jsonify({
            "class_ids": result.get("class_ids", []),
            "message": result.get("error")  # Include warning if any
        }), 200

    except pyjwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired", "class_ids": []}), 401
    except pyjwt.InvalidTokenError as e:
        print(f"Generate Schedule Token Error: {e}")
        return jsonify({"error": "Invalid token", "class_ids": []}), 401
    except Exception as e:
        print(f"Generate Schedule Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to generate schedule", "class_ids": []}), 500


@schedule_bp.route("/schedule/classes", methods=["GET"])
def get_classes():
    """
    Get available classes with optional search and filtering.
    
    Query Parameters:
        search: Text search (code, title, professor)
        days: Comma-separated days (e.g., "M,W,F")
        time_start: Minimum start time in minutes from midnight
        time_end: Maximum end time in minutes from midnight
        credits_min: Minimum credits
        credits_max: Maximum credits
        subject: Filter by subject (e.g., "CPSC")
        limit: Max results (default 50)
        offset: Pagination offset (default 0)
        include_requirements: Include degree requirement badges (default true)
    
    Returns:
        {
            "classes": [...],
            "total": number,
            "limit": number,
            "offset": number
        }
    """
    # Parse query parameters
    search = request.args.get("search", "").strip() or None
    days_param = request.args.get("days", "")
    days = [d.strip() for d in days_param.split(",") if d.strip()] or None
    
    time_start = request.args.get("time_start", type=int)
    time_end = request.args.get("time_end", type=int)
    credits_min = request.args.get("credits_min", type=float)
    credits_max = request.args.get("credits_max", type=float)
    subject = request.args.get("subject", "").strip() or None
    
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    include_requirements = request.args.get("include_requirements", "true").lower() == "true"
    
    # Cap limit to prevent abuse
    limit = min(limit, 200)
    
    # Search classes
    classes, total = search_classes(
        query=search,
        days=days,
        time_start=time_start,
        time_end=time_end,
        credits_min=credits_min,
        credits_max=credits_max,
        subject=subject,
        limit=limit,
        offset=offset,
    )
    
    # Optionally enrich with requirement badges
    if include_requirements:
        try:
            payload = decode_app_token_from_request()
            email = payload.get("email", "")
            if email:
                requirements = _get_user_requirements(email)
                if requirements:
                    classes = enrich_classes_with_requirements(classes, requirements)
                
                # Also apply EECS-specific requirement badges
                program_name = _get_user_program_name(email)
                if program_name:
                    classes = enrich_classes_with_eecs_requirements(classes, program_name)
        except Exception:
            # If auth fails, just return classes without requirement badges
            pass
    
    return jsonify({
        "classes": [cls.to_dict() for cls in classes],
        "total": total,
        "limit": limit,
        "offset": offset,
    }), 200


@schedule_bp.route("/schedule/classes/<class_id>", methods=["GET"])
def get_single_class(class_id: str):
    """
    Get a single class by ID with full details.
    
    Returns:
        Class object with all details and requirement badges
    """
    cls = get_class_by_id(class_id)
    
    if not cls:
        return jsonify({"error": "Class not found"}), 404
    
    # Try to enrich with requirements
    try:
        payload = decode_app_token_from_request()
        email = payload.get("email", "")
        if email:
            requirements = _get_user_requirements(email)
            if requirements:
                enrich_classes_with_requirements([cls], requirements)
            
            # Also apply EECS-specific requirement badges
            program_name = _get_user_program_name(email)
            if program_name:
                enrich_classes_with_eecs_requirements([cls], program_name)
    except Exception:
        pass
    
    return jsonify(cls.to_dict()), 200


@schedule_bp.route("/schedule/validate", methods=["POST"])
def validate_user_schedule():
    """
    Validate a schedule for conflicts and credit limits.
    
    Request Body:
        { "classes": ["class-id-1", "class-id-2", ...] }
    
    Returns:
        {
            "valid": boolean,
            "conflicts": [...],
            "totalCredits": number,
            "warnings": [...]
        }
    """
    data = request.get_json() or {}
    class_ids = data.get("classes", [])
    
    if not isinstance(class_ids, list):
        return jsonify({"error": "classes must be an array"}), 400
    
    result = validate_schedule(class_ids)
    return jsonify(result), 200


@schedule_bp.route("/schedule/user-requirements", methods=["GET"])
def get_user_requirements():
    """
    Get the current user's remaining degree requirements.
    Requires authentication.
    
    Returns:
        {
            "total": number,
            "byType": { "major_core": n, "ge": n, ... },
            "requirements": [...]
        }
    """
    try:
        payload = decode_app_token_from_request()
        email = payload.get("email", "")
        if not email:
            return jsonify({"error": "Invalid token"}), 401
    except pyjwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except Exception:
        return jsonify({"error": "Unauthorized"}), 401
    
    requirements = _get_user_requirements(email)
    
    # For EECS students, also include EECS-specific curriculum requirements
    # This allows the View Impact modal to properly show progress
    program_name = _get_user_program_name(email)
    if program_name and is_eecs_program(program_name):
        eecs_requirements = get_eecs_degree_requirements()
        # Add EECS requirements that aren't already in the list
        existing_labels = {req.label for req in requirements}
        for eecs_req in eecs_requirements:
            if eecs_req.label not in existing_labels:
                requirements.append(eecs_req)
    
    summary = get_requirement_summary(requirements)
    
    return jsonify(summary), 200


@schedule_bp.route("/schedule/subjects", methods=["GET"])
def get_subjects():
    """
    Get a list of all unique subjects (e.g., CPSC, MATH, ENG).
    Useful for filtering dropdowns.
    
    Returns:
        { "subjects": ["ACTG", "AH", "ANTH", ...] }
    """
    subjects = get_unique_subjects()
    return jsonify({"subjects": subjects}), 200


@schedule_bp.route("/schedule/stats", methods=["GET"])
def get_schedule_stats():
    """
    Get statistics about available classes.
    
    Returns:
        {
            "totalClasses": number,
            "subjects": number,
            "avgCredits": number
        }
    """
    all_classes = load_all_classes()

    total = len(all_classes)
    subjects = len(set(cls.subject for cls in all_classes))
    avg_credits = sum(cls.credits for cls in all_classes) / total if total > 0 else 0

    return jsonify({
        "totalClasses": total,
        "subjects": subjects,
        "avgCredits": round(avg_credits, 2),
    }), 200


# ============================================================================
# Schedule Snapshot Endpoints
# ============================================================================

@schedule_bp.route("/schedule/snapshots", methods=["POST"])
def create_snapshot():
    """
    Save a new schedule snapshot.
    Requires authentication.

    Request Body:
        {
            "name": "My Spring Schedule",
            "class_ids": ["CPSC-350-01", "MATH-210-02", ...],
            "total_credits": 15
        }

    Returns:
        201: Created snapshot object
        400: Invalid request (missing fields, empty name)
        401: Unauthorized
        409: Duplicate name
    """
    try:
        payload = decode_app_token_from_request()
        email = payload.get("email", "")
        if not email:
            return jsonify({"error": "Invalid token - missing email"}), 401
    except pyjwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except pyjwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    data = request.get_json() or {}
    name = data.get("name", "").strip()
    class_ids = data.get("class_ids", [])
    total_credits = data.get("total_credits", 0)

    if not name:
        return jsonify({"error": "Snapshot name is required"}), 400

    if not isinstance(class_ids, list):
        return jsonify({"error": "class_ids must be an array"}), 400

    try:
        snapshot = save_snapshot(email, name, class_ids, float(total_credits))
        return jsonify(snapshot.to_dict()), 201
    except DuplicateNameError as e:
        return jsonify({"error": str(e)}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except SnapshotError as e:
        return jsonify({"error": str(e)}), 500


@schedule_bp.route("/schedule/snapshots", methods=["GET"])
def get_all_snapshots():
    """
    List all schedule snapshots for the current user.
    Requires authentication.

    Returns:
        200: { "snapshots": [...] }
        401: Unauthorized
    """
    try:
        payload = decode_app_token_from_request()
        email = payload.get("email", "")
        if not email:
            return jsonify({"error": "Invalid token - missing email"}), 401
    except pyjwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except pyjwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    snapshots = list_snapshots(email)
    return jsonify({
        "snapshots": [s.to_dict() for s in snapshots]
    }), 200


@schedule_bp.route("/schedule/snapshots/<snapshot_id>", methods=["GET"])
def get_single_snapshot(snapshot_id: str):
    """
    Get a specific schedule snapshot by ID.
    Requires authentication.

    Returns:
        200: Snapshot object
        401: Unauthorized
        404: Not found
    """
    try:
        payload = decode_app_token_from_request()
        email = payload.get("email", "")
        if not email:
            return jsonify({"error": "Invalid token - missing email"}), 401
    except pyjwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except pyjwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    snapshot = get_snapshot(email, snapshot_id)
    if not snapshot:
        return jsonify({"error": "Snapshot not found"}), 404

    return jsonify(snapshot.to_dict()), 200


@schedule_bp.route("/schedule/snapshots/<snapshot_id>", methods=["DELETE"])
def remove_snapshot(snapshot_id: str):
    """
    Delete a schedule snapshot.
    Requires authentication.

    Returns:
        204: Successfully deleted
        401: Unauthorized
        404: Not found
    """
    try:
        payload = decode_app_token_from_request()
        email = payload.get("email", "")
        if not email:
            return jsonify({"error": "Invalid token - missing email"}), 401
    except pyjwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except pyjwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    deleted = delete_snapshot(email, snapshot_id)
    if not deleted:
        return jsonify({"error": "Snapshot not found"}), 404

    return "", 204


@schedule_bp.route("/schedule/snapshots/<snapshot_id>", methods=["PATCH"])
def modify_snapshot(snapshot_id: str):
    """
    Update a schedule snapshot.
    Requires authentication.

    Request Body (all fields optional):
        {
            "name": "New Name",
            "class_ids": ["CPSC-350-01", ...],
            "total_credits": 15
        }

    Returns:
        200: Updated snapshot object
        400: Invalid request
        401: Unauthorized
        404: Not found
        409: Duplicate name
    """
    try:
        payload = decode_app_token_from_request()
        email = payload.get("email", "")
        if not email:
            return jsonify({"error": "Invalid token - missing email"}), 401
    except pyjwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except pyjwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    data = request.get_json() or {}
    name = data.get("name")
    class_ids = data.get("class_ids")
    total_credits = data.get("total_credits")

    # Validate class_ids if provided
    if class_ids is not None and not isinstance(class_ids, list):
        return jsonify({"error": "class_ids must be an array"}), 400

    try:
        updated = update_snapshot(
            email,
            snapshot_id,
            name=name,
            class_ids=class_ids,
            total_credits=float(total_credits) if total_credits is not None else None,
        )

        if not updated:
            return jsonify({"error": "Snapshot not found"}), 404

        return jsonify(updated.to_dict()), 200
    except DuplicateNameError as e:
        return jsonify({"error": str(e)}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
