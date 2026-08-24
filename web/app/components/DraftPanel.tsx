// STEP 2 — the draft pane. STYLING SHELL ONLY.
//
// There is no useCompletion here, no /api/draft, no markdown renderer. What is
// here is the layout, the three visual states, and the CSS classes the streamed
// markdown will land in (.draft-prose and .streaming-caret, both in globals.css).
//
// The three flags below stand in for the hook. Flip them by hand to see each
// state, then delete them and read the real values off useCompletion.

"use client";

const hasDraft = true; // → completion.length > 0
const isStreaming = false; // → isLoading  (blinking caret + disabled button)
const failed = false; // → error

export default function DraftPanel({ jobId }: { jobId: string }) {
  // jobId is what the /api/draft POST body will carry. Unused until then.
  void jobId;

  return (
    <section className="mt-10 border-t border-black/10 pt-6 dark:border-white/15">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-xs uppercase tracking-wide text-gray-500">
          Cover letter
        </h2>

        <button
          type="button"
          disabled={isStreaming}
          className="rounded-full bg-foreground px-4 py-2 text-sm text-background hover:opacity-80 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isStreaming ? "Drafting…" : "Draft application"}
        </button>
      </div>

      {/* state 1 — nothing asked for yet */}
      {!hasDraft && !isStreaming && !failed && (
        <p className="mt-4 rounded-lg border border-dashed border-black/15 px-4 py-8 text-center text-sm text-gray-500 dark:border-white/20">
          No draft yet. Press{" "}
          <span className="font-medium">Draft application</span> and the letter
          is written from this job description.
        </p>
      )}

      {/* state 2 — the letter. Replace the static markup inside .draft-prose
          with the markdown renderer; the wrapper classes stay exactly as they
          are. The caret is a sibling of the text, not part of it. */}
      {(hasDraft || isStreaming) && (
        <article className="mt-4 rounded-lg border border-black/10 px-5 py-4 dark:border-white/15">
          <div className="draft-prose">
            <h3>Dear hiring team at Northwind Labs,</h3>
            <p>
              I am writing about the <strong>Senior Frontend Engineer</strong>{" "}
              role. Your description says you care about{" "}
              <em>perceived performance</em> — streaming, optimistic updates,
              honest loading states. That is the work I have spent the last year
              doing.
            </p>
            <p>Three things from my side that line up directly:</p>
            <ul>
              <li>
                Rebuilt a checkout flow as a streaming, optimistic UI and cut
                perceived load time by half.
              </li>
              <li>
                Led a design system of 40+ components adopted by six product
                teams.
              </li>
              <li>Migrated a large React codebase, incrementally, in public.</li>
            </ul>
            <blockquote>
              Static placeholder text. Every tag in here is styled by
              .draft-prose, not by a Tailwind class.
            </blockquote>
          </div>

          {isStreaming && <span className="streaming-caret" aria-hidden />}

          <div className="mt-4 h-px bg-black/10 dark:bg-white/15" />

          {/* step 3 hangs copy / regenerate / edit off this row */}
          <div className="mt-3 flex items-center gap-2 text-xs text-gray-500">
            {isStreaming ? "Writing…" : "Draft ready"}
          </div>
        </article>
      )}

      {/* state 3 — it broke. Step 5 splits this into three different failures;
          for now it is one box with room for a Retry button. */}
      {failed && (
        <div className="mt-4 flex items-center justify-between gap-4 rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3 text-sm">
          <span className="text-red-700 dark:text-red-400">
            The draft could not be written.
          </span>
          <button
            type="button"
            className="shrink-0 rounded-full border border-red-500/40 px-3 py-1.5 text-xs text-red-700 hover:bg-red-500/10 dark:text-red-400"
          >
            Retry
          </button>
        </div>
      )}
    </section>
  );
}
