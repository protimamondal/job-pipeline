import { getToken } from "@/app/lib/auth";
import { backendBaseUrl } from "@/app/lib/backend";

// Render will not wake a sleeping free service for a request coming from
// another Render service, so the backend cannot wake the MCP server itself:
// it gets a 429 in 0.3s and the server stays asleep. Vercel is outside
// Render, so this request can wake it. Deliberately not awaited -- the chat
// is not delayed, and the backend retries its own connection until the
// server is up.
function wakeJobSearchService() {
  const mcpServerUrl = process.env.MCP_SERVER_URL;
  if (!mcpServerUrl) return;

  try {
    // Any status proves something is listening; the answer is not used.
    // no-store because a cached response would skip the request entirely,
    // which is the one thing this call exists to make.
    void fetch(new URL(mcpServerUrl).origin, { cache: "no-store" }).catch(
      () => {},
    );
  } catch {
    // A malformed URL must not stop the chat.
  }
}

export async function POST(req : Request){
 const token = await getToken();
 if(token==null){
    return new Response("Not authenticated",{status : 401})
 }

 wakeJobSearchService();

 const backendResponse = await fetch(`${backendBaseUrl}/chat`,{
    method: "POST",
    headers:{
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
    },
    body: await req.text(),
    signal: req.signal,
 })

 return new Response(backendResponse.body,{
    status: backendResponse.status,
    headers: backendResponse.headers,
 })
}
