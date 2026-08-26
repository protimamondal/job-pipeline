import { createTextStreamResponse } from "ai";

const text = `## Application for the Senior Frontend Engineer role

Dear hiring team,

I am **very keen** on this position. Three things line up directly:

- I led a [design system](https://example.com) adopted by six product teams
- I rebuilt a checkout flow as a streaming, optimistic UI
- I care about \`perceived performance\` more than benchmark numbers

\`\`\`ts
const timeToFirstToken = "the only wait the user cannot see progress during";
\`\`\`

Sincerely,
Protima`;

export async function POST() {
  const stream = new ReadableStream<string>({
    async start(controller) {
      for (const ch of text) {
        controller.enqueue(ch);
        await new Promise((r) => setTimeout(r, 200));
      }
      controller.close();
    },
  });

  return createTextStreamResponse({ stream });
}