import { type Animal } from "@/components/animal/AnimalCard";
import { type Alert } from "@/components/alerts/AlertFeed";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// Mock alerts for now since the backend doesn't explicitly have an alerts endpoint defined
import { MOCK_ALERTS } from "./mock-data";

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
    const res = await fetch(
      `${API_BASE_URL}/cows/${cowId}/readings?page=1&size=1`,
      { cache: "no-store" },
    );
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

export async function fetchDashboardData(): Promise<{
  animals: Animal[];
  alerts: Alert[];
}> {
  // Parrallel request for dashboard speed
  const [latestReadings, cows] = await Promise.all([
    getLatestReadings(),
    getCows(),
  ]);

  if (!latestReadings || latestReadings.length === 0) {
    return { animals: [], alerts: MOCK_ALERTS };
  }

  // Create lookup for breed
  const cowMap = new Map();
  if (cows) {
    cows.forEach((cow) =>
      cowMap.set(cow.id || cow.cow_id, cow.breed || "Mestiza"),
    );
  }

  // To build the dashboard we need the AI status for each reading.
  // We process in batches to prevent "Failed to fetch" errors caused by opening
  // too many concurrent connections (browser connection limit / local server socket exhaustion).
  const animals: Animal[] = [];
  const chunkSize = 5;

  for (let i = 0; i < latestReadings.length; i += chunkSize) {
    const chunk = latestReadings.slice(i, i + chunkSize);

    const chunkResults = await Promise.all(
      chunk.map(async (reading) => {
        const cowId = reading.cow_id;
        const health = await getHealthStatus(cowId);

        // Map backend status to our frontend "healthy" | "warning" | "critical"
        let frontendStatus: "healthy" | "warning" | "critical" = "healthy";
        if (health && health.status) {
          if (health.status === "CLINICA") {
            frontendStatus = "critical";
          } else if (health.status === "SUBCLINICA") {
            frontendStatus = "warning";
          }
        }

        return {
          id: String(cowId),
          breed: cowMap.get(cowId) || "Mestiza",
          status: frontendStatus,
          temperature: reading?.temperatura_corporal_prom || 38.5,
          heartRate: reading?.frec_cardiaca_prom
            ? Math.round(reading.frec_cardiaca_prom)
            : 70,
          distance: reading?.metros_recorridos
            ? Math.round(reading.metros_recorridos)
            : 0,
          lastUpdated: reading?.timestamp
            ? new Date(reading.timestamp).toLocaleString([], {
                year: "numeric",
                month: "2-digit",
                day: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
              })
            : "N/A",
        };
      }),
    );

    animals.push(...chunkResults);
  }

  return { animals, alerts: MOCK_ALERTS }; // Keeping mock alerts for now
}

export async function fetchAnimalDetail(idString: string) {
  // Extract number from "AG-1"
  const cowId = parseInt(idString.replace(/\D/g, ""), 10);

  if (isNaN(cowId)) return null;

  const [cowRes, readingsRes, healthStatus] = await Promise.all([
    fetch(`${API_BASE_URL}/cows/${cowId}`, { cache: "no-store" }).then((r) =>
      r.ok ? r.json() : null,
    ),
    fetch(`${API_BASE_URL}/cows/${cowId}/readings?page=1&size=288`, {
      cache: "no-store",
    }).then((r) => (r.ok ? r.json() : [])), // Get last 24 hours (288 readings, 5 min intervals)
    getHealthStatus(cowId),
  ]);

  if (!cowRes) return null;

  // Process readings for chart
  // Check if readingsRes has an array inside (e.g. { items: [] }) or is an array
  const rawReadings = Array.isArray(readingsRes)
    ? readingsRes
    : readingsRes?.items || readingsRes?.readings || [];

  const chartData = rawReadings
    .map((r: any) => ({
      time: new Date(r.timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      value: r.temperatura_corporal_prom,
    }))
    .reverse(); // Assuming backend sorts DESC, we want ASC for chart

  const latestReading = rawReadings.length > 0 ? rawReadings[0] : null;

  let frontendStatus: "healthy" | "warning" | "critical" = "healthy";
  if (healthStatus && healthStatus.status) {
    if (healthStatus.status === "CLINICA") {
      frontendStatus = "critical";
    } else if (healthStatus.status === "SUBCLINICA") {
      frontendStatus = "warning";
    }
  }

  const animalInfo = {
    id: idString,
    breed: cowRes.breed || "Mestiza",
    status: frontendStatus,
    temperature: latestReading?.temperatura_corporal_prom || 38.5,
    heartRate: latestReading?.frec_cardiaca_prom
      ? Math.round(latestReading.frec_cardiaca_prom)
      : 70,
    distance: latestReading?.metros_recorridos
      ? Math.round(latestReading.metros_recorridos)
      : 0,
    rumination: latestReading?.hubo_rumia ? 40 : 15,
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

  return { animal: animalInfo, chartData, healthStatus };
}
