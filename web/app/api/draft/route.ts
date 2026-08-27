import { jobs } from "@/app/lib/data/jobs";
import { profile } from "@/app/lib/data/profile";
import { openai } from "@ai-sdk/openai";
import { createTextStreamResponse, streamText, toTextStream } from "ai";

export async function POST(req: Request) {
  const { id,prompt } = await req.json();

  const job = jobs.find((job) => job.id === id);
  if (!job) {
    return new Response(`No job with id ${id}`, { status: 404 });
  }

  const result = streamText({
    model: openai("gpt-4.1-mini"),
    prompt: `consider yourself as the job applicant and create a cover letter
             using the job title ${job.title} whose description is
             ${job.description} and this is my profile ${profile}

             Return the cover letter itself.
             You may use markdown formatting like **bold**.
             Do not wrap the answer in triple backticks.
             Do not use a markdown code block.
             Do not start with \`\`\`markdown.
             Use 2-3 short paragraphs and bold one important skill match.

             ${prompt ? `Extra user instruction: ${prompt}` : ""}`,
  });

  return createTextStreamResponse({
    stream: toTextStream({
      stream: result.stream,
    }),
  });
}
