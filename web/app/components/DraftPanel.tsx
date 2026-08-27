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

export default function DraftPanel({ id }: { id: string }) {

  const [instruction, setInstruction] = useState("");
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState("");


  const [edited, setEdited] = useState(false);

  const { completion, complete, setCompletion, isLoading, stop } = useCompletion({
    api: FAKE ? "/api/draft/fake" : "/api/draft",
    streamProtocol: "text",
    body: { id },
  });

   function handleDraft() {
    setIsEditing(false);
    setEditedText("");
    setEdited(false);
    complete("");
  }

  function handleRegenerate() {
    setIsEditing(false);
    setEditedText("");
    setEdited(false);
    complete(instruction);
  }

  async function handleCopy(){
    const textToCopy = isEditing ? editedText : completion;
    await navigator.clipboard.writeText(textToCopy);
    setCopied(true)
    setTimeout(()=>{
      setCopied(false)
    },2000)
  }

  function handleEdit(){
    setEditedText(completion)
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
      <Streamdown isAnimating={isLoading}>
        {trimOpenMarker(completion, isLoading)}
      </Streamdown>
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
