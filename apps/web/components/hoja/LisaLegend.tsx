import styles from "./lisa-legend.module.css";

export const LISA_LABELS: Record<string, string> = {
  HH: "Alto entre altos",
  LL: "Bajo entre bajos",
  HL: "Alto entre bajos",
  LH: "Bajo entre altos",
  NS: "Sin asociación significativa",
  NE: "No evaluable · sin vecinos",
};

/**
 * Las seis categorías LISA. Las cuatro primeras son asociaciones locales; NS
 * es ausencia de evidencia, no presión baja; NE es un municipio sin vecinos
 * en la muestra, que se ve pero no se evalúa.
 */
export default function LisaLegend({ compact = false }: { compact?: boolean }) {
  return (
    <ul className={`${styles.legend}${compact ? ` ${styles.compact}` : ""}`}>
      {Object.entries(LISA_LABELS).map(([key, label]) => (
        <li key={key}>
          <i data-cluster={key} aria-hidden="true" />
          <b>{key}</b>
          <span>{label}</span>
        </li>
      ))}
    </ul>
  );
}
