import type { ReviewRequest, ReviewResponse } from "./types";

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

export async function reviewCode(req: ReviewRequest): Promise<ReviewResponse> {
  const res = await fetch(`${BASE_URL}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const detail = await res
      .json()
      .then((d: { detail?: string }) => d.detail ?? res.statusText)
      .catch(() => res.statusText);
    throw new Error(detail);
  }

  return res.json() as Promise<ReviewResponse>;
}
