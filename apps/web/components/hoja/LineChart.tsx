"use client";

import { useEffect, useRef, useState } from "react";

import type { HistoricalPoint } from "@/lib/api";
import { fmt, layerLabel } from "@/lib/format";

import styles from "./line-chart.module.css";

/**
 * El color va atado al nombre de la serie, nunca a su posición: una misma
 * serie puede empezar en años distintos según el municipio, y con un reparto
 * por orden de llegada el mismo factor cambiaría de color de una ficha a otra.
 *
 * Los cinco factores llevan los tonos cromáticos. Los dos índices no son un
 * factor más, sino la puntuación completa, así que van en neutro: tinta el
 * observado y gris el prospectivo, que es un escenario y no un dato medido.
 */
const SERIES_COLORS: Record<string, string> = {
  asequibilidad: "var(--data-series-1)",
  turismo: "var(--data-series-3)",
  especulacion: "var(--data-series-4)",
  gentrificacion: "var(--data-series-5)",
  riesgo_futuro: "var(--data-series-6)",
  ipr_observado: "var(--data-series-2)",
  ipr_prospectivo: "var(--color-muted)",
  ipr_historico: "var(--color-accent)",
};

const SERIES_ORDER = Object.keys(SERIES_COLORS);

const seriesColor = (name: string) => SERIES_COLORS[name] ?? "var(--color-ink-2)";

/** Orden fijo de la leyenda; lo que no reconocemos va detrás, alfabético. */
function bySeriesOrder(a: string, b: string) {
  const ia = SERIES_ORDER.indexOf(a);
  const ib = SERIES_ORDER.indexOf(b);
  if (ia === -1 && ib === -1) return a.localeCompare(b);
  if (ia === -1) return 1;
  if (ib === -1) return -1;
  return ia - ib;
}

/**
 * Serie histórica de los factores, en SVG, midiendo su propio contenedor.
 *
 * Las series que solo tienen estimaciones van discontinuas: la línea continua
 * se reserva para lo observado. Los índices de un único año (IPR-4 e IPR-5,
 * ambos de 2023) aparecen como un punto suelto, no como una tendencia.
 *
 * El eje siempre va de 0 a 100, así que todas las series de una misma gráfica
 * tienen que medir lo mismo; `valueName` es el nombre de esa magnitud y sale en
 * el rótulo de cada punto, junto a la puntuación de origen cuando la hay.
 */
export default function LineChart({
  points,
  height = 240,
  cutYear,
  valueName = "posición",
}: {
  points: HistoricalPoint[];
  height?: number;
  /** Año del corte publicado: lo que queda a su derecha aún no entra en él. */
  cutYear?: number;
  /** Qué mide el eje en esta gráfica; sale en el rótulo de cada punto. */
  valueName?: string;
}) {
  const ref = useRef<HTMLElement>(null);
  const [width, setWidth] = useState(640);

  useEffect(() => {
    if (!ref.current) return;
    const observer = new ResizeObserver(([entry]) =>
      setWidth(Math.max(280, Math.round(entry.contentRect.width))),
    );
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  const years = [...new Set(points.map((point) => point.anio))].sort((a, b) => a - b);
  const series = [...new Set(points.map((point) => point.serie))].sort(bySeriesOrder);
  if (years.length === 0) {
    return <p className={styles.empty}>Sin serie histórica disponible.</p>;
  }
  // Con el eje estrecho las cifras se solapan, así que se rotula uno de cada dos.
  const yearStep = Math.max(1, Math.ceil((years.length * 34) / Math.max(width - 60, 1)));
  const cut =
    cutYear != null && cutYear > years[0] && cutYear < years[years.length - 1]
      ? cutYear
      : null;

  const pad = { l: 34, r: 14, t: 12, b: 26 };
  const x = (year: number) =>
    years.length === 1
      ? (pad.l + width - pad.r) / 2
      : pad.l +
        ((year - years[0]) / (years[years.length - 1] - years[0])) *
          (width - pad.l - pad.r);
  const y = (value: number) => pad.t + (1 - value / 100) * (height - pad.t - pad.b);
  const cutOnTheRight = cut != null && x(cut) > (width * 2) / 3;
  // El último año solo se rotula si no se pisa con el anterior ya rotulado.
  const previousLabelled = years.length - 1 - ((years.length - 1) % yearStep);
  const lastLabelled =
    x(years[years.length - 1]) - x(years[previousLabelled]) >= 30 ? years.length - 1 : -1;

  return (
    <figure className={styles.chart} ref={ref}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: "100%", height }}
        role="img"
        aria-label="Evolución de los factores"
      >
        {[0, 25, 50, 75, 100].map((tick) => (
          <g key={tick}>
            <line
              className={styles.grid}
              x1={pad.l}
              x2={width - pad.r}
              y1={y(tick)}
              y2={y(tick)}
            />
            <text className={styles.axis} x={pad.l - 8} y={y(tick) + 4} textAnchor="end">
              {tick}
            </text>
          </g>
        ))}

        {years
          .filter((_, index) => index % yearStep === 0 || index === lastLabelled)
          .map((year) => (
            <text
              key={year}
              className={styles.axis}
              x={x(year)}
              y={height - 6}
              textAnchor="middle"
            >
              {year}
            </text>
          ))}

        {cut == null ? null : (
          <g>
            <line
              className={styles.cut}
              x1={x(cut)}
              x2={x(cut)}
              y1={pad.t}
              y2={height - pad.b}
            />
            <text
              className={styles.cutLabel}
              x={x(cut) + (cutOnTheRight ? -5 : 5)}
              y={pad.t + 9}
              textAnchor={cutOnTheRight ? "end" : "start"}
            >
              corte del índice
            </text>
          </g>
        )}

        {series.map((name) => {
          const color = seriesColor(name);
          const own = points.filter((point) => point.serie === name && point.valor != null);
          const dashed = own.every((point) => point.tipo !== "observado");
          const alone = own.length === 1;
          const segments: string[] = [];
          let current = "";
          years.forEach((year) => {
            const value = points.find(
              (point) => point.anio === year && point.serie === name,
            )?.valor;
            if (value == null) {
              if (current) segments.push(current);
              current = "";
            } else {
              current += `${current ? "L" : "M"}${x(year).toFixed(1)},${y(value).toFixed(1)}`;
            }
          });
          if (current) segments.push(current);

          return (
            <g key={name} style={{ color }}>
              {segments.map((d) => (
                <path
                  key={d}
                  d={d}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2.5}
                  strokeDasharray={dashed ? "6 5" : undefined}
                />
              ))}
              {years.map((year) => {
                const point = points.find(
                  (item) => item.anio === year && item.serie === name,
                );
                const value = point?.valor;
                const raw = point?.bruto;
                const projected = point?.tipo === "proyectado";
                return value == null ? null : (
                  <circle
                    key={year}
                    cx={x(year)}
                    cy={y(value)}
                    r={alone ? 5 : 3.5}
                    fill={projected ? "var(--color-paper)" : "currentColor"}
                    stroke="currentColor"
                    strokeWidth={projected ? 2 : 0}
                  >
                    <title>
                      {`${layerLabel(name, true)} ${year}: ${valueName} ${fmt(value)}`}
                      {raw == null ? "" : ` · puntuación ${fmt(raw)}`}
                    </title>
                  </circle>
                );
              })}
            </g>
          );
        })}
      </svg>

      <figcaption className={styles.legend}>
        {series.map((name) => {
          const own = points.filter((point) => point.serie === name && point.valor != null);
          const single = own.length === 1;
          return (
            <span key={name} style={{ color: seriesColor(name) }}>
              <i
                aria-hidden="true"
                className={single ? styles.dot : undefined}
                data-projected={own.every((point) => point.tipo === "proyectado") || undefined}
              />
              <b>
                {layerLabel(name, true)}
                {single ? ` · ${own[0].anio}` : ""}
              </b>
            </span>
          );
        })}
      </figcaption>
    </figure>
  );
}
