// PAGE 1 â€” the pipeline list.
// Skeleton only: layout and styling, static placeholder markup.
// You write the grouping and the mapping over `jobs`.
"use client"

import { useState } from "react";
import { JobStatus, Job, jobs, jobsByStatus } from "./lib/data/jobs";
import Link from "next/link";

export default function PipelinePage() {
  //const [jobsList, setJobsList] = useState<Job[]>(jobs)

  const ORDER : JobStatus[] = ["interviewing","applied","saved",
    "rejected"
  ]

  const jobList  = jobs.reduce<jobsByStatus>((acc,cur)=>{
    acc[cur.status].push(cur)
    return acc;
  },{
    interviewing : [],
    applied : [],
    saved : [],
    rejected : [],
  })
  

  return (
    <main className="mx-auto max-w-3xl p-6">
      <h1 className="mb-6 text-xl font-semibold">My pipeline</h1>

      {/* one group per status â€” repeat this section per group */}
      {ORDER.map(status=>{
        const rows = jobList[status]
        return (
        <section key={status} className="mb-8">
        <h2 className="mb-2 border-b border-black/10 pb-1 text-xs uppercase tracking-wide text-gray-500 dark:border-white/15">
          {status} - {rows.length}
        </h2>

        {/* one of these per job */}
        {
          rows.map(row=>(
        <Link key={row.id} href={`/jobs/${row.id}`} className="block rounded-lg px-3 py-2.5 hover:bg-black/5 dark:hover:bg-white/10">
          <div className="font-medium">{row.title}</div>
          <div className="text-sm text-gray-500"  >
            {row.company} . {row.location} . ${row.salary_usd}
          </div>
        </Link>
          ))
        }

      </section>
        )
})}
    
    </main>
  );
}
