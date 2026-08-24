export type JobStatus = "saved" | "applied" | "interviewing" | "rejected";

export type Job = {
  // the locked flagship contract
  company: string;
  title: string;
  location: string;
  salary_usd: number | null;
  url: string | null;
  // added for this phase
  id: string;
  description: string;
  status: JobStatus;
};

export type jobsByStatus = Record<JobStatus,Job[]>



export const jobs: Job[] = [
  {
    id: "1",
    company: "Northwind Labs",
    title: "Senior Frontend Engineer",
    location: "Bengaluru",
    salary_usd: 128000,
    url: null,
    status: "interviewing",
    description: `We are hiring a senior frontend engineer to own our customer-facing dashboard end to end.

You will lead the migration of a large React codebase to the App Router, and set the patterns the rest of the team follows.

We care a lot about perceived performance — streaming, optimistic updates, and honest loading states. If a request takes four seconds, the screen should say so in a way that feels considered rather than broken.

You will work directly with two backend engineers and a designer. No layers in between.

Experience mentoring engineers and running design reviews is strongly preferred.`,
  },
  {
    id: "2",
    company: "Cobalt Health",
    title: "Staff Engineer, Web Platform",
    location: "Remote (India)",
    salary_usd: 165000,
    url: null,
    status: "interviewing",
    description: `Cobalt Health builds scheduling and records software used by around four hundred clinics.

This role owns the web platform: the design system, the build pipeline, and the shared component library that six product teams depend on. You are not shipping features week to week — you are making it possible for other people to ship them safely.

Concretely, in the first six months we would expect you to take our component library from something maintained on the side to something with a real release process, versioning, and documentation people actually read.

We have a large amount of older React that predates hooks. Part of this job is deciding what gets migrated, what gets replaced, and what is left alone on purpose.

Accessibility is a regulatory requirement for us, not a nice-to-have. You should be comfortable with keyboard navigation, focus management, and screen-reader behaviour, or willing to become comfortable quickly.

We are fully remote and asynchronous. Strong written communication matters more here than it would elsewhere.`,
  },
  {
    id: "3",
    company: "Farrow & Vine",
    title: "Frontend Engineer, AI Products",
    location: "Pune",
    salary_usd: null,
    url: null,
    status: "applied",
    description: `We are a small product studio building AI features inside other companies' products, and we are looking for a frontend engineer who thinks the interface is the hard part.

Most of our work is the same shape: a model produces something slowly and imperfectly, and a person has to be able to trust it, correct it, and move on. Streaming text, partial failures, citations back to source material, edit-and-retry flows. If you have opinions about what a good loading state looks like when the wait is fifteen seconds, we want to talk to you.

You would work in TypeScript and React across three or four client codebases a year. Some are modern; some are not.

We do not expect machine learning experience. We expect you to be unusually good at building interfaces for things that are uncertain.

Salary is negotiated per person and depends heavily on experience, so we have not listed a band.`,
  },
  {
    id: "4",
    company: "Meridian Freight",
    title: "Senior Engineer, Internal Tools",
    location: "Bengaluru",
    salary_usd: 112000,
    url: null,
    status: "applied",
    description: `Meridian moves shipping containers. This role builds the software our operations team uses to do that.

The users are forty people in one building who use your software for eight hours a day and will tell you immediately when it is bad. That feedback loop is the best part of the job.

You will be working on a dispatch console: a lot of dense tables, a lot of real-time state, a lot of keyboard shortcuts. It is not glamorous and it is genuinely interesting.

We are a Rails shop moving the frontend to React incrementally. You would be the third frontend engineer.`,
  },
  {
    id: "5",
    company: "Tessellate",
    title: "Product Engineer",
    location: "Remote",
    salary_usd: 96000,
    url: null,
    status: "saved",
    description: `Small team, early product, broad role. You would write frontend most days and backend when it is in the way.

We are looking for someone who is comfortable making product decisions rather than waiting for a specification.`,
  },
  {
    id: "6",
    company: "Halden Systems",
    title: "Senior React Engineer",
    location: "Hyderabad",
    salary_usd: 134000,
    url: null,
    status: "saved",
    description: `Enterprise data visualisation. Large tables, large charts, customers who care about export fidelity.

The work is performance-heavy: rendering tens of thousands of rows without the interface stuttering.`,
  },
  {
    id: "7",
    company: "Junco",
    title: "Frontend Lead",
    location: "Mumbai",
    salary_usd: 145000,
    url: null,
    status: "rejected",
    description: `Leading a team of four on a consumer marketplace app.

Half the role is people management and roadmap; half is still writing code.`,
  },
];
