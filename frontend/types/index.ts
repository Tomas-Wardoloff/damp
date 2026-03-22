export interface CowResponse {
  id: number;
  breed: string;
  registration_date: string;
  age_months: number;
}

export type CowStatus =
  | "SANA"
  | "SUBCLINICA"
  | "CLINICA"
  | "MASTITIS"
  | "CELO"
  | "FEBRIL"
  | "DIGESTIVO"
  | "SIN DATOS";

export type UrgencyLevel = "none" | "low" | "medium" | "high";

export interface DiagnosisContent {
  label: string;
  urgency: UrgencyLevel;
  summary: string;
  what_it_means: string;
  recommendation: string;
  timeframe: string;
}

export const DIAGNOSIS_CONTENT: Record<CowStatus, DiagnosisContent> = {
  SANA: {
    label: "Saludable",
    urgency: "none",
    summary: "El animal se encuentra dentro de todos los parámetros normales.",
    what_it_means:
      "La temperatura corporal, frecuencia cardíaca, actividad de movimiento y rumia están en rangos esperados para su raza y edad. No se detectaron señales de alerta.",
    recommendation:
      "Continuar con el monitoreo rutinario. No se requiere intervención.",
    timeframe: "Próxima revisión: seguimiento estándar",
  },
  CLINICA: {
    label: "Estado Clínico",
    urgency: "high",
    summary: "El animal presenta síntomas severos de enfermedad clínica.",
    what_it_means:
      "Los biomarcadores indican un cuadro clínico evidente. El animal requiere aislamiento y atención inmediata.",
    recommendation: "Contactar de urgencia al veterinario e iniciar protocolo de tratamiento respectivo.",
    timeframe: "Intervención requerida: Inmediata",
  },
  "SIN DATOS": {
    label: "Faltan datos",
    urgency: "none",
    summary: "No hay suficientes datos biométricos recolectados del animal.",
    what_it_means:
      "Los sensores no han registrado datos recientemente. Puede deberse a problemas de conectividad, collar apagado, o datos pendientes de procesamiento.",
    recommendation:
      "Verificar el estado de la batería del collar y su correcta colocación en el animal.",
    timeframe: "Próxima revisión: Cuando se restablezca la conexión",
  },

  SUBCLINICA: {
    label: "Estado subclínico",
    urgency: "low",
    summary:
      "El animal muestra señales tempranas de malestar que aún no se expresan visualmente.",
    what_it_means:
      "Los sensores detectaron variaciones sutiles en la actividad cardíaca y un leve incremento de temperatura. El animal todavía se ve aparentemente normal, pero los datos sugieren que algo está comenzando a desarrollarse.",
    recommendation:
      "Elevar la prioridad de observación. Revisar el animal en las próximas horas para evaluar si los síntomas progresan.",
    timeframe: "Intervención sugerida: dentro de las próximas 6–12 horas",
  },

  MASTITIS: {
    label: "Posible mastitis",
    urgency: "high",
    summary:
      "Patrón compatible con infección mamaria activa. Requiere atención veterinaria.",
    what_it_means:
      "La combinación de temperatura elevada, reducción significativa del movimiento y signos de estrés fisiológico es característica de mastitis. Esta condición afecta la producción de leche y puede volverse severa si no se trata a tiempo.",
    recommendation:
      "Contactar al veterinario de manera urgente. Examinar manualmente los cuatro cuartos mamarios para identificar el afectado. Iniciar protocolo de tratamiento antibiótico según indicación profesional.",
    timeframe: "Intervención requerida: inmediata",
  },

  CELO: {
    label: "Celo detectado",
    urgency: "low",
    summary:
      "El animal se encuentra en período fértil. Ventana de inseminación activa.",
    what_it_means:
      "Se detectó un incremento marcado en la actividad de movimiento, especialmente en horario nocturno, junto con una mayor dispersión geográfica. Este patrón es característico del estro bovino y representa la ventana óptima para la reproducción.",
    recommendation:
      "Programar inseminación artificial o monta natural en las próximas 12–18 horas para maximizar la tasa de concepción.",
    timeframe: "Ventana fértil: activa ahora, cierra en ~18 horas",
  },

  FEBRIL: {
    label: "Cuadro febril",
    urgency: "medium",
    summary:
      "Temperatura corporal elevada sostenida. Posible proceso infeccioso en curso.",
    what_it_means:
      "La temperatura supera el umbral normal de manera consistente. El movimiento y la actividad cardíaca son relativamente normales, lo que sugiere una infección sistémica o un factor ambiental como causa probable.",
    recommendation:
      "Evaluar posibles focos infecciosos. Controlar temperatura cada 2–3 horas. Si supera 40.5°C o persiste más de 24 horas, consultar al veterinario.",
    timeframe: "Intervención sugerida: dentro de las próximas 12 horas",
  },

  DIGESTIVO: {
    label: "Problema digestivo",
    urgency: "medium",
    summary:
      "Actividad ruminal comprometida. Posible alteración en la digestión.",
    what_it_means:
      "Los sensores detectaron ausencia o reducción significativa de la rumia, junto con menor actividad de movimiento. Este patrón puede indicar acidosis ruminal, indigestión simple u otras alteraciones gastrointestinales relacionadas con la alimentación.",
    recommendation:
      "Revisar la ración y el acceso al agua. Administrar sales buffer o bicarbonato de sodio como medida inicial. Si la rumia no se recupera en 12 horas, consultar al veterinario.",
    timeframe: "Intervención sugerida: dentro de las próximas 6 horas",
  },
};

export const URGENCY_CONFIG: Record<
  UrgencyLevel,
  {
    color: string;
    bg: string;
    border: string;
    label: string;
    icon: string;
  }
> = {
  none: {
    color: "text-primary",
    bg: "bg-primary-container/10",
    border: "border-primary/20",
    label: "Sin urgencia",
    icon: "✓",
  },
  low: {
    color: "text-pink-400",
    bg: "bg-pink-500/10",
    border: "border-pink-500/20",
    label: "Baja prioridad",
    icon: "!",
  },
  medium: {
    color: "text-secondary",
    bg: "bg-secondary-container/20",
    border: "border-secondary/30",
    label: "Atención necesaria",
    icon: "!!",
  },
  high: {
    color: "text-tertiary",
    bg: "bg-tertiary-container/10",
    border: "border-tertiary/20",
    label: "Urgente",
    icon: "!!!",
  },
};

export interface ReadingResponse {
  id?: number;
  cow_id: number;
  timestamp: string;
  temperatura_corporal_prom: number;
  frec_cardiaca_prom: number;
  metros_recorridos: number;
  hubo_rumia?: boolean;
  hubo_vocalizacion?: boolean;
  rmssd?: number;
  sdnn?: number;
}

export interface HealthAnalysisResponse {
  id: number;
  cow_id?: number;
  created_at: string;
  status: string;
  confidence?: number;
}
