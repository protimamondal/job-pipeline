// STEP 2 — the draft pane. CSS SKELETON ONLY.
//
// Structure and classes, nothing else. No hook, no route, no renderer, no
// placeholder copy. The two classes that matter are in globals.css:
//   .draft-prose      styles the tags a markdown renderer emits
//   .streaming-caret  the blinking block for "still arriving" (not used yet)

"use client";

export default function DraftPanel() {
  return (
    <section className="mt-10 border-t border-black/10 pt-6 dark:border-white/15">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-xs uppercase tracking-wide text-gray-500">
          Cover letter
        </h2>

        <button
          type="button"
          className="rounded-full bg-foreground px-4 py-2 text-sm text-background hover:opacity-80 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Draft application
        </button>
      </div>

      <article className="mt-4 rounded-lg border border-black/10 px-5 py-4 dark:border-white/15">
        <div className="draft-prose">{/* the letter renders here */}</div>
      </article>
    </section>
  );
}
