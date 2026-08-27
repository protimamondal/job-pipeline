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


  const { completion, complete, isLoading, stop } = useCompletion({
    api: FAKE ? "/api/draft/fake" : "/api/draft",
    streamProtocol: "text",
    body: { id },
  });

   function handleDraft() {
    setIsEditing(false);
    setEditedText("");
    complete("");
  }

  function handleRegenerate() {
    setIsEditing(false);
    setEditedText("");
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

      {/* STEP 4 — the version strip. One chip per draft, in creation order:

            <button
              className={`version-chip ${draft.edited ? "version-chip--edited" : ""}`}
              aria-current={draft.id === currentDraftId}
              onClick={() => switchTo(draft)}
            >
              v{n}
            </button>

          Add version-chip--branch to a chip whose parentId is not the draft
          before it, so a branch does not read as a straight line. */}
      <div className="version-strip mt-4" />

      {/* Add .draft-editing to this article while the letter is editable. */}
      <article className="mt-4 rounded-lg border border-black/10 px-5 py-4 dark:border-white/15">
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

        {/* Swaps in where the rendered letter is, once editing starts:
            <textarea className="draft-editor" ... />
            Same metrics as .draft-prose, so nothing moves. */}

        {/* STEP 3 — the affordances. Copy says "Copied" for about two seconds
            and is disabled while text is still arriving. */}
        <div className="mt-4 flex items-center gap-2 border-t border-black/10 pt-3 dark:border-white/15">
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
        </div>
      </article>
    </section>
  );
}
