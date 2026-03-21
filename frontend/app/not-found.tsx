import { Button } from "@/components/ui/Button"

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center h-screen bg-surface text-on-surface">
      <div className="flex flex-col items-center gap-6 max-w-md text-center">

        <h1 className="text-display-lg font-display tracking-tight leading-none text-on-surface">
          Error 404
        </h1>

        <p className="text-body-lg text-on-surface-variant font-mono">
          La ruta que buscas está fuera de nuestro perímetro de monitoreo.
        </p>

        <Button href="/" variant="primary" className="mt-4 hover:scale-[1.02] active:scale-[0.98]">
          Volver al Panel Principal
        </Button>
      </div>

      <div className="fixed bottom-10 left-10 text-label-sm font-mono text-outline/40">
        SYS.ERR.404_NOT_FOUND
      </div>
    </div>
  )
}
