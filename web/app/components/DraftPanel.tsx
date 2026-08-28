// STEP 2 — the draft pane.
//
// Streams a cover letter for one job and renders it as markdown while it
// arrives. The markdown repair lives in app/lib/markdown/renderable.ts.
//
// FAKE points the hook at a fixed, slow, character-by-character stream —
// the only reliable way to watch the half-arrived markers. Step 5 reuses it.

"use client";

import { useState } from "react";
import { useCompletion } from "@ai-sdk/react";
import { Streamdown } from "streamdown";
import "streamdown/styles.css";
import { trimOpenMarker } from "@/app/lib/markdown/renderable";

const FAKE = false;
const STREAM_ERROR_MARKER = "[[error:stream_failed]]";

function parseDraftStream(text: string) {
  const markerIndex = text.indexOf(STREAM_ERROR_MARKER);

  if (markerIndex === -1) {
    return {
      visibleText: text,
      streamFailed: false,
    };
  }

  return {
    visibleText: text.slice(0, markerIndex),
    streamFailed: true,
  };
}

  function renderCitations(text: string) {
    return text
      .replaceAll("[[job]]", " [job](#source-job)")
      .replaceAll("[[profile]]", " [profile](#source-profile)");
  }

export default function DraftPanel({ id }: { id: string }) {

  const [instruction, setInstruction] = useState("");
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState("");
  const [selectedSource, setSelectedSource] = useState<"job" | "profile" | null>(null);


  const [edited, setEdited] = useState(false);

  const { completion, complete, error, setCompletion, isLoading, stop } = useCompletion({
    api: FAKE ? "/api/draft/fake" : "/api/draft",
    streamProtocol: "text",
    body: { id },
  });
  const parsedDraft = parseDraftStream(completion);

  // Two ways a draft can stop early, and they arrive differently.
  // The marker is the server telling us generation failed — it could still
  // talk to us. If the connection itself broke there is no way to send the
  // marker at all, and all we get is `error` plus whatever text had already
  // landed. Both mean the same thing to the reader.
  const stoppedEarly = parsedDraft.streamFailed || (!!error && !!completion);
   const visibleDraft = renderCitations(parsedDraft.visibleText);

  function handleDraft() {
    setIsEditing(false);
    setEditedText("");
    setEdited(false);
    setSelectedSource(null);
    complete("");
  }

  function handleRegenerate() {
    setIsEditing(false);
    setEditedText("");
    setEdited(false);
    setSelectedSource(null);
    complete(instruction);
  }

  async function handleCopy(){
    const textToCopy = isEditing ? editedText : visibleDraft;
    await navigator.clipboard.writeText(textToCopy);
    setCopied(true)
    setTimeout(()=>{
      setCopied(false)
    },2000)
  }


  function handleEdit(){
    setEditedText(visibleDraft)
    setIsEditing(true);
  }

  // Saving writes the user's text into the hook's own state, so there stays
  // exactly one copy of the letter. Copy, and later the citations, read
  // `completion` and do not have to ask which version is the real one.
  function handleSave(){
    setCompletion(editedText);
    setEdited(true);
    setIsEditing(false);
  }

  function handleCancel(){
    setEditedText("");
    setIsEditing(false);
  }

  return (
    <section className="mt-10 border-t border-black/10 pt-6 dark:border-white/15">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-xs uppercase tracking-wide text-gray-500">
          Cover letter
        </h2>

        <div className="flex gap-2">
          <button
            type="button"
            disabled={isLoading}
            className="rounded-full bg-foreground px-4 py-2 text-sm text-background hover:opacity-80 disabled:cursor-not-allowed disabled:opacity-40"
            onClick={handleDraft}
          >
            Draft application
          </button>

          <button
            type="button"
            disabled={!isLoading}
            className="rounded-full border border-black/15 px-4 py-2 text-sm hover:bg-black/5 disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/20 dark:hover:bg-white/10"
            onClick={stop}
          >
            Stop
          </button>
        </div>
      </div>

      {/* STEP 3 — the instruction. Nothing is wired: the value becomes state,
          and Regenerate passes it to complete(). */}
      <div className="mt-4 flex gap-2">
        <input
          type="text"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          placeholder="Add an instruction — e.g. make it shorter, mention the design system"
          className="w-full min-w-0 rounded-full border border-black/15 px-4 py-2 text-sm outline-none focus:border-black/40 dark:border-white/20 dark:focus:border-white/40"
        />
        <button
          type="button"
          disabled={isLoading || !completion}
          onClick={handleRegenerate}
          className="shrink-0 rounded-full border border-black/15 px-4 py-2 text-sm hover:bg-black/5 disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/20 dark:hover:bg-white/10"
        >
          Regenerate
        </button>
      </div>

      <article
        className={`mt-4 rounded-lg border border-black/10 px-5 py-4 dark:border-white/15 ${
          isEditing ? "draft-editing" : ""
        }`}
      >
      {isEditing ? (
    <textarea
      value={editedText}
      onChange={(e) => setEditedText(e.target.value)}
      className="draft-editor"
    />
  ) : (
    <div className="draft-prose">
      {isLoading && !completion && <p>Preparing draft…</p>}
      <Streamdown
        isAnimating={isLoading}
        components={{
          a({ href, children }) {
            if (href === "#source-job") {
              return (
                <button
                  type="button"
                  onClick={() => setSelectedSource("job")}
                  className="mx-0.5 inline-flex rounded-full border border-black/15 px-1.5 py-0.5 text-[0.7rem] font-medium no-underline hover:bg-black/5 dark:border-white/20 dark:hover:bg-white/10"
                >
                  {children}
                </button>
              );
            }

            if (href === "#source-profile") {
              return (
                <button
                  type="button"
                  onClick={() => setSelectedSource("profile")}
                  className="mx-0.5 inline-flex rounded-full border border-black/15 px-1.5 py-0.5 text-[0.7rem] font-medium no-underline hover:bg-black/5 dark:border-white/20 dark:hover:bg-white/10"
                >
                  {children}
                </button>
              );
            }

            return <a href={href}>{children}</a>;
          },
        }}
      >
        {trimOpenMarker(visibleDraft, isLoading)}
      </Streamdown>
      {completion && (
        <div className="mt-4 grid gap-2 border-t border-black/10 pt-3 text-xs dark:border-white/15">
          <p className="text-gray-500">Sources used by the draft</p>
          <div
            id="source-job"
            className={`rounded-md border p-2 ${
              selectedSource === "job"
                ? "border-yellow-400 bg-yellow-50 ring-2 ring-yellow-300 dark:border-yellow-400/70 dark:bg-yellow-500/10"
                : "border-black/10 dark:border-white/15"
            }`}
          >
            <strong>[job]</strong> selected job description
          </div>

          <div
            id="source-profile"
            className={`rounded-md border p-2 ${
              selectedSource === "profile"
                ? "border-yellow-400 bg-yellow-50 ring-2 ring-yellow-300 dark:border-yellow-400/70 dark:bg-yellow-500/10"
                : "border-black/10 dark:border-white/15"
            }`}
          >
            <strong>[profile]</strong> candidate profile
          </div>
        </div>
      )}
      {stoppedEarly && !isLoading && (
        <div className="mt-4 rounded-lg border border-yellow-500/40 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-900 dark:text-yellow-200">
          <p>The draft stopped before finishing. The text above is incomplete.</p>
          <button
            type="button"
            onClick={handleRegenerate}
            className="mt-2 rounded-full border border-yellow-600/40 px-3 py-1.5 text-xs hover:bg-yellow-500/10"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  )}
  {error && !isLoading && !completion && (
  <div className="mt-4 flex items-center justify-between gap-4 rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3 text-sm">
    <span className="text-red-700 dark:text-red-400">
      The draft could not be started.
    </span>
    <button
      type="button"
      onClick={() => complete(instruction)}
      className="shrink-0 rounded-full border border-red-500/40 px-3 py-1.5 text-xs"
    >
      Retry
    </button>
  </div>
)}

        {/* STEP 3 — the affordances. Copy says "Copied" for about two seconds
            and is disabled while text is still arriving. Editing replaces the
            whole row: Copy and Edit make no sense while the pane is a
            textarea. */}
        <div className="mt-4 flex items-center gap-2 border-t border-black/10 pt-3 dark:border-white/15">
          {isEditing ? (
            <>
              <button
                type="button"
                disabled={editedText === completion}
                onClick={handleSave}
                className="rounded-full bg-foreground px-3 py-1.5 text-xs text-background hover:opacity-80 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Save
              </button>
              <button
                type="button"
                onClick={handleCancel}
                className="rounded-full border border-black/10 px-3 py-1.5 text-xs hover:bg-black/5 dark:border-white/15 dark:hover:bg-white/10"
              >
                Cancel
              </button>
            </>
          ) : (
            <>
          <button
            type="button"
             disabled={isLoading || !completion}
            onClick={handleCopy}
            className="rounded-full border border-black/10 px-3 py-1.5 text-xs hover:bg-black/5 disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/15 dark:hover:bg-white/10"
          >
            {copied ? 'Copied' : 'Copy'}
          </button>
          <button
            type="button"
            disabled={isLoading || !completion}
            onClick={handleEdit}
            className="rounded-full border border-black/10 px-3 py-1.5 text-xs hover:bg-black/5 disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/15 dark:hover:bg-white/10"
          >
            Edit
          </button>
            </>
          )}

          {edited && !isEditing && (
            <span className="ml-auto text-xs text-gray-500">Edited</span>
          )}
        </div>
      </article>
    </section>
  );
}
