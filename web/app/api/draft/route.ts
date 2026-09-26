import { getToken } from "@/app/lib/auth";
import { backendBaseUrl } from "@/app/lib/backend";

export async function POST(req: Request) {
  const { id,prompt } = await req.json();

  const token = await getToken();
  if (token === null) {
    return new Response("Not authenticated", { status: 401 });
  }

  const backendResponse = await fetch(`${backendBaseUrl}/jobs/${id}/draft`,{
    method: "POST",
    headers:{
      "Content-Type":"application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({instruction: prompt || null}),
    signal: req.signal
  })


  return new Response(backendResponse.body,{
    status: backendResponse.status,
    headers: backendResponse.headers
  })
}
