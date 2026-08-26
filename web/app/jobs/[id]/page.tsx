// PAGE 2 — one job.
// Skeleton only: layout and styling, static placeholder markup.
// You write the params handling and the lookup in `jobs`.

import Link from "next/link";
import { jobs } from "@/app/lib/data/jobs";
import { notFound } from "next/navigation";
import DraftPanel from "@/app/components/DraftPanel";

type JobDesc = {
  params : Promise<{id : string}>
}


export default async function JobPage({params}: JobDesc) {

  const {id} = await params

const jobWithId = jobs.find(job=>job.id === id)

if(!jobWithId){
  notFound();
}

  return (
    <main className="mx-auto max-w-3xl p-6">
      <Link href="/" className="text-sm text-blue-700 hover:underline">
        ← My pipeline
      </Link>

      <h1 className="mt-3 text-xl font-semibold">{jobWithId.title}</h1>
      <div className="text-sm text-gray-500">{jobWithId.company} · {jobWithId.location} · {jobWithId.salary_usd !== null ? `$${jobWithId.salary_usd.toLocaleString()}` : "salary not listed"}</div>

      <h2 className="mt-8 text-xs uppercase tracking-wide text-gray-500">
        Job description
      </h2>
      <div className="mt-2 whitespace-pre-line text-sm leading-relaxed">
        {jobWithId.description}
      </div>

      <DraftPanel id= {id}/>
    </main>
  );
}
