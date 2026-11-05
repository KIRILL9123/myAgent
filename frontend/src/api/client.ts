export class ApiError extends Error {
  status: number;
  detail: string;
  data?: unknown;

  constructor(message: string, status: number, detail = message, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.data = data;
  }
}

function getHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers({
    Accept: 'application/json',
    'X-API-Key': (import.meta.env.VITE_API_KEY as string) || '',
  });
  new Headers(extra).forEach((value, key) => headers.set(key, value));
  return headers;
}

async function readError(response: Response): Promise<{ message: string; data?: unknown }> {
  const text = await response.text();
  if (!text) return { message: `${response.status} ${response.statusText}`.trim() };
  try {
    const payload = JSON.parse(text) as { detail?: unknown; message?: unknown };
    const detail = payload.detail;
    const message = typeof detail === 'string'
      ? detail
      : typeof payload.message === 'string'
        ? payload.message
        : text;
    return { message, data: detail };
  } catch {
    return { message: text };
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, { ...init, headers: getHeaders(init.headers) });
  if (!response.ok) {
    const error = await readError(response);
    throw new ApiError(error.message, response.status, error.message, error.data);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
