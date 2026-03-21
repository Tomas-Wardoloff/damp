import { type Animal } from "@/components/animal/AnimalCard";
import { type Alert } from "@/components/alerts/AlertFeed";
import { HealthAnalysisResponse } from "@/types";
import { MOCK_ALERTS } from "./mock-data";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

function pickEffectivePrediction(health: Record<string, unknown> | null | undefined): {
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

  const secondaryStatus = typeof health?.secondary_status === "string" ? health.secondary_status : null;
  const secondaryConfidence =
    typeof health?.secondary_confidence === "number" ? health.secondary_confidence : null;

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

function toFrontendStatus(status: string | null): "healthy" | "warning" | "critical" {
  if (!status) return "healthy";

  if (["CLINICA", "MASTITIS"].includes(status)) {
    return "critical";
  }

  if (["SUBCLINICA", "FEBRIL", "DIGESTIVO"].includes(status)) {
    return "warning";
  }

  return "healthy";
}

function normalizeCowStatus(status: string | undefined): string {
  if (!status) return "HEALTHY";
  return status === "SANA" ? "HEALTHY" : status;
}

/* eslint-disable @typescript-eslint/no-explicit-any */
export async function getCows(): Promise<any[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/cows`, { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch cows:", err);
    return [];
  }
}

export async function getLatestReading(cowId: number): Promise<any | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/cows/${cowId}/readings?page=1&size=1`, {
      cache: "no-store",
    });
    if (!res.ok) return null;

    const data = await res.json();
    return data?.items && data.items.length > 0 ? data.items[0] : null;
  } catch (err) {
    console.error(`Failed to fetch reading for cow ${cowId}:`, err);
    return null;
  }
}

export async function getHealthStatus(cowId: number): Promise<any | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/health/status/${cowId}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error(`Failed to fetch health status for cow ${cowId}:`, err);
    return null;
  }
}

export async function getHealthHistory(cowId: number): Promise<HealthAnalysisResponse[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/health/history/${cowId}`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.error(`Failed to fetch health history for cow ${cowId}:`, err);
    return [];
  }
}

export async function getLatestHealthByHistory(cowId: number): Promise<any | null> {
  try {
    const history = await getHealthHistory(cowId);
    return history.length > 0 ? history[0] : null;
  } catch (err) {
    console.error(`Failed to fetch latest health by history for cow ${cowId}:`, err);
    return null;
  }
}

export async function getLatestReadings(): Promise<any[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/readings/latests`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
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
  alerts: Alert[];
}> {
  const [latestReadings, cows] = await Promise.all([getLatestReadings(), getCows()]);

  const allCowIds = new Set<number>();
  const cowInfoMap = new Map<number, any>();
  const readingMap = new Map<number, any>();

  if (Array.isArray(cows)) {
    cows.forEach((cow) => {
      const cowId = Number(cow.id || cow.cow_id);
      if (!Number.isFinite(cowId)) return;
      allCowIds.add(cowId);
      cowInfoMap.set(cowId, cow);
    });
  }

  if (Array.isArray(latestReadings)) {
    latestReadings.forEach((reading) => {
      const cowId = Number(reading.cow_id || reading.id);
      if (!Number.isFinite(cowId)) return;
      allCowIds.add(cowId);
      readingMap.set(cowId, reading);
    });
  }

  if (allCowIds.size === 0) {
    return { animals: [], alerts: [] };
  }

  const animals: Animal[] = [];
  const chunkSize = 5;
  const allCowsArray = Array.from(allCowIds);

  for (let i = 0; i < allCowsArray.length; i += chunkSize) {
    const chunk = allCowsArray.slice(i, i + chunkSize);

    const chunkResults = await Promise.all(
      chunk.map(async (cowId) => {
        const cow = cowInfoMap.get(cowId) || {};
        const reading = readingMap.get(cowId);
        const health = await getHealthStatus(cowId);
        const prediction = pickEffectivePrediction(health);

        return {
          id: String(cowId),
          breed: cow.breed || "Mestiza",
          status: toFrontendStatus(prediction.status),
          temperature: reading?.temperatura_corporal_prom ?? 38.5,
          heartRate: reading?.frec_cardiaca_prom ? Math.round(reading.frec_cardiaca_prom) : 70,
          distance: reading?.metros_recorridos ? Math.round(reading.metros_recorridos) : 0,
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

  return { animals, alerts: MOCK_ALERTS };
}

export async function fetchAnimalDetail(idString: string) {
  const cowId = parseInt(idString.replace(/\D/g, ""), 10);
  if (isNaN(cowId)) return null;

  const [cowRes, readingsRes, healthStatus, healthHistory] = await Promise.all([
    fetch(`${API_BASE_URL}/cows/${cowId}`, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)),
    fetch(`${API_BASE_URL}/cows/${cowId}/readings?page=1&size=288`, {
      cache: "no-store",
    }).then((r) => (r.ok ? r.json() : [])),
    getHealthStatus(cowId),
    getHealthHistory(cowId),
  ]);

  if (!cowRes) return null;

  const rawReadings = Array.isArray(readingsRes) ? readingsRes : readingsRes?.items || readingsRes?.readings || [];

  const chartData = rawReadings
    .map((r: any) => ({
      time: new Date(r.timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      value: r.temperatura_corporal_prom,
    }))
    .reverse();

  const latestReading = rawReadings.length > 0 ? rawReadings[0] : null;
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

  const animalInfo = {
    id: idString,
    breed: cowRes.breed || "Mestiza",
    ageMonths: cowRes.age_months || 0,
    registrationDate: cowRes.registration_date || new Date().toISOString(),
    status: frontendStatus,
    temperature: latestReading?.temperatura_corporal_prom || 38.5,
    heartRate: latestReading?.frec_cardiaca_prom ? Math.round(latestReading.frec_cardiaca_prom) : 70,
    distance: latestReading?.metros_recorridos ? Math.round(latestReading.metros_recorridos) : 0,
    rumination: latestReading?.hubo_rumia ?? false,
    rmssd: latestReading?.rmssd || 0,
    sdnn: latestReading?.sdnn || 0,
    vocalization: latestReading?.hubo_vocalizacion ?? false,
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
