import { FC } from "react";
import { Activity, Thermometer, ShieldAlert, CheckCircle2 } from "lucide-react";
import { type HealthAnalysisResponse } from "@/types";

interface Props {
  history: HealthAnalysisResponse[];
}

export const HealthHistoryTimeline: FC<Props> = ({ history }) => {
  if (!history || history.length === 0) {
    return (
      <div className="p-6 text-center text-on-surface-variant font-mono">
        No hay historial de salud registrado.
      </div>
    );
  }

  return (
    <div className="bg-surface-container-low rounded-xl border border-outline-variant/30 p-6">
      <h3 className="text-title-lg font-semibold text-on-surface mb-6 flex items-center gap-2">
        <Activity className="w-5 h-5 text-primary" />
        Evolución del estado de salud
      </h3>
      <div className="relative border-l-2 border-outline-variant/50 ml-3 space-y-8">
        {history.map((record) => {
          const date = new Date(record.created_at);
          const timeString = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          const dateString = date.toLocaleDateString();

          let Icon = CheckCircle2;
          let iconColor = "text-primary";
          let bgIcon = "bg-primary-container/20";
          let statusText = "Sana";
          let descText = "Todo en rango normal.";
          const normStatus = record.status?.toLowerCase();

          switch (normStatus) {
            case "mastitis":
              Icon = ShieldAlert;
              iconColor = "text-tertiary";
              bgIcon = "bg-tertiary-container/20";
              statusText = "Mastitis";
              descText = "Temp alta + movimiento bajo + RMSSD bajo";
              break;
            case "subclinica":
              Icon = Thermometer;
              iconColor = "text-secondary";
              bgIcon = "bg-secondary-container/20";
              statusText = "Subclínica";
              descText = "RMSSD cae primero, temp leve incremento";
              break;
            case "celo":
              Icon = Activity;
              iconColor = "text-blue-400";
              bgIcon = "bg-blue-500/20";
              statusText = "Celo";
              descText = "Movimiento x3 especialmente nocturno, GPS spread alto";
              break;
            case "febril":
              Icon = Thermometer;
              iconColor = "text-secondary";
              bgIcon = "bg-secondary-container/20";
              statusText = "Febril";
              descText = "Temp alta, movimiento casi normal, RMSSD ok";
              break;
            case "digestivo":
              Icon = ShieldAlert;
              iconColor = "text-secondary";
              bgIcon = "bg-secondary-container/20";
              statusText = "Digestivo";
              descText = "Rumia colapsa, movimiento bajo, temp leve, HR moderada";
              break;
          }

          return (
            <div key={record.id} className="relative pl-6">
              <span className={`absolute -left-[17px] top-1 h-8 w-8 rounded-full flex items-center justify-center ring-4 ring-surface ${bgIcon}`}>
                <Icon className={`w-4 h-4 ${iconColor}`} />
              </span>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-1">
                <h4 className="text-label-lg font-bold text-on-surface">{statusText}</h4>
                <time className="text-label-sm text-on-surface-variant font-mono">
                  {dateString} {timeString}
                </time>
              </div>
              <p className="text-body-sm text-on-surface-variant">
                {descText}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
