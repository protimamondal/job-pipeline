// The job board: every job that exists, whether or not you track it.

import Link from "next/link";

import BackendHealth from "../components/BackendHealth";
import { requireToken } from "../lib/auth";
import { fetchApplications } from "../lib/applicationsApi";
import { fetchJobs } from "../lib/jobsApi";
import type { Job } from "../lib/data/jobs";
import type { Application } from "../lib/data/applications";

export default async function JobBoardPage() {
  const token = await requireToken();

  let jobs: Job[];
  let applications: Application[];
  try {
    [jobs, applications] = await Promise.all([
      fetchJobs(token),
      fetchApplications(token),
    ]);
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

  const trackedJobIds = new Set(
    applications.map((application) => application.job.id),
  );

  return (
    <main className="mx-auto max-w-3xl p-6">
      <BackendHealth />

      <div className="mb-6 flex items-baseline justify-between">
        <h1 className="text-xl font-semibold">Jobs</h1>
        <Link href="/" className="text-sm text-blue-700 hover:underline">
          ← My pipeline
        </Link>
      </div>

      <p className="mb-4 text-sm text-gray-500">{jobs.length} open roles</p>

      {jobs.map((job) => (
        <Link
          key={job.id}
          href={`/jobs/${job.id}`}
          className="block rounded-lg px-3 py-2.5 hover:bg-black/5 dark:hover:bg-white/10"
        >
          <div className="flex items-baseline gap-2">
            <span className="font-medium">{job.title}</span>
            {trackedJobIds.has(job.id) && (
              <span className="text-xs text-gray-500">· tracked</span>
            )}
          </div>
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
