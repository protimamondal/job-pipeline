import { getToken } from "@/app/lib/auth";
import { backendBaseUrl } from "@/app/lib/backend";

export async function POST(req : Request){
 const token = await getToken();
 if(token==null){
    return new Response("Not authenticated",{status : 401})
 }

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
