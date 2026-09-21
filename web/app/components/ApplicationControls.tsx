"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { JobStatus } from "@/app/lib/data/jobs";

const STATUSES: JobStatus[] = ["saved", "applied", "interviewing", "rejected"];

type Props = {
  applicationId: number;
  status: JobStatus;
};

export default function ApplicationControls({ applicationId, status }: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function changeStatus(next: JobStatus) {
    setBusy(true);
    try {
      await fetch(`/api/applications/${applicationId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: next }),
      });
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      await fetch(`/api/applications/${applicationId}`, { method: "DELETE" });
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <label className="sr-only" htmlFor={`status-${applicationId}`}>
        Status
      </label>
      <select
        id={`status-${applicationId}`}
        value={status}
        disabled={busy}
        onChange={(event) => changeStatus(event.target.value as JobStatus)}
        className="rounded-lg border border-black/15 bg-transparent px-2 py-1 text-xs disabled:opacity-50 dark:border-white/20"
      >
        {STATUSES.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>

      <button
        type="button"
        onClick={remove}
        disabled={busy}
        className="rounded-lg px-2 py-1 text-xs text-gray-500 hover:bg-black/5 disabled:opacity-50 dark:hover:bg-white/10"
      >
        Remove
      </button>
    </div>
  );
}
