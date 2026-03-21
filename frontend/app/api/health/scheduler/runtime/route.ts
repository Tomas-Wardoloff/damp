import { NextResponse } from "next/server";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function fetchUpstreamWithRetry(input: string): Promise<Response> {
  let lastError: unknown;

  for (let attempt = 0; attempt < 2; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 12000);

    try {
      return await fetch(input, {
        cache: "no-store",
        signal: controller.signal,
      });
    } catch (error) {
      lastError = error;
      if (attempt === 1) {
        throw error;
      }
    } finally {
      clearTimeout(timeoutId);
    }
  }

  throw lastError instanceof Error ? lastError : new Error("Upstream request failed");
}

export async function GET() {
  try {
    const upstream = await fetchUpstreamWithRetry(`${API_BASE_URL}/health/scheduler/runtime`);

    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("Content-Type") || "application/json" },
    });
  } catch (error) {
    return NextResponse.json(
      { detail: "Scheduler upstream unavailable", error: String(error) },
      { status: 502 },
    );
  }
}
