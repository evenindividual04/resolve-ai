const API_BASE_DEFAULT = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const API_BASE = API_BASE_DEFAULT;

class ApiError extends Error {
  constructor(public status: number, public isTimeout: boolean, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

type FetchOptions = {
  revalidate?: number | false;
  tags?: string[];
  timeoutMs?: number;
  retries?: number;
};

/**
 * Server-side fetch wrapper with:
 * - Retry with exponential backoff (1s, 2s, 4s)
 * - AbortController timeout (default 10s)
 * - No retry on 4xx client errors
 * - Next.js revalidation strategy via `next: { revalidate }`
 */
export async function fetchJson<T>(
  path: string,
  { revalidate, tags, timeoutMs = 10_000, retries = 3 }: FetchOptions = {}
): Promise<T> {
  const url = `${API_BASE_DEFAULT}${path}`;

  const nextOptions: { revalidate?: number | false; tags?: string[] } = {};
  if (revalidate !== undefined) nextOptions.revalidate = revalidate;
  if (tags) nextOptions.tags = tags;

  // cache: "no-store" is the default if no revalidate is specified
  const cacheStrategy = revalidate !== undefined ? undefined : "no-store";

  let attempt = 0;
  const delays = [1000, 2000, 4000];

  while (attempt < retries) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const res = await fetch(url, {
        signal: controller.signal,
        cache: cacheStrategy,
        next: Object.keys(nextOptions).length > 0 ? nextOptions : undefined,
      });

      clearTimeout(timer);

      if (res.ok) return res.json() as Promise<T>;

      // Don't retry on client errors
      if (res.status >= 400 && res.status < 500) {
        throw new ApiError(res.status, false, `Client error ${res.status} fetching ${path}`);
      }

      throw new ApiError(res.status, false, `Server error ${res.status} fetching ${path}`);
    } catch (err) {
      clearTimeout(timer);
      const isTimeout = (err as Error).name === "AbortError";

      attempt++;
      if (attempt >= retries) {
        throw new ApiError(0, isTimeout, isTimeout ? `Timeout fetching ${path}` : `Failed to fetch ${path}`);
      }

      await new Promise((r) => setTimeout(r, delays[attempt - 1]));
    }
  }

  throw new ApiError(0, false, `Exhausted retries for ${path}`);
}
