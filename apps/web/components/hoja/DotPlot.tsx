import type { Benchmark, Detail } from "@/lib/api";
import { fmt, layerLabel, placeName } from "@/lib/format";

import styles from "./dot-plot.module.css";

const LEVEL_LABELS: Record<Benchmark["nivel"], string> = {
  provincia: "Provincia",
  ccaa: "Comunidad",
  espana: "Media estudiada",
};

/**
 * Dónde queda el municipio frente a su provincia, su comunidad y el conjunto
 * estudiado, factor a factor. Cada serie tiene su propia marca, no su propio
 * color: así se distingue también sin ver el color.
 */
export default function DotPlot({
  detail,
  benchmarks,
}: {
  detail: Detail;
  benchmarks: Benchmark[];
}) {
  const rows = [
    { key: "score", label: "Puntuación total", own: detail.score },
    ...detail.capas.map((capa) => ({
      key: capa.nombre,
      label: layerLabel(capa.nombre, true),
      own: capa.score,
    })),
  ];

  return (
    <div className={styles.plot}>
      <ul className={styles.legend}>
        <li data-level="own">{placeName(detail.nombre)}</li>
        {benchmarks.map((item) => (
          <li key={item.nivel} data-level={item.nivel}>
            {item.nivel === "espana"
              ? "Media de los municipios estudiados"
              : item.nivel === "provincia"
                ? `Provincia de ${placeName(item.territorio)}`
                : placeName(item.territorio)}
          </li>
        ))}
      </ul>

      {rows.map((row) => (
        <div className={styles.row} key={row.key}>
          <span className={styles.label}>{row.label}</span>
          <span className={styles.track}>
            {benchmarks.map((item) => {
              const value = item[row.key as keyof Benchmark] as number | null;
              return value == null ? null : (
                <i
                  key={item.nivel}
                  className={styles.dot}
                  data-level={item.nivel}
                  style={{ left: `${value}%` }}
                  title={`${LEVEL_LABELS[item.nivel]}: ${fmt(value)}`}
                />
              );
            })}
            {row.own != null && (
              <i
                className={styles.dot}
                data-level="own"
                style={{ left: `${row.own}%` }}
                title={`${placeName(detail.nombre)}: ${fmt(row.own)}`}
              />
            )}
          </span>
          <b className={styles.value}>{fmt(row.own)}</b>
        </div>
      ))}

      <div className={styles.axis} aria-hidden="true">
        <span>0</span>
        <span>50</span>
        <span>100</span>
      </div>
    </div>
  );
}
