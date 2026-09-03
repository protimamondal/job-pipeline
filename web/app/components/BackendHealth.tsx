"use client";

import { useEffect, useState } from "react";

import { backendBaseUrl } from "../lib/backend";

type HealthStatus = "checking" | "ok" | "error";

export default function BackendHealth() {
  const [status, setStatus] = useState<HealthStatus>("checking");

  useEffect(() => {
    async function checkHealth() {
      try {
        const response = await fetch(`${backendBaseUrl}/health`);

        if (!response.ok) {
          throw new Error("Health check failed");
        }

        setStatus("ok");
      } catch {
        setStatus("error");
      }
    }

    void checkHealth();
  }, []);

  return <div className="mb-4 text-xs text-gray-500">Backend: {status}</div>;
}
