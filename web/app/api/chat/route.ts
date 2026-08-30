// Placeholder. Task 6 brings the real route over from aisdk-ground-up
// (createMCPClient + streamText). Empty files are not modules, and the

import { createMCPClient } from "@ai-sdk/mcp";
import { openai } from "@ai-sdk/openai";
import { convertToModelMessages, createUIMessageStreamResponse, stepCountIs, streamText, toUIMessageStream, UIMessage } from "ai";

// build fails on them, so this keeps the route valid until then.

export async function POST(req : Request){

    const {messages} : {messages : UIMessage[]} = await req.json();
    const mcpServerUrl = process.env.MCP_SERVER_URL ?? "http://127.0.0.1:8001/mcp";

const mcpClient = await createMCPClient({
    transport : {
        type : "http",
        url : mcpServerUrl
    }
})

const tools = await mcpClient.tools();
const result = streamText({
    model : openai("gpt-4.1-mini"),
    messages : await convertToModelMessages(messages),
    tools,
    stopWhen: stepCountIs(5),
    onFinish : async ()=>{
        mcpClient.close()
    },
    onError : async()=>{
        mcpClient.close()
    }
})

    return createUIMessageStreamResponse({
        stream : toUIMessageStream({
            stream : result.stream,
        })
})
}
