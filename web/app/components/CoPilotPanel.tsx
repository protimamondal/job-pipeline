// Layout shell only — no useChat, no transport, no MCP.
// The working chat gets wired in here at task 6.

'use client'

import { useState, type FormEvent } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { searchJobInput2, serachResultObject2 } from "../lib/data/types";

export default function CoPilotPanel() {
  const [input,setInput] = useState("");

  const {
    messages,
    sendMessage,
    status,
    error,
    stop
  } = useChat({
    transport : new DefaultChatTransport({
      api : "/api/chat"
    })
  })

function handleSubmit(e : FormEvent){
    e.preventDefault();
    if(!input.trim()) return;

  sendMessage({
    text: input,
  })

  setInput("")
}

  return (
    <aside className="sticky top-0 flex h-screen w-80 shrink-0 flex-col border-l border-black/10 dark:border-white/15">
      <header className="border-b border-black/10 px-4 py-3 dark:border-white/15">
        <h2 className="text-sm font-semibold">Copilot</h2>
        <p className="text-xs text-gray-500">Ask about jobs</p>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
      {messages.length > 0 && messages.map(message=>(
      <div key={message.id}>
        <div>{message.role==="user" ? "you":message.role}</div>
        {message.parts.map((part,index)=>{
          if(part.type==="text"){
            return <p key={index}>{part.text}</p>
          }
          if(part.type==="dynamic-tool" && 
            part.toolName==="search_job")
          {
            switch(part.state){
              case "input-streaming" :
                return(
                  <div key={part.toolCallId}>preparing...</div>
                )
              case "input-available" : {
              const inputStream = part.input as searchJobInput2;
              return(
                <div key={part.toolCallId}>searching for {inputStream.title} in {inputStream.location}</div>
              )
              }
              case "output-available" : {
                const output = part.output as serachResultObject2;
                const toolJobs = output.structuredContent.result;
                         return(
                  <div key={part.toolCallId}>
                    {toolJobs.map((outpt,ind)=>(
                      <div key={ind}
                      className="border border-gray-600 rounded-xl p-2 mb-2"
                      >{outpt.company} job for {outpt.title} in {outpt.location} {outpt.salary ? `for salary of $${outpt.salary}` : "salary not mentioned" }</div>
                    ))}
                  </div>
                )
              }
              case "output-error" : {
                return(
                  <div key={part.toolCallId} className="text-red-500">{part.errorText}</div>
                )
              }
            }
          }
        })}
      </div>
))}
      </div>

   {status==="submitted" && <div className="mx-auto w-full max-w-2xl px-4 py-3 text-sm text-gray-500">Thinking...</div>}
   {error && <div className="mx-auto w-full max-w-2xl px-4 py-3  text-red-700">Some problem occured</div>}

      <form onSubmit={handleSubmit} className="shrink-0 border-t border-black/10 p-3 dark:border-white/15">
        <div className="flex gap-2">
          <input
            type="text"
            value={input} onChange={(e)=>{setInput(e.target.value)}}
            placeholder="Ask something..."
            className="w-full min-w-0 rounded-full border border-black/15 px-3 py-2 text-sm outline-none focus:border-black/40 dark:border-white/20 dark:focus:border-white/40"
          />
    {status === "submitted" || status === "streaming" ? (
      <button type="button" onClick={stop} className="rounded-full border border-black/15 px-6 py-3 hover:bg-black/5 dark:border-white/20 dark:hover:bg-white/10">stop</button>
    ) : (
      <button type="submit" className="rounded-full bg-foreground px-6 py-3 text-background hover:opacity-80">send</button>
    )}
        </div>
      </form>
    </aside>
  );
}
