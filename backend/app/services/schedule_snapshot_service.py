"""
Schedule Snapshot Service - CRUD operations for saved schedule snapshots.
Allows users to save, list, load, and delete schedule snapshots.
"""
from typing import Any, Dict, List, Optional

from app.models.schedule_types import ScheduleSnapshot
from app.services.supabase_client import supabase_request


def _get_user_id(email: str) -> Optional[str]:
    """Get user_id from email address."""
    resp = supabase_request("GET", f"/rest/v1/app_users?email=eq.{email}&select=id")
    if resp.status_code == 200 and resp.json():
        return resp.json()[0]["id"]
    return None


class SnapshotError(Exception):
    """Base exception for snapshot operations."""
    pass


class DuplicateNameError(SnapshotError):
    """Raised when trying to create a snapshot with a duplicate name."""
    pass


class SnapshotNotFoundError(SnapshotError):
    """Raised when a snapshot is not found."""
    pass


def save_snapshot(
    email: str,
    name: str,
    class_ids: List[str],
    total_credits: float,
) -> ScheduleSnapshot:
    """
    Save a new schedule snapshot.
    
    Args:
        email: User's email address
        name: User-defined snapshot name
        class_ids: List of class IDs in the schedule
        total_credits: Total credits in the schedule
    
    Returns:
        The created ScheduleSnapshot
    
    Raises:
        ValueError: If user not found or name is empty
        DuplicateNameError: If a snapshot with this name already exists
    """
    user_id = _get_user_id(email)
    if not user_id:
        raise ValueError(f"User not found for email: {email}")
    
    name = name.strip()
    if not name:
        raise ValueError("Snapshot name cannot be empty")
    
    schedule_data: Dict[str, Any] = {
        "class_ids": class_ids,
        "total_credits": total_credits,
        "class_count": len(class_ids),
    }
    
    payload = {
        "user_id": user_id,
        "name": name,
        "schedule_data": schedule_data,
    }
    
    resp = supabase_request(
        "POST",
        "/rest/v1/schedule_snapshots",
        json=payload,
        headers={"Prefer": "return=representation"},
    )
    
    if resp.status_code == 409 or (resp.status_code == 400 and "duplicate" in resp.text.lower()):
        raise DuplicateNameError(f"A snapshot named '{name}' already exists")
    
    if resp.status_code not in (200, 201):
        raise SnapshotError(f"Failed to save snapshot: {resp.text}")
    
    rows = resp.json()
    if not rows:
        raise SnapshotError("No data returned from insert")
    
    return ScheduleSnapshot.from_db_row(rows[0])


def list_snapshots(email: str) -> List[ScheduleSnapshot]:
    """
    List all snapshots for a user, ordered by creation date (newest first).
    
    Args:
        email: User's email address
    
    Returns:
        List of ScheduleSnapshot objects
    """
    user_id = _get_user_id(email)
    if not user_id:
        return []
    
    resp = supabase_request(
        "GET",
        f"/rest/v1/schedule_snapshots?user_id=eq.{user_id}&order=created_at.desc",
    )
    
    if resp.status_code != 200:
        return []
    
    rows = resp.json() or []
    return [ScheduleSnapshot.from_db_row(row) for row in rows]


def get_snapshot(email: str, snapshot_id: str) -> Optional[ScheduleSnapshot]:
    """
    Get a specific snapshot by ID.

    Args:
        email: User's email address (for ownership verification)
        snapshot_id: UUID of the snapshot

    Returns:
        ScheduleSnapshot if found, None otherwise
    """
    user_id = _get_user_id(email)
    if not user_id:
        return None

    resp = supabase_request(
        "GET",
        f"/rest/v1/schedule_snapshots?id=eq.{snapshot_id}&user_id=eq.{user_id}",
    )

    if resp.status_code != 200:
        return None

    rows = resp.json() or []
    if not rows:
        return None

    return ScheduleSnapshot.from_db_row(rows[0])


def get_snapshot_by_name(email: str, name: str) -> Optional[ScheduleSnapshot]:
    """
    Get a snapshot by name.

    Args:
        email: User's email address
        name: Snapshot name to look up

    Returns:
        ScheduleSnapshot if found, None otherwise
    """
    user_id = _get_user_id(email)
    if not user_id:
        return None

    # URL-encode the name for the query
    import urllib.parse
    encoded_name = urllib.parse.quote(name, safe="")

    resp = supabase_request(
        "GET",
        f"/rest/v1/schedule_snapshots?user_id=eq.{user_id}&name=eq.{encoded_name}",
    )

    if resp.status_code != 200:
        return None

    rows = resp.json() or []
    if not rows:
        return None

    return ScheduleSnapshot.from_db_row(rows[0])


def delete_snapshot(email: str, snapshot_id: str) -> bool:
    """
    Delete a snapshot by ID.

    Args:
        email: User's email address (for ownership verification)
        snapshot_id: UUID of the snapshot to delete

    Returns:
        True if deleted, False if not found or error
    """
    user_id = _get_user_id(email)
    if not user_id:
        return False

    resp = supabase_request(
        "DELETE",
        f"/rest/v1/schedule_snapshots?id=eq.{snapshot_id}&user_id=eq.{user_id}",
    )

    return resp.status_code in (200, 204)


def update_snapshot(
    email: str,
    snapshot_id: str,
    name: Optional[str] = None,
    class_ids: Optional[List[str]] = None,
    total_credits: Optional[float] = None,
) -> Optional[ScheduleSnapshot]:
    """
    Update an existing snapshot.

    Args:
        email: User's email address (for ownership verification)
        snapshot_id: UUID of the snapshot to update
        name: New name (optional)
        class_ids: New class IDs (optional)
        total_credits: New total credits (optional)

    Returns:
        Updated ScheduleSnapshot if successful, None otherwise

    Raises:
        DuplicateNameError: If the new name already exists
    """
    user_id = _get_user_id(email)
    if not user_id:
        return None

    # First, get the existing snapshot to merge schedule_data
    existing = get_snapshot(email, snapshot_id)
    if not existing:
        return None

    payload: Dict[str, Any] = {}

    if name is not None:
        name = name.strip()
        if not name:
            raise ValueError("Snapshot name cannot be empty")
        payload["name"] = name

    # Build updated schedule_data if class_ids or total_credits changed
    if class_ids is not None or total_credits is not None:
        schedule_data: Dict[str, Any] = {
            "class_ids": class_ids if class_ids is not None else existing.class_ids,
            "total_credits": total_credits if total_credits is not None else existing.total_credits,
            "class_count": len(class_ids) if class_ids is not None else existing.class_count,
        }
        payload["schedule_data"] = schedule_data

    if not payload:
        # Nothing to update
        return existing

    resp = supabase_request(
        "PATCH",
        f"/rest/v1/schedule_snapshots?id=eq.{snapshot_id}&user_id=eq.{user_id}",
        json=payload,
        headers={"Prefer": "return=representation"},
    )

    if resp.status_code == 409 or (resp.status_code == 400 and "duplicate" in resp.text.lower()):
        raise DuplicateNameError(f"A snapshot named '{name}' already exists")

    if resp.status_code not in (200, 204):
        return None

    rows = resp.json() or []
    if not rows:
        return None

    return ScheduleSnapshot.from_db_row(rows[0])

