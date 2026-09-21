export type JobStatus = "saved" | "applied" | "interviewing" | "rejected";

export type Job = {
  // the locked flagship contract
  company: string;
  title: string;
  location: string;
  salary_usd: number | null;
  url: string | null;
  // added for this phase
  id: number;
  description: string;
};

export type jobsByStatus = Record<JobStatus, Job[]>;
