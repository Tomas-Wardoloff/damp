import * as React from "react"
import { cn } from "@/lib/utils"
import { AnimalCard, type Animal } from "@/components/animal/AnimalCard"

interface HerdMapProps extends React.HTMLAttributes<HTMLDivElement> {
  animals: Animal[]
  onAnimalClick: (id: string) => void
  lastFetchTime?: Date | null
}

export function HerdMap({ animals, onAnimalClick, lastFetchTime, className, ...props }: HerdMapProps) {
  return (
    <div className={cn("flex flex-col h-full gap-4", className)} {...props}>
      <div className="flex justify-between items-center mb-2">
        <h2 className="text-headline-md font-display">Monitoreo en Tiempo Real</h2>
        <span className="text-label-sm font-mono text-on-surface-variant uppercase flex items-center gap-2">
          {lastFetchTime && (
            <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          )}
          {lastFetchTime ? `Última act: ${lastFetchTime.toLocaleString()}` : "Conectando..."}
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 overflow-y-auto pr-2 pb-10">
        {animals.map((animal) => (
          <AnimalCard 
            key={animal.id} 
            animal={animal} 
            onClick={() => onAnimalClick(animal.id)} 
          />
        ))}
      </div>
    </div>
  )
}
