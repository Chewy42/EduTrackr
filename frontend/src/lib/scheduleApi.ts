/**
 * Schedule API functions for the schedule builder feature.
 * Provides typed API calls for class search, validation, and requirements.
 */
import type {
	  ClassSection,
	  ClassSearchParams,
	  ClassesSearchResponse,
	  RequirementsSummary,
	  ScheduleValidation,
	  StatsResponse,
	  SubjectsResponse,
	  ScheduleSnapshot,
	} from '../components/schedule/types';

const API_BASE = '/api';

/**
 * Search and filter available classes.
 */
export async function searchClasses(
  params: ClassSearchParams = {},
  jwt?: string
): Promise<ClassesSearchResponse> {
  const searchParams = new URLSearchParams();
  
  if (params.search) searchParams.set('search', params.search);
  if (params.days?.length) searchParams.set('days', params.days.join(','));
  if (params.timeStart !== undefined) searchParams.set('time_start', params.timeStart.toString());
  if (params.timeEnd !== undefined) searchParams.set('time_end', params.timeEnd.toString());
  if (params.creditsMin !== undefined) searchParams.set('credits_min', params.creditsMin.toString());
  if (params.creditsMax !== undefined) searchParams.set('credits_max', params.creditsMax.toString());
  if (params.subject) searchParams.set('subject', params.subject);
  if (params.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params.offset !== undefined) searchParams.set('offset', params.offset.toString());
  if (params.includeRequirements !== undefined) {
    searchParams.set('include_requirements', params.includeRequirements.toString());
  }
  
  const url = `${API_BASE}/schedule/classes?${searchParams.toString()}`;
  
  const headers: Record<string, string> = {
    'Accept': 'application/json',
  };
  
  if (jwt) {
    headers['Authorization'] = `Bearer ${jwt}`;
  }
  
  const res = await fetch(url, { headers });
  
  if (!res.ok) {
    throw new Error(`Failed to search classes: ${res.status}`);
  }
  
  return res.json();
}

/**
 * Get a single class by ID.
 */
export async function getClassById(
  classId: string,
  jwt?: string
): Promise<ClassSection> {
  const headers: Record<string, string> = {
    'Accept': 'application/json',
  };
  
  if (jwt) {
    headers['Authorization'] = `Bearer ${jwt}`;
  }
  
  const res = await fetch(`${API_BASE}/schedule/classes/${classId}`, { headers });
  
  if (!res.ok) {
    if (res.status === 404) {
      throw new Error('Class not found');
    }
    throw new Error(`Failed to get class: ${res.status}`);
  }
  
  return res.json();
}

/**
 * Validate a schedule for conflicts.
 */
export async function validateSchedule(
  classIds: string[]
): Promise<ScheduleValidation> {
  const res = await fetch(`${API_BASE}/schedule/validate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ classes: classIds }),
  });
  
  if (!res.ok) {
    throw new Error(`Failed to validate schedule: ${res.status}`);
  }
  
  return res.json();
}

/**
 * Get user's remaining degree requirements.
 * Requires authentication.
 */
export async function getUserRequirements(
  jwt: string
): Promise<RequirementsSummary> {
  const res = await fetch(`${API_BASE}/schedule/user-requirements`, {
    headers: {
      'Authorization': `Bearer ${jwt}`,
      'Accept': 'application/json',
    },
  });
  
  if (!res.ok) {
    if (res.status === 401) {
      throw new Error('Unauthorized');
    }
    throw new Error(`Failed to get requirements: ${res.status}`);
  }
  
  return res.json();
}

/**
 * Auto-generate a schedule based on user preferences.
 * Requires authentication.
 */
export async function generateAutoSchedule(
  jwt: string
): Promise<{ class_ids: string[]; message?: string }> {
  const res = await fetch(`${API_BASE}/schedule/generate`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${jwt}`,
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    },
  });
  
  if (!res.ok) {
    // Try to parse error message from response
    let errorMessage = `Failed to generate schedule: ${res.status}`;
    try {
      const errorData = await res.json();
      if (errorData.error) {
        errorMessage = errorData.error;
      }
    } catch {
      // Ignore JSON parse errors for error response
    }
    
    if (res.status === 401) {
      throw new Error('Session expired. Please log in again.');
    }
    throw new Error(errorMessage);
  }
  
  return res.json();
}

/**
 * Get list of all available subjects.
 */
export async function getSubjects(): Promise<SubjectsResponse> {
  const res = await fetch(`${API_BASE}/schedule/subjects`, {
    headers: {
      'Accept': 'application/json',
    },
  });
  
  if (!res.ok) {
    throw new Error(`Failed to get subjects: ${res.status}`);
  }
  
  return res.json();
}

/**
 * Get statistics about available classes.
 */
export async function getScheduleStats(): Promise<StatsResponse> {
  const res = await fetch(`${API_BASE}/schedule/stats`, {
    headers: {
      'Accept': 'application/json',
    },
  });
  
  if (!res.ok) {
    throw new Error(`Failed to get stats: ${res.status}`);
  }
  
  return res.json();
}

/**
 * Save the current schedule as a named snapshot for the authenticated user.
 */
export async function createScheduleSnapshot(
	name: string,
	classIds: string[],
	totalCredits: number,
	jwt: string,
): Promise<ScheduleSnapshot> {
	const res = await fetch(`${API_BASE}/schedule/snapshots`, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${jwt}`,
			Accept: 'application/json',
			'Content-Type': 'application/json',
		},
		body: JSON.stringify({
			name,
			class_ids: classIds,
			total_credits: totalCredits,
		}),
	});

	if (!res.ok) {
		let message = `Failed to save schedule snapshot: ${res.status}`;
		try {
			const data = await res.json();
			if (data?.error) {
				message = data.error;
			}
		} catch {
			// Ignore JSON parse errors when reading error response
		}
		throw new Error(message);
	}

	return res.json();
}

/**
 * Get all schedule snapshots for the authenticated user.
 */
export async function listScheduleSnapshots(jwt: string): Promise<ScheduleSnapshot[]> {
	const res = await fetch(`${API_BASE}/schedule/snapshots`, {
		headers: {
			Authorization: `Bearer ${jwt}`,
			Accept: 'application/json',
		},
	});

	if (!res.ok) {
		throw new Error(`Failed to load schedule snapshots: ${res.status}`);
	}

	const data = await res.json();
	// Backend returns { snapshots: [...] }
	return Array.isArray(data.snapshots) ? data.snapshots : [];
}

/**
 * Delete a schedule snapshot by ID for the authenticated user.
 */
export async function deleteScheduleSnapshot(
	snapshotId: string,
	jwt: string,
): Promise<void> {
	const res = await fetch(`${API_BASE}/schedule/snapshots/${snapshotId}`, {
		method: 'DELETE',
		headers: {
			Authorization: `Bearer ${jwt}`,
			Accept: 'application/json',
		},
	});

	if (!res.ok && res.status !== 404) {
		// 404 can be safely treated as "already deleted"
		throw new Error(`Failed to delete schedule snapshot: ${res.status}`);
	}
}
