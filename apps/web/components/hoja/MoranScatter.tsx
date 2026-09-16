"use client";

import { useEffect, useRef, useState } from "react";

import type { SpatialYear } from "@/lib/spatial";
import { placeName } from "@/lib/format";

import styles from "./moran-scatter.module.css";

/**
 * Diagrama de Moran en SVG: cada punto es un municipio evaluable, con su IPR
 * estandarizado frente al de sus vecinos. La pendiente de la recta es la I de
 * Moran. Los cuadrantes describen; la significación local la decide LISA.
 */
export default function MoranScatter({
  data,
  height = 380,
}: {
  data: SpatialYear;
  height?: number;
}) {
  const ref = useRef<HTMLElement>(null);
  const [width, setWidth] = useState(560);

  useEffect(() => {
    if (!ref.current) return;
    const observer = new ResizeObserver(([entry]) =>
      setWidth(Math.max(280, Math.round(entry.contentRect.width))),
    );
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  const points = data.items.filter(
    (item) => item.eligible && item.standardized_ipr != null && item.spatial_lag != null,
  );
  const limit = Math.ceil(
    Math.max(
      1,
      ...points.flatMap((item) => [
        Math.abs(item.standardized_ipr as number),
        Math.abs(item.spatial_lag as number),
      ]),
    ),
  );
  const result = data.global_result;
  const pad = { l: 44, r: 16, t: 18, b: 40 };
  const x = (value: number) =>
    pad.l + ((value + limit) / (2 * limit)) * (width - pad.l - pad.r);
  const y = (value: number) =>
    pad.t + (1 - (value + limit) / (2 * limit)) * (height - pad.t - pad.b);

  return (
    <figure className={styles.chart} ref={ref}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: "100%", height }}
        role="img"
        aria-label={`Diagrama de Moran ${result.anio}: pendiente ${result.moran_i.toFixed(3)}`}
      >
        <line className={styles.axis} x1={pad.l} x2={width - pad.r} y1={y(0)} y2={y(0)} />
        <line className={styles.axis} x1={x(0)} x2={x(0)} y1={pad.t} y2={height - pad.b} />
        {[-limit, 0, limit].map((tick) => (
          <g key={tick}>
            <text className={styles.tick} x={x(tick)} y={height - pad.b + 16} textAnchor="middle">
              {tick}
            </text>
            <text className={styles.tick} x={pad.l - 8} y={y(tick) + 4} textAnchor="end">
              {tick}
            </text>
          </g>
        ))}
        <text className={styles.quadrant} x={pad.l + 8} y={pad.t + 14}>LH</text>
        <text className={styles.quadrant} x={width - pad.r - 8} y={pad.t + 14} textAnchor="end">HH</text>
        <text className={styles.quadrant} x={pad.l + 8} y={height - pad.b - 8}>LL</text>
        <text className={styles.quadrant} x={width - pad.r - 8} y={height - pad.b - 8} textAnchor="end">HL</text>

        {points.map((item) => (
          <circle
            key={item.cod_ine}
            className={styles.dot}
            data-cluster={item.cluster_type}
            cx={x(item.standardized_ipr as number)}
            cy={y(item.spatial_lag as number)}
            r={3.5}
          >
            <title>{`${placeName(item.nombre)} · IPR ${item.ipr.toFixed(1)} · ${item.cluster_type}`}</title>
          </circle>
        ))}

        <line
          className={styles.slope}
          x1={x(-limit)}
          y1={y(-limit * result.moran_i)}
          x2={x(limit)}
          y2={y(limit * result.moran_i)}
        />
        <text className={styles.axisName} x={(pad.l + width - pad.r) / 2} y={height - 4} textAnchor="middle">
          IPR estandarizado
        </text>
        <text
          className={styles.axisName}
          transform={`translate(12 ${(pad.t + height - pad.b) / 2}) rotate(-90)`}
          textAnchor="middle"
        >
          Media de los vecinos
        </text>
      </svg>
      <figcaption className={styles.caption}>
        Pendiente = I de Moran = {result.moran_i.toFixed(3)} · {points.length} municipios
        evaluables. Los cuadrantes son descriptivos; no implican significación LISA.
      </figcaption>
    </figure>
  );
}
