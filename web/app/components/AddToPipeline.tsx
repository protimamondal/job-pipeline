"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

type Props = {
  jobId: number;
  /** True when this job is already in the pipeline. */
  tracked: boolean;
};

export default function AddToPipeline({ jobId, tracked }: Props) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleClick() {
    setError(null);
    setSubmitting(true);

    try {
      const response = await fetch("/api/applications", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId }),
      });

      if (!response.ok) {
        throw new Error("Could not add this job to your pipeline.");
      }

      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Something broke.");
    } finally {
      setSubmitting(false);
    }
  }

  if (tracked) {
    return (
      <p className="mt-4 text-sm text-gray-500">
        Already in your pipeline.
      </p>
    );
  }

  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={handleClick}
        disabled={submitting}
        className="rounded-lg bg-black px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-black"
      >
        {submitting ? "Adding…" : "Add to pipeline"}
      </button>

      {error !== null && (
        <p role="alert" className="mt-2 text-sm text-red-700 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}
