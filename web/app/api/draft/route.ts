import { jobs } from "@/app/lib/data/jobs";
import { profile } from "@/app/lib/data/profile";
import { openai } from "@ai-sdk/openai";
import { createTextStreamResponse, streamText, toTextStream } from "ai";

export async function POST(req: Request) {
  const { id } = await req.json();

  const job = jobs.find((job) => job.id === id);
  if (!job) {
    return new Response(`No job with id ${id}`, { status: 404 });
  }

  const result = streamText({
    model: openai("gpt-4.1-mini"),
    prompt: `consider yourself as the job applicant and create a cover letter
             using the job title ${job.title} whose description is
             ${job.description} and this is my profile ${profile}
             Return markdown. Use 2-3 short paragraphs and bold one important
             skill match. Do not use headings, links or code blocks.`,
  });

  return createTextStreamResponse({
    stream: toTextStream({
      stream: result.stream,
    }),
  });
}
