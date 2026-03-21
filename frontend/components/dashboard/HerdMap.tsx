import * as React from "react"
import { cn } from "@/lib/utils"
import { AnimalCard, type Animal } from "@/components/animal/AnimalCard"

interface HerdMapProps extends React.HTMLAttributes<HTMLDivElement> {
  animals: Animal[]
  onAnimalClick: (id: string) => void
  lastFetchTime?: Date | null
}

export function HerdMap({ animals, onAnimalClick, lastFetchTime, className, ...props }: HerdMapProps) {
  const animalsWithData = animals.filter(a => a.status !== "sin datos");
  const animalsWithoutData = animals.filter(a => a.status === "sin datos");

  return (
    <div className={cn("flex flex-col h-full gap-4", className)} {...props}>
      <div className="flex justify-between items-center mb-2 shrink-0">
        <h2 className="text-headline-md font-display">Monitoreo en Tiempo Real</h2>
        <span className="text-label-sm font-mono text-on-surface-variant uppercase flex items-center gap-2">
          {lastFetchTime && (
            <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          )}
          {lastFetchTime ? `Última act: ${lastFetchTime.toLocaleString()}` : "Conectando..."}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto pr-2 pb-10 flex flex-col gap-8">
        {/* Section 1: With Data */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <h3 className="text-body-md font-medium text-on-surface-variant">Con Datos Recientes</h3>
            <span className="bg-surface-container-highest px-2 py-0.5 rounded-full text-label-sm text-on-surface">{animalsWithData.length}</span>
          </div>

          {animalsWithData.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {animalsWithData.map((animal) => (
                <AnimalCard
                  key={animal.id}
                  animal={animal}
                  onClick={() => onAnimalClick(animal.id)}
                />
              ))}
            </div>
          ) : (
            <div className="p-8 border border-dashed border-outline-variant/30 rounded-xl flex items-center justify-center">
              <p className="text-label-md text-on-surface-variant font-mono uppercase">Ninguna vaca transmitiendo</p>
            </div>
          )}
        </div>

        {/* Section 2: Without Data */}
        {animalsWithoutData.length > 0 && (
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <h3 className="text-body-md font-medium text-on-surface-variant">Sin Datos</h3>
              <span className="bg-surface-container-highest px-2 py-0.5 rounded-full text-label-sm text-on-surface">{animalsWithoutData.length}</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 opacity-80 mix-blend-luminosity">
              {animalsWithoutData.map((animal) => (
                <AnimalCard
                  key={animal.id}
                  animal={animal}
                  onClick={() => onAnimalClick(animal.id)}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
