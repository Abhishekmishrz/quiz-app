import type { ApiErrorEnvelope } from '../types';

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) || 'http://localhost:8000';

const API_PREFIX = '/api/v1';

/**
 * Typed error thrown for any non-2xx response from the backend.
 * Carries the HTTP status plus whatever the backend's
 * `{"detail": str, "code": str}` error envelope contained.
 */
export class ApiError extends Error {
  status: number;
  detail: string;
  code?: string;

  constructor(status: number, detail: string, code?: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.code = code;
  }
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  userId?: string;
  /** Additional query string parameters to append to the path. */
  query?: Record<string, string | number | undefined>;
}

function buildUrl(path: string, query?: RequestOptions['query']): string {
  const url = new URL(`${API_PREFIX}${path}`, API_BASE_URL);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

/**
 * Shared fetch wrapper used by every resource-specific API module.
 * - Prefixes paths with the configured base URL + /api/v1.
 * - Attaches X-User-Id when a userId is supplied.
 * - Parses JSON responses.
 * - Throws ApiError on any non-2xx response.
 */
export async function apiRequest<TResponse>(
  path: string,
  options: RequestOptions = {},
): Promise<TResponse> {
  const { method = 'GET', body, userId, query } = options;

  const headers: Record<string, string> = {};
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  if (userId) {
    headers['X-User-Id'] = userId;
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'Unable to reach the server. Please check your connection and try again.');
  }

  // 204 No Content or empty body
  const text = await response.text();
  let data: unknown = undefined;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = undefined;
    }
  }

  if (!response.ok) {
    const envelope = (data ?? {}) as ApiErrorEnvelope;
    const detail = envelope.detail || response.statusText || 'Something went wrong.';
    throw new ApiError(response.status, detail, envelope.code);
  }

  return data as TResponse;
}
