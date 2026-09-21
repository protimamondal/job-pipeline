// My pipeline: the jobs this user chose to track, grouped by their own status.
// The board of every job lives at /jobs.

import Link from "next/link";

import ApplicationControls from "./components/ApplicationControls";
import BackendHealth from "./components/BackendHealth";
import SignOut from "./components/SignOut";
import { requireToken } from "./lib/auth";
import { fetchApplications } from "./lib/applicationsApi";
import type {
  Application,
  applicationsByStatus,
} from "./lib/data/applications";
import type { JobStatus } from "./lib/data/jobs";

const ORDER: JobStatus[] = ["interviewing", "applied", "saved", "rejected"];

export default async function PipelinePage() {
  const token = await requireToken();

  let applications: Application[];
  try {
    applications = await fetchApplications(token);
  } catch {
    return (
      <main className="mx-auto max-w-3xl p-6">
        <BackendHealth />
        <h1 className="mb-6 text-xl font-semibold">My pipeline</h1>
        <p className="text-sm text-gray-500">
          Could not load your pipeline — the backend is not reachable.
        </p>
      </main>
    );
  }

  const grouped = applications.reduce<applicationsByStatus>(
    (acc, application) => {
      acc[application.status].push(application);
      return acc;
    },
    { interviewing: [], applied: [], saved: [], rejected: [] },
  );

  return (
    <main className="mx-auto max-w-3xl p-6">
      <BackendHealth />

      <div className="mb-6 flex items-baseline justify-between">
        <h1 className="text-xl font-semibold">My pipeline</h1>
        <div className="flex items-baseline gap-4">
          <Link href="/jobs" className="text-sm text-blue-700 hover:underline">
            Browse jobs →
          </Link>
          <SignOut />
        </div>
      </div>

      {applications.length === 0 && (
        <p className="text-sm text-gray-500">
          Nothing tracked yet.{" "}
          <Link href="/jobs" className="underline underline-offset-2">
            Browse jobs
          </Link>{" "}
          and add the ones you care about.
        </p>
      )}

      {ORDER.map((status) => {
        const rows = grouped[status];
        if (rows.length === 0) return null;

        return (
          <section key={status} className="mb-8">
            <h2 className="mb-2 border-b border-black/10 pb-1 text-xs uppercase tracking-wide text-gray-500 dark:border-white/15">
              {status} — {rows.length}
            </h2>

            {rows.map((application) => (
              <div
                key={application.id}
                className="flex items-center justify-between gap-4 rounded-lg px-3 py-2.5 hover:bg-black/5 dark:hover:bg-white/10"
              >
                <Link href={`/jobs/${application.job.id}`} className="min-w-0">
                  <div className="font-medium">{application.job.title}</div>
                  <div className="truncate text-sm text-gray-500">
                    {application.job.company} · {application.job.location} ·{" "}
                    {application.job.salary_usd !== null
                      ? `$${application.job.salary_usd.toLocaleString()}`
                      : "salary not listed"}
                  </div>
                </Link>

                <ApplicationControls
                  applicationId={application.id}
                  status={application.status}
                />
              </div>
            ))}
          </section>
        );
      })}
    </main>
  );
}
