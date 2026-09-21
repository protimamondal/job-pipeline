import { cookies } from "next/headers";
import { redirect } from "next/navigation";

/** The signed-in user's token, or null when there is no usable cookie. */
export async function getToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get("token")?.value ?? null;
}

/**
 * The signed-in user's token, or a redirect to the sign-in page.
 *
 * Use this at the top of any page that cannot render without a user.
 */
export async function requireToken(): Promise<string> {
  const token = await getToken();

  if (token === null) {
    redirect("/login");
  }

  return token;
}
