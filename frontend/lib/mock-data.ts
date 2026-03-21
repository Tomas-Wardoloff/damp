import { type Animal } from "@/components/animal/AnimalCard"
import { type Alert } from "@/components/alerts/AlertFeed"

export const MOCK_ANIMALS: Animal[] = Array.from({ length: 40 }).map((_, i) => {
  const isWarning = i === 4 || i === 12
  const isCritical = i === 7
  
  // Deterministic math based on index
  const tempOffset = (i % 5) * 0.1
  const hrOffset = (i % 8) * 2
  const respOffset = (i % 4) * 2

  return {
    id: (1000 + i).toString(),
    breed: "Angus",
    status: isCritical ? "critical" : isWarning ? "warning" : "healthy",
    temperature: isCritical ? 39.8 : isWarning ? 39.4 : 38.5 + tempOffset,
    heartRate: isCritical ? 95 : isWarning ? 88 : 70 + hrOffset,
    distance: 140 + i * 4,
    lastUpdated: "Justo ahora"
  }
})

export const MOCK_ALERTS: Alert[] = [
  {
    id: "al-1",
    animalId: "AG-1007",
    animalName: "Vaca 8",
    condition: "Fiebre temprana detectada. Rumia disminuida.",
    severity: "critical",
    timestamp: "Hace 12 min"
  },
  {
    id: "al-2",
    animalId: "AG-1004",
    animalName: "Vaca 5",
    condition: "Frecuencia cardíaca elevada sostenida.",
    severity: "warning",
    timestamp: "Hace 45 min"
  },
  {
    id: "al-3",
    animalId: "AG-1012",
    animalName: "Vaca 13",
    condition: "Patrón respiratorio anormal.",
    severity: "warning",
    timestamp: "Hace 2 horas"
  }
]

export const generateBiometricData = () => {
  const data = []
  let temp = 38.6
  
  for (let i = 24; i >= 0; i--) {
    // Deterministic math instead of Math.random
    const pseudoRandom = ((i * 17) % 10) / 10
    
    // Add artificial trend going up
    if (i < 8) {
      temp += 0.15 + (pseudoRandom * 0.1)
    } else {
      temp += (pseudoRandom - 0.5) * 0.3
    }
    
    // Formatting time deterministically since Date.now() can hydration error
    // Use fixed recent hours (e.g. going back from 14:00)
    const hour = (14 - i + 24) % 24
    
    data.push({
      time: `${hour}:00`,
      value: Number(temp.toFixed(1))
    })
  }
  return data
}
