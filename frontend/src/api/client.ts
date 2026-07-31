export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(message: string, status: number, detail = message) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
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

async function readError(response: Response): Promise<string> {
  const text = await response.text();
  if (!text) return `${response.status} ${response.statusText}`.trim();
  try {
    const payload = JSON.parse(text) as { detail?: string; message?: string };
    return payload.detail || payload.message || text;
  } catch {
    return text;
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, { ...init, headers: getHeaders(init.headers) });
  if (!response.ok) {
    const detail = await readError(response);
    throw new ApiError(detail, response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
