import { getToken } from "@/app/lib/auth";
import { backendBaseUrl } from "@/app/lib/backend";

/**
 * Add a job to the signed-in user's pipeline.
 *
 * The browser cannot read the httpOnly token cookie, so mutations go through
 * here: the browser posts same-origin, and this reads the cookie server-side
 * and forwards it to FastAPI.
 */
export async function POST(request: Request) {
  const token = await getToken();
  if (token === null) {
    return Response.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const body = await request.json();

  const response = await fetch(`${backendBaseUrl}/applications`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });

  return Response.json(await response.json(), { status: response.status });
}
