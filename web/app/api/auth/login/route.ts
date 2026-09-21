import { cookies } from "next/headers";

import { backendBaseUrl } from "@/app/lib/backend";

export async function POST(request: Request) {
  const body = await request.json();

  const response = await fetch(`${backendBaseUrl}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    return Response.json(
      { detail: "Invalid email or password" },
      { status: 401 },
    );
  }

  const { access_token } = await response.json();

  const cookieStore = await cookies();
  cookieStore.set("token", access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    // Matches the backend's access_token_expire_minutes.
    maxAge: 60 * 60,
  });

  return Response.json({ ok: true });
}
