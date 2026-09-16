import type { DataQuality } from "@/lib/api";
import { fmt, layerLabel, qualityLabel } from "@/lib/format";

import styles from "./data-quality.module.css";

const score = (value: number | null | undefined) =>
  value == null ? "No evaluable" : `${fmt(value)} / 100`;

/**
 * Calidad del dato del IPR-4 (DQS): cobertura y actualidad de lo que se usó
 * para calcular la puntuación. Va junto al índice pero nunca lo modifica, y
 * se escribe con su propia escala para que no se lea como presión.
 */
export default function DataQualityBlock({
  quality,
  compact = false,
}: {
  quality: DataQuality | null | undefined;
  compact?: boolean;
}) {
  const low = quality?.level === "baja" || quality?.level === "muy_baja";

  return (
    <section
      className={`${styles.block}${compact ? ` ${styles.compact}` : ""}`}
      aria-label="Calidad del dato del IPR-4"
    >
      <p className={styles.kicker}>Calidad del dato · IPR-4</p>
      <p className={styles.headline}>
        <strong className={styles.figure} data-level={quality?.level ?? "none"}>
          {quality?.score == null ? "—" : fmt(quality.score)}
        </strong>
        <span>
          {quality ? qualityLabel(quality.level) : "No disponible"}
          <small>Cobertura y actualidad de los datos; no mide presión.</small>
        </span>
      </p>

      {low && (
        <p className={styles.notice} role="status">
          Interpreta la puntuación con cautela: los datos de este municipio tienen
          limitaciones de cobertura o de actualidad.
        </p>
      )}

      {quality && (
        <details className={styles.details}>
          <summary>Ver desglose y limitaciones</summary>
          <dl className={styles.facts}>
            <div>
              <dt>Cobertura</dt>
              <dd>{score(quality.coverage)}</dd>
            </div>
            <div>
              <dt>Actualidad</dt>
              <dd>{score(quality.recency)}</dd>
            </div>
            <div>
              <dt>Consistencia</dt>
              <dd>{score(quality.consistency)} · sin evidencia municipal trazable</dd>
            </div>
          </dl>
          <ul className={styles.components}>
            {quality.components.map((component) => (
              <li key={component.component}>
                <b>{layerLabel(component.component, true)}</b>
                <span>
                  Calidad {score(component.quality_score)} · periodo{" "}
                  {component.statistical_period}
                </span>
                <span>
                  Cobertura {score(component.coverage_score)} · actualidad{" "}
                  {score(component.recency_score)}
                </span>
              </li>
            ))}
          </ul>
          {quality.issues.length > 0 && (
            <ul className={styles.issues}>
              {quality.issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          )}
          <p className={styles.small}>
            El DQS no es una probabilidad de acierto ni un intervalo de confianza.
            Versión {quality.calculation_version}.
          </p>
        </details>
      )}
    </section>
  );
}
