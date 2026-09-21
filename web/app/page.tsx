// The job board: every job that exists, not just the ones you track.
// "My pipeline" reads /applications instead, and arrives in a later slice.

import Link from "next/link";

import BackendHealth from "./components/BackendHealth";
import { requireToken } from "./lib/auth";
import { fetchJobs } from "./lib/jobsApi";
import type { Job } from "./lib/data/jobs";

export default async function JobBoardPage() {
  const token = await requireToken();

  let jobs: Job[];
  try {
    jobs = await fetchJobs(token);
  } catch {
    return (
      <main className="mx-auto max-w-3xl p-6">
        <BackendHealth />
        <h1 className="mb-6 text-xl font-semibold">Jobs</h1>
        <p className="text-sm text-gray-500">
          Could not load jobs — the backend is not reachable.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl p-6">
      <BackendHealth />
      <h1 className="mb-1 text-xl font-semibold">Jobs</h1>
      <p className="mb-6 text-sm text-gray-500">{jobs.length} open roles</p>

      {jobs.map((job) => (
        <Link
          key={job.id}
          href={`/jobs/${job.id}`}
          className="block rounded-lg px-3 py-2.5 hover:bg-black/5 dark:hover:bg-white/10"
        >
          <div className="font-medium">{job.title}</div>
          <div className="text-sm text-gray-500">
            {job.company} · {job.location} ·{" "}
            {job.salary_usd !== null
              ? `$${job.salary_usd.toLocaleString()}`
              : "salary not listed"}
          </div>
        </Link>
      ))}
    </main>
  );
}
