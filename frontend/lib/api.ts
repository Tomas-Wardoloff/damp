import { type Animal } from "@/components/animal/AnimalCard";
import { type Alert } from "@/components/alerts/AlertFeed";
import { HealthAnalysisResponse } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

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
    const res = await fetch(`${API_BASE_URL}/cows/${cowId}/readings`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data = await res.json();
    return Array.isArray(data) && data.length > 0 ? data[0] : null;
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

export async function getHealthHistory(
  cowId: number,
): Promise<HealthAnalysisResponse[]> {
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

  // Consolidate unique cows from BOTH database and active latest readings
  const allCowIds = new Set<number>();
  const cowInfoMap = new Map();
  const readingMap = new Map();

  if (cows && Array.isArray(cows)) {
    cows.forEach((cow) => {
      const cowId = cow.id || cow.cow_id;
      allCowIds.add(cowId);
      cowInfoMap.set(cowId, cow);
    });
  }

  if (latestReadings && Array.isArray(latestReadings)) {
    latestReadings.forEach((reading) => {
      const cowId = reading.cow_id || reading.id;
      allCowIds.add(cowId);
      readingMap.set(cowId, reading);
    });
  }

  // If we have literally 0 cows in both lists
  if (allCowIds.size === 0) {
    return { animals: [], alerts: [] };
  }

  const allCowsArray = Array.from(allCowIds);
  const animals: Animal[] = [];
  const chunkSize = 5;

  for (let i = 0; i < allCowsArray.length; i += chunkSize) {
    const chunk = allCowsArray.slice(i, i + chunkSize);

    const chunkResults = await Promise.all(
      chunk.map(async (cowId) => {
        const cow = cowInfoMap.get(cowId) || {};
        const reading = readingMap.get(cowId);
        const health = await getHealthStatus(cowId);

        let frontendStatus = "sana";
        if (health && health.status) {
          frontendStatus = health.status.toLowerCase();
        }

        return {
          id: String(cowId),
          breed: cow.breed || "Mestiza",
          status: frontendStatus,
          temperature: reading?.temperatura_corporal_prom || "--",
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
        };
      }),
    );

    animals.push(...chunkResults);
  }

  return { animals, alerts: [] };
}

export async function fetchAnimalDetail(idString: string) {
  const cowId = parseInt(idString);

  if (isNaN(cowId)) return null;

  const [cowRes, readingsRes, healthStatus, healthHistory] = await Promise.all([
    fetch(`${API_BASE_URL}/cows/${cowId}`, { cache: "no-store" }).then((r) =>
      r.ok ? r.json() : null,
    ),
    fetch(`${API_BASE_URL}/cows/${cowId}/readings`, {
      cache: "no-store",
    }).then((r) => (r.ok ? r.json() : [])), // Get last 24 hours
    getHealthStatus(cowId),
    getHealthHistory(cowId),
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

  let frontendStatus = "sana";
  if (healthStatus && healthStatus.status) {
    frontendStatus = healthStatus.status.toLowerCase();
  }

  const animalInfo = {
    id: idString,
    breed: cowRes.breed || "Mestiza",
    ageMonths: cowRes.age_months || 0,
    registrationDate: cowRes.registration_date || new Date().toISOString(),
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

  return { animal: animalInfo, chartData, healthStatus, healthHistory };
}
