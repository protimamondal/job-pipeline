import { backendBaseUrl } from "./backend";
import type { Job } from "@/app/lib/data/jobs";

/** The backend protects every job route, so callers must pass a token. */
function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

export async function fetchJobs(token: string): Promise<Job[]> {
  const response = await fetch(`${backendBaseUrl}/jobs`, {
    cache: "no-store",
    headers: authHeaders(token),
  });

  if (!response.ok) {
    throw new Error(`GET /jobs failed with ${response.status}`);
  }

  return response.json();
}

export async function fetchJob(
  id: number,
  token: string,
): Promise<Job | null> {
  const result = await fetch(`${backendBaseUrl}/jobs/${id}`, {
    cache: "no-store",
    headers: authHeaders(token),
  });

  // A missing job is an expected outcome, not a failure.
  if (result.status === 404) {
    return null;
  }

  if (!result.ok) {
    throw new Error(`GET /jobs/${id} failed with ${result.status}`);
  }

  return result.json();
}
