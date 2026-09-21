import type { Job, JobStatus } from "./jobs";

export type Application = {
  id: number;
  job: Job;
  status: JobStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type applicationsByStatus = Record<JobStatus, Application[]>;
