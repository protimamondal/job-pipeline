import { cookies } from "next/headers";

import { backendBaseUrl } from "@/app/lib/backend";

/**
 * Create an account and sign the new user straight in.
 *
 * Registering does not return a token — the backend answers with the user —
 * so this logs in with the same credentials and sets the cookie, sparing the
 * user a second form.
 */
export async function POST(request: Request) {
  const { name, email, password } = await request.json();

  const registered = await fetch(`${backendBaseUrl}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password }),
  });

  if (!registered.ok) {
    const detail =
      registered.status === 409
        ? "That email is already registered."
        : "Could not create the account.";
    return Response.json({ detail }, { status: registered.status });
  }

  const loggedIn = await fetch(`${backendBaseUrl}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!loggedIn.ok) {
    // The account exists, so send them to sign in by hand rather than failing.
    return Response.json({ ok: true, signedIn: false });
  }

  const { access_token } = await loggedIn.json();

  const cookieStore = await cookies();
  cookieStore.set("token", access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60,
  });

  return Response.json({ ok: true, signedIn: true });
}
