import { backendBaseUrl } from "./backend";
import type { Job } from "@/app/lib/data/jobs";


export async function fetchJobs() : Promise<Job[]> {
    const response = await fetch(`${backendBaseUrl}/jobs`,{cache: "no-store"})
    if(!response.ok){
        throw new Error(`GET /jobs failed with ${response.status}`)
    }

    return response.json();
}

export async function fetchJob(id : number) : Promise<Job | null> {
    const result = await fetch(`${backendBaseUrl}/jobs/${id}`, { cache: "no-store" });

    // A missing job is an expected outcome, not a failure.
    if(result.status === 404){
        return null;
    }

    if(!result.ok){
        throw new Error(`GET /jobs/${id} failed with ${result.status}`)
    }

    return result.json()
}