/**
 * Robust API client wrapper with retry logic, timeout handling, and typed responses.
 */

export type ApiSuccess<T> = {
  success: true;
  data: T;
};

export type ApiError = {
  success: false;
  error: string;
  status?: number;
  shouldSignOut?: boolean;
};

export type ApiResult<T> = ApiSuccess<T> | ApiError;

interface RequestOptions {
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  jwt?: string;
  timeout?: number;
  retries?: number;
}

const DEFAULT_TIMEOUT = 30000;
const DEFAULT_RETRIES = 3;
const RETRY_DELAYS: readonly number[] = [1000, 2000, 4000];

function isRetryableError(status: number): boolean {
  return status >= 500 && status <= 599;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getRetryDelay(attempt: number): number {
  return RETRY_DELAYS[Math.min(attempt, RETRY_DELAYS.length - 1)] ?? RETRY_DELAYS[0]!;
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeout: number
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}

async function request<T>(
  url: string,
  options: RequestOptions
): Promise<ApiResult<T>> {
  const { method, body, jwt, timeout = DEFAULT_TIMEOUT, retries = DEFAULT_RETRIES } = options;

  const headers: Record<string, string> = {
    Accept: 'application/json',
  };

  if (jwt) {
    headers['Authorization'] = `Bearer ${jwt}`;
  }

  if ((method === 'POST' || method === 'PATCH') && body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  const fetchOptions: RequestInit = {
    method,
    headers,
  };

  if (body !== undefined) {
    fetchOptions.body = JSON.stringify(body);
  }

  let lastError: Error | null = null;
  let lastStatus: number | undefined;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetchWithTimeout(url, fetchOptions, timeout);

      if (response.status === 401) {
        let errorMessage = 'Unauthorized';
        try {
          const errorData = await response.json();
          if (errorData?.error || errorData?.message) {
            errorMessage = errorData.error || errorData.message;
          }
        } catch {
          // Ignore JSON parse errors
        }
        return {
          success: false,
          error: errorMessage,
          status: 401,
          shouldSignOut: true,
        };
      }

      if (isRetryableError(response.status)) {
        lastStatus = response.status;
        lastError = new Error(`Server error: ${response.status}`);

        if (attempt < retries) {
          await delay(getRetryDelay(attempt));
          continue;
        }

        let errorMessage = `Server error: ${response.status}`;
        try {
          const errorData = await response.json();
          if (errorData?.error || errorData?.message) {
            errorMessage = errorData.error || errorData.message;
          }
        } catch {
          // Ignore JSON parse errors
        }

        return {
          success: false,
          error: errorMessage,
          status: response.status,
        };
      }

      if (!response.ok) {
        let errorMessage = `Request failed: ${response.status}`;
        try {
          const errorData = await response.json();
          if (errorData?.error || errorData?.message) {
            errorMessage = errorData.error || errorData.message;
          }
        } catch {
          // Ignore JSON parse errors
        }
        return {
          success: false,
          error: errorMessage,
          status: response.status,
        };
      }

      if (response.status === 204) {
        return {
          success: true,
          data: undefined as T,
        };
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const data = await response.json();
        return {
          success: true,
          data: data as T,
        };
      }

      const text = await response.text();
      return {
        success: true,
        data: text as T,
      };
    } catch (error) {
      const isNetworkError =
        error instanceof TypeError ||
        (error instanceof Error && error.name === 'AbortError');

      if (isNetworkError && attempt < retries) {
        lastError = error instanceof Error ? error : new Error(String(error));
        await delay(getRetryDelay(attempt));
        continue;
      }

      if (error instanceof Error && error.name === 'AbortError') {
        return {
          success: false,
          error: 'Request timed out',
        };
      }

      const errorMessage =
        error instanceof Error ? error.message : 'An unexpected error occurred';

      return {
        success: false,
        error: errorMessage,
        status: lastStatus,
      };
    }
  }

  return {
    success: false,
    error: lastError?.message || 'Request failed after retries',
    status: lastStatus,
  };
}

export const apiClient = {
  async get<T>(url: string, jwt?: string): Promise<ApiResult<T>> {
    return request<T>(url, { method: 'GET', jwt });
  },

  async post<T>(url: string, body?: unknown, jwt?: string): Promise<ApiResult<T>> {
    return request<T>(url, { method: 'POST', body, jwt });
  },

  async patch<T>(url: string, body?: unknown, jwt?: string): Promise<ApiResult<T>> {
    return request<T>(url, { method: 'PATCH', body, jwt });
  },

  async delete<T>(url: string, jwt?: string): Promise<ApiResult<T>> {
    return request<T>(url, { method: 'DELETE', jwt });
  },
};

export default apiClient;
