import { cookies } from "next/headers";

/** Clear the session cookie. The token itself stays valid until it expires. */
export async function POST() {
  const cookieStore = await cookies();
  cookieStore.delete("token");

  return Response.json({ ok: true });
}
