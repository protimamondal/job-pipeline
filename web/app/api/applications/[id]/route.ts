import { getToken } from "@/app/lib/auth";
import { backendBaseUrl } from "@/app/lib/backend";

type Context = { params: Promise<{ id: string }> };

export async function PATCH(request: Request, { params }: Context) {
  const token = await getToken();
  if (token === null) {
    return Response.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const { id } = await params;
  const body = await request.json();

  const response = await fetch(`${backendBaseUrl}/applications/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });

  return Response.json(await response.json(), { status: response.status });
}

export async function DELETE(_request: Request, { params }: Context) {
  const token = await getToken();
  if (token === null) {
    return Response.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const { id } = await params;

  const response = await fetch(`${backendBaseUrl}/applications/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });

  // 204 carries no body, so there is nothing to forward.
  return new Response(null, { status: response.status });
}
