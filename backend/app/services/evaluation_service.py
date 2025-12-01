import io
from typing import Any, Dict, Optional, Tuple, List

from werkzeug.datastructures import FileStorage
from app.services.supabase_client import supabase_request

BUCKET = "program-evaluations"


def _get_user_id(email: str) -> Optional[str]:
	resp = supabase_request("GET", f"/rest/v1/app_users?email=eq.{email}&select=id")
	if resp.status_code == 200 and resp.json():
		return resp.json()[0]["id"]
	return None


def _ensure_bucket_exists() -> None:
	"""Ensure the Supabase storage bucket for program evaluations exists."""
	# Check if bucket exists
	resp = supabase_request("GET", f"/storage/v1/bucket/{BUCKET}")
	if resp.status_code == 200:
		return

	print(f"Bucket '{BUCKET}' not found. Creating...")
	payload = {
		"id": BUCKET,
		"name": BUCKET,
		"public": False,
		"file_size_limit": 5242880,  # 5MB
		"allowed_mime_types": ["application/pdf"],
	}
	create_resp = supabase_request("POST", "/storage/v1/bucket", json=payload)
	if create_resp.status_code not in (200, 201):
		print(f"Failed to create bucket: {create_resp.text}")
		# Proceeding might fail, but let the upload try or fail naturally


def delete_existing_evaluations_for_user(user_id: str) -> None:
	"""Delete all existing program evaluations (and their files) for a user.

	This keeps at most one program evaluation per user at a time. It is used
	by the upload flow *before* inserting a new evaluation record.
	"""
	# Fetch all existing evaluations for this user
	eval_resp = supabase_request(
		"GET",
		f"/rest/v1/program_evaluations?user_id=eq.{user_id}&select=id,storage_path",
	)
	if eval_resp.status_code != 200:
		print(
			f"WARNING: Failed to load existing evaluations for user {user_id}: "
			f"{eval_resp.status_code} {eval_resp.text}"
		)
		return

	rows = eval_resp.json() or []
	for row in rows:
		eval_id = row.get("id")
		storage_path = row.get("storage_path")

		if eval_id:
			del_resp = supabase_request(
				"DELETE", f"/rest/v1/program_evaluations?id=eq.{eval_id}"
			)
			if del_resp.status_code not in (200, 204):
				print(
					f"WARNING: Failed to delete program_evaluations row {eval_id}: "
					f"{del_resp.status_code} {del_resp.text}"
				)

		if storage_path:
			storage_resp = supabase_request(
				"DELETE",
				f"/storage/v1/object/{BUCKET}/{storage_path}",
			)
			if storage_resp.status_code not in (200, 204):
				print(
					f"WARNING: Failed to delete stored evaluation file {storage_path}: "
					f"{storage_resp.status_code} {storage_resp.text}"
				)

def has_program_evaluation(email: str) -> bool:
    user_id = _get_user_id(email)
    if not user_id:
        return False
    
    resp = supabase_request(
        "GET", 
        f"/rest/v1/program_evaluations?user_id=eq.{user_id}&select=id", 
        headers={"Range": "0-0"}
    )
    return resp.status_code == 200 and len(resp.json()) > 0

def upload_evaluation_file(file: FileStorage, email: str) -> Tuple[str, int, bytes]:
    """
    Uploads file to Supabase Storage.
    Returns (storage_path, size_bytes, file_content_bytes).
    """
    user_id = _get_user_id(email)
    if not user_id:
        raise ValueError(f"User not found for {email}")

    _ensure_bucket_exists()

    file_bytes = file.read()
    size_bytes = len(file_bytes)
    file.seek(0) 

    # storage path: user_id/original_filename
    # Use forward slashes for storage paths
    filename = f"{user_id}/{file.filename}"
    
    # Supabase Storage Upload
    # Upsert true to overwrite if exists
    resp = supabase_request(
        "POST", 
        f"/storage/v1/object/{BUCKET}/{filename}", 
        data=file_bytes,
        headers={"Content-Type": "application/pdf", "x-upsert": "true"}
    )
    
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Upload failed: {resp.text}")
        
    return filename, size_bytes, file_bytes

def get_evaluation_file(email: str) -> Optional[bytes]:
    user_id = _get_user_id(email)
    if not user_id:
        return None

    # Get path from DB
    resp = supabase_request(
        "GET",
        f"/rest/v1/program_evaluations?user_id=eq.{user_id}&select=storage_path&order=created_at.desc&limit=1"
    )
    if resp.status_code != 200 or not resp.json():
        return None
    
    storage_path = resp.json()[0]["storage_path"]
    
    # Download
    # Use authenticated download if bucket is private
    # Note: For authenticated download, we usually POST to /object/sign or use bearer token with GET.
    # The supabase_request uses the service key (or anon key + token).
    # Direct GET to /storage/v1/object/authenticated/{bucket}/{path} works with RLS/Policies or Service Key.
    file_resp = supabase_request("GET", f"/storage/v1/object/authenticated/{BUCKET}/{storage_path}")
    if file_resp.status_code != 200:
        # Fallback to public? No, it should be private.
        # Maybe create signed url? For now, service key access is fine for backend.
        return None
        
    return file_resp.content

def save_metadata(
    email: str, 
    filename: str, 
    storage_path: str, 
    size_bytes: int, 
    parsed_data: Dict[str, Any]
) -> str:
    """
    Saves metadata to program_evaluations and sections.
    Returns evaluation_id.
    """
    user_id = _get_user_id(email)
    if not user_id:
        raise ValueError("User not found")

    # 1. Insert program_evaluation
    eval_payload = {
        "user_id": user_id,
        "storage_path": storage_path,
        "original_filename": filename,
        "file_size_bytes": size_bytes,
        "parsing_status": "completed",
        "processed_at": "now()", 
    }
    
    eval_resp = supabase_request(
        "POST",
        "/rest/v1/program_evaluations",
        json=eval_payload,
        headers={"Prefer": "return=representation"}
    )
    if eval_resp.status_code not in (200, 201):
        raise RuntimeError(f"DB Save failed: {eval_resp.text}")
    
    evaluation_id = eval_resp.json()[0]["id"]

    # 2. Insert Sections
    sections = []
    order = 0
    section_keys = [
        "student_info", 
        "gpa", 
        "credit_requirements", 
        "courses",
        "academic_status",
        "degree_requirements",
        "additional_programs",
        "transfer_credits",
        "semester_history",
        "advisor"
    ]
    for key in section_keys:
        if key in parsed_data:
            sections.append({
                "evaluation_id": evaluation_id,
                "section_name": key,
                "section_order": order,
                "content": parsed_data[key]
            })
            order += 1
            
    if sections:
        sec_resp = supabase_request("POST", "/rest/v1/program_evaluation_sections", json=sections)
        if sec_resp.status_code not in (200, 201):
            print(f"ERROR: Failed to save sections! {sec_resp.status_code} {sec_resp.text}")
            raise RuntimeError(f"Failed to save sections: {sec_resp.text}")
    
    # 3. Insert Snapshots (GPA)
    snapshots = []
    gpa = parsed_data.get("gpa", {})
    from datetime import date
    today = date.today().isoformat()
    
    if "overall" in gpa:
        snapshots.append({
            "user_id": user_id,
            "evaluation_id": evaluation_id,
            "snapshot_date": today,
            "metric_key": "gpa_overall",
            "metric_value": gpa["overall"]
        })
    if "major" in gpa:
        snapshots.append({
            "user_id": user_id,
            "evaluation_id": evaluation_id,
            "snapshot_date": today,
            "metric_key": "gpa_major",
            "metric_value": gpa["major"]
        })
        
    if snapshots:
        snap_resp = supabase_request("POST", "/rest/v1/student_progress_snapshots", json=snapshots)
        if snap_resp.status_code not in (200, 201):
            print(f"WARNING: Failed to save snapshots: {snap_resp.text}")

    return evaluation_id

def load_parsed_data(email: str) -> Optional[Dict[str, Any]]:
    user_id = _get_user_id(email)
    if not user_id:
        return None

    # Get latest evaluation
    eval_resp = supabase_request(
        "GET",
        f"/rest/v1/program_evaluations?user_id=eq.{user_id}&select=id,original_filename,created_at&order=created_at.desc&limit=1"
    )
    if eval_resp.status_code != 200 or not eval_resp.json():
        return None
    
    eval_rec = eval_resp.json()[0]
    eval_id = eval_rec["id"]
    
    # Get sections
    sect_resp = supabase_request(
        "GET",
        f"/rest/v1/program_evaluation_sections?evaluation_id=eq.{eval_id}&select=section_name,content"
    )
    
    parsed = {}
    if sect_resp.status_code == 200:
        rows = sect_resp.json()
        print(f"DEBUG: Loaded {len(rows)} sections for evaluation {eval_id}")
        for row in rows:
            print(f"DEBUG: Section '{row['section_name']}' found, content type: {type(row['content'])}")
            parsed[row["section_name"]] = row["content"]
    else:
        print(f"DEBUG: Failed to load sections: {sect_resp.status_code} {sect_resp.text}")
            
    return {
        "email": email,
        "uploaded_at": eval_rec["created_at"],
        "original_filename": eval_rec["original_filename"],
        "parsed_data": parsed
    }
