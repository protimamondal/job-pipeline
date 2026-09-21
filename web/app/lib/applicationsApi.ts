import { backendBaseUrl } from "./backend";
import type { Application } from "@/app/lib/data/applications";

/** The signed-in user's pipeline. Server-side only — it needs the token. */
export async function fetchApplications(token: string): Promise<Application[]> {
  const response = await fetch(`${backendBaseUrl}/applications`, {
    cache: "no-store",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    throw new Error(`GET /applications failed with ${response.status}`);
  }

  return response.json();
}
