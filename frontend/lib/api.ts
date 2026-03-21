import { type Animal } from "@/components/animal/AnimalCard";
import { HealthAnalysisResponse } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function fetchWithRetry(
  input: string,
  init: RequestInit = {},
  timeoutMs = 12000,
): Promise<Response> {
  let lastError: unknown;

  for (let attempt = 0; attempt < 2; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      return await fetch(input, {
        ...init,
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

  throw lastError instanceof Error ? lastError : new Error("Fetch failed");
}

function pickEffectivePrediction(
  health: Record<string, unknown> | null | undefined,
): {
  status: string | null;
  confidence: number | null;
  primary: { status: string | null; confidence: number | null };
  secondary: { status: string | null; confidence: number | null };
} {
  const primaryStatus =
    typeof health?.primary_status === "string"
      ? health.primary_status
      : typeof health?.status === "string"
        ? health.status
        : null;

  const primaryConfidence =
    typeof health?.primary_confidence === "number"
      ? health.primary_confidence
      : typeof health?.confidence === "number"
        ? health.confidence
        : null;

  const secondaryStatus =
    typeof health?.secondary_status === "string"
      ? health.secondary_status
      : null;
  const secondaryConfidence =
    typeof health?.secondary_confidence === "number"
      ? health.secondary_confidence
      : null;

  let effectiveStatus = primaryStatus;
  let effectiveConfidence = primaryConfidence;

  if (
    secondaryStatus &&
    secondaryConfidence !== null &&
    (primaryConfidence === null || secondaryConfidence > primaryConfidence)
  ) {
    effectiveStatus = secondaryStatus;
    effectiveConfidence = secondaryConfidence;
  }

  return {
    status: effectiveStatus,
    confidence: effectiveConfidence,
    primary: { status: primaryStatus, confidence: primaryConfidence },
    secondary: { status: secondaryStatus, confidence: secondaryConfidence },
  };
}

function toFrontendStatus(status: string | null): string {
  if (!status) return "sin datos";

  return status.toLowerCase();
}

function normalizeCowStatus(status: string | undefined): string {
  if (!status) return "SANA";
  return status;
}

function isNotFutureDate(value: unknown): boolean {
  if (typeof value !== "string") return false;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) && parsed <= Date.now();
}

/* eslint-disable @typescript-eslint/no-explicit-any */
export async function getCows(): Promise<any[]> {
  try {
    const res = await fetchWithRetry(`${API_BASE_URL}/cows`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch cows:", err);
    return [];
  }
}

export async function getLatestReading(cowId: number): Promise<any | null> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/cows/${cowId}/readings?page=1&size=1`,
      {
        cache: "no-store",
      },
    );
    if (!res.ok) return null;

    const data = await res.json();
    const latest = data?.items && data.items.length > 0 ? data.items[0] : null;
    if (!latest) return null;
    return isNotFutureDate(latest.timestamp) ? latest : null;
  } catch (err) {
    console.error(`Failed to fetch reading for cow ${cowId}:`, err);
    return null;
  }
}

export async function getHealthStatus(cowId: number): Promise<any | null> {
  try {
    const res = await fetchWithRetry(`${API_BASE_URL}/health/status/${cowId}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    const health = await res.json();
    if (!health?.created_at) return health;
    return isNotFutureDate(health.created_at) ? health : null;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      return null;
    }
    console.error(`Failed to fetch health status for cow ${cowId}:`, err);
    return null;
  }
}

export async function getHealthHistory(
  cowId: number,
): Promise<HealthAnalysisResponse[]> {
  try {
    const res = await fetchWithRetry(
      `${API_BASE_URL}/health/history/${cowId}`,
      {
        cache: "no-store",
      },
    );
    if (!res.ok) return [];
    const history = await res.json();
    if (!Array.isArray(history)) return [];
    return history.filter((item) => isNotFutureDate(item?.created_at));
  } catch (err) {
    console.error(`Failed to fetch health history for cow ${cowId}:`, err);
    return [];
  }
}

export async function getClinicalHistory(days = 7): Promise<{
  days: number;
  from_date: string;
  to_date: string;
  cows: Array<{
    cow_id: number;
    total_points: number;
    transitions: number;
    stable: boolean;
    latest_status: string;
    points: Array<{
      created_at: string;
      status: string;
      confidence: number | null;
      primary_status: string | null;
      primary_confidence: number | null;
      secondary_status: string | null;
      secondary_confidence: number | null;
    }>;
  }>;
} | null> {
  try {
    const safeDays = Number.isFinite(days) ? Math.max(1, Math.min(30, Math.floor(days))) : 7;
    const res = await fetchWithRetry(
      `${API_BASE_URL}/health/clinical-history?days=${safeDays}`,
      {
        cache: "no-store",
      },
    );
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch clinical history:", err);
    return null;
  }
}

export async function getLatestHealthByHistory(
  cowId: number,
): Promise<any | null> {
  try {
    // /health/status is now read-only and returns latest analysis directly.
    return await getHealthStatus(cowId);
  } catch (err) {
    console.error(
      `Failed to fetch latest health by history for cow ${cowId}:`,
      err,
    );
    return null;
  }
}

export async function getLatestReadings(): Promise<any[]> {
  try {
    const res = await fetchWithRetry(`${API_BASE_URL}/readings/latests`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    const readings = await res.json();
    if (!Array.isArray(readings)) return [];
    return readings.filter((reading) => isNotFutureDate(reading?.timestamp));
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      return [];
    }
    console.error("Failed to fetch latest readings:", err);
    return [];
  }
}

export async function getHealthSchedulerConfig(): Promise<any | null> {
  try {
    const res = await fetch(`/api/health/scheduler/config`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch scheduler config:", err);
    return null;
  }
}

export async function updateHealthSchedulerConfig(payload: {
  enabled: boolean;
  cycle_minutes: number;
}): Promise<any | null> {
  try {
    const res = await fetch(`/api/health/scheduler/config`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error("Failed to update scheduler config:", err);
    return null;
  }
}

export async function getHealthSchedulerRuntime(): Promise<any | null> {
  try {
    const res = await fetch(`/api/health/scheduler/runtime`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch scheduler runtime:", err);
    return null;
  }
}

export async function fetchDashboardData(): Promise<{
  animals: Animal[];
}> {
  const [latestReadings, cows] = await Promise.all([
    getLatestReadings(),
    getCows(),
  ]);

  if (!cows || cows.length === 0) {
    return { animals: [] };
  }

  // Create lookup for readings mapping cow_id to reading
  const readingMap = new Map();
  if (latestReadings) {
    latestReadings.forEach((r) => readingMap.set(r.cow_id, r));
  }

  // We process in batches to prevent "Failed to fetch" errors caused by opening
  // too many concurrent connections
  const animals: Animal[] = [];
  const chunkSize = 5;

  for (let i = 0; i < cows.length; i += chunkSize) {
    const chunk = cows.slice(i, i + chunkSize);

    const chunkResults = await Promise.all(
      chunk.map(async (cow) => {
        const cowId = cow.id || cow.cow_id;
        const reading = readingMap.get(cowId);

        let health = null;
        if (reading) {
          health = await getHealthStatus(cowId);
        }
        const prediction = pickEffectivePrediction(health);

        return {
          id: String(cowId),
          breed: cow.breed || "Mestiza",
          status: toFrontendStatus(prediction.status),
          temperature: reading?.temperatura_corporal_prom ?? "--",
          heartRate: reading?.frec_cardiaca_prom
            ? Math.round(reading.frec_cardiaca_prom)
            : "--",
          distance: reading?.metros_recorridos
            ? Math.round(reading.metros_recorridos)
            : "--",
          lastUpdated: reading?.timestamp
            ? new Date(reading.timestamp).toLocaleString([], {
                year: "numeric",
                month: "2-digit",
                day: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
              })
            : "N/A",
        } satisfies Animal;
      }),
    );

    animals.push(...chunkResults);
  }

  return { animals };
}

export async function fetchAnimalDetail(idString: string) {
  const cowId = parseInt(idString.replace(/\D/g, ""), 10);
  if (isNaN(cowId)) return null;

  const [cowRes, readingsRes, healthStatus, healthHistory] = await Promise.all([
    fetch(`${API_BASE_URL}/cows/${cowId}`, { cache: "no-store" }).then((r) =>
      r.ok ? r.json() : null,
    ),
    fetch(`${API_BASE_URL}/cows/${cowId}/readings?page=1&size=200`, {
      cache: "no-store",
    }).then((r) => (r.ok ? r.json() : [])),
    getHealthStatus(cowId),
    getHealthHistory(cowId),
  ]);

  if (!cowRes) return null;

  const rawReadings = Array.isArray(readingsRes)
    ? readingsRes
    : readingsRes?.items || readingsRes?.readings || [];

  const validReadings = rawReadings.filter((r: any) => isNotFutureDate(r?.timestamp));

  const chartData = validReadings
    .map((r: any) => ({
      time: new Date(r.timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      value: r.temperatura_corporal_prom,
    }))
    .reverse();

  const latestReading = validReadings.length > 0 ? validReadings[0] : null;
  const prediction = pickEffectivePrediction(healthStatus);

  const frontendStatus = toFrontendStatus(prediction.status);

  const normalizedHealthStatus = healthStatus
    ? {
        ...healthStatus,
        status: normalizeCowStatus(healthStatus.status),
        primary_status: normalizeCowStatus(healthStatus.primary_status),
        secondary_status: normalizeCowStatus(healthStatus.secondary_status),
      }
    : null;

  const regDateStr = cowRes.registration_date || new Date().toISOString();
  let currentAgeMonths = Number(cowRes.age_months) || 0;
  
  if (cowRes.registration_date) {
    const regDate = new Date(cowRes.registration_date);
    const now = new Date();
    const monthsPassed = (now.getFullYear() - regDate.getFullYear()) * 12 + (now.getMonth() - regDate.getMonth());
    if (monthsPassed > 0) {
      currentAgeMonths += monthsPassed;
    }
  }

  const rawBreed = cowRes.breed?.trim();

  const animalInfo = {
    id: idString,
    breed: rawBreed && rawBreed.toLowerCase() !== "string" ? rawBreed : "Mestiza",
    ageMonths: currentAgeMonths,
    registrationDate: regDateStr,
    status: frontendStatus,
    temperature: latestReading?.temperatura_corporal_prom || 38.5,
    heartRate: latestReading?.frec_cardiaca_prom
      ? Math.round(latestReading.frec_cardiaca_prom)
      : 70,
    distance: latestReading?.metros_recorridos
      ? Math.round(latestReading.metros_recorridos)
      : 0,
    rumination: latestReading?.hubo_rumia ?? false,
    rmssd: latestReading?.rmssd || 0,
    sdnn: latestReading?.sdnn || 0,
    vocalization: latestReading?.hubo_vocalizacion ?? false,
    latitude: latestReading?.latitud || null,
    longitude: latestReading?.longitud || null,
    lastUpdated: latestReading?.timestamp
      ? new Date(latestReading.timestamp).toLocaleString([], {
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        })
      : "N/A",
  };

  return {
    animal: animalInfo,
    chartData,
    healthStatus: normalizedHealthStatus,
    healthHistory,
    prediction,
  };
}
