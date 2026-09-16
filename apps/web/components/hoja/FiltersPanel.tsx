"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";

import { placeName } from "@/lib/format";

import styles from "./filters-panel.module.css";

/** Reparte los diez tramos del histograma entre los cinco pasos de la rampa. */
function rampStep(binIndex: number) {
  return Math.min(5, Math.floor(binIndex / 2) + 1);
}

function ScoreRange({
  min,
  max,
  scores,
  onCommit,
}: {
  min: number;
  max: number;
  scores: number[];
  onCommit: (min: number, max: number) => void;
}) {
  const [local, setLocal] = useState({ min, max });
  const [synced, setSynced] = useState({ min, max });
  const timer = useRef<number | undefined>(undefined);

  // Si la URL cambia desde fuera (p. ej. «Quitar filtros»), se adopta el rango.
  if (synced.min !== min || synced.max !== max) {
    setSynced({ min, max });
    setLocal({ min, max });
  }
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const commit = (next: { min: number; max: number }) => {
    setLocal(next);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => onCommit(next.min, next.max), 260);
  };

  const bins = useMemo(() => {
    if (!scores.length) return null;
    const counts = Array<number>(10).fill(0);
    scores.forEach((score) => {
      counts[Math.min(9, Math.floor(score / 10))] += 1;
    });
    const top = Math.max(...counts, 1);
    return counts.map((count) => ({ count, height: count / top }));
  }, [scores]);

  return (
    <div className={styles.range}>
      <div className={styles.rangeHead}>
        <span>Puntuación</span>
        <output>
          {local.min} – {local.max}
        </output>
      </div>
      {bins && (
        <div className={styles.hist} aria-hidden="true">
          {bins.map((bin, index) => (
            <i
              key={index}
              data-step={rampStep(index)}
              data-out={
                index * 10 + 10 <= local.min || index * 10 >= local.max || undefined
              }
              style={{ "--h": bin.height } as React.CSSProperties}
              title={`${index * 10}–${index * 10 + 10}: ${bin.count}`}
            />
          ))}
        </div>
      )}
      <div className={styles.sliders}>
        <label>
          <span>Mínima</span>
          <input
            type="range"
            min={0}
            max={100}
            step={1}
            value={local.min}
            onChange={(event) =>
              commit({ min: Math.min(Number(event.target.value), local.max), max: local.max })
            }
          />
        </label>
        <label>
          <span>Máxima</span>
          <input
            type="range"
            min={0}
            max={100}
            step={1}
            value={local.max}
            onChange={(event) =>
              commit({ min: local.min, max: Math.max(Number(event.target.value), local.min) })
            }
          />
        </label>
      </div>
    </div>
  );
}

export type FiltersPanelProps = {
  ccaa: string;
  province: string;
  regions: string[];
  provinces: string[];
  /**
   * Rango de puntuación con histograma. Se omite en las páginas que filtran
   * por otra magnitud, como la diferencia entre resultados de Riesgo futuro.
   */
  score?: { min: number; max: number; values: number[] };
  /** Número de filtros activos que se muestran en el contador del botón. */
  count: number;
  onChange: (changes: Record<string, string | null>) => void;
  onClear: () => void;
  /** Controles extra que solo tienen sentido en algunas páginas (p. ej. «Ordenar»). */
  children?: React.ReactNode;
};

/**
 * Botón «Filtros» y su panel. Los filtros viven plegados para que la pantalla
 * muestre una sola cosa; los que están puestos se ven como fichas junto al
 * titular, no aquí dentro.
 */
export default function FiltersPanel({
  ccaa,
  province,
  regions,
  provinces,
  score,
  count,
  onChange,
  onClear,
  children,
}: FiltersPanelProps) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  return (
    <div className={styles.wrap}>
      <button
        type="button"
        className={styles.button}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
      >
        Filtros
        {count > 0 && <b>{count}</b>}
      </button>
      {open && (
        <div id={panelId} className={styles.panel}>
          <label className={styles.field}>
            <span>Comunidad autónoma</span>
            <select
              value={ccaa}
              onChange={(event) => onChange({ ccaa: event.target.value, provincia: null })}
            >
              <option value="">Todas</option>
              {regions.map((region) => (
                <option key={region} value={region}>
                  {region}
                </option>
              ))}
            </select>
          </label>

          <label className={styles.field}>
            <span>Provincia</span>
            <select
              value={province}
              disabled={!ccaa}
              onChange={(event) => onChange({ provincia: event.target.value })}
            >
              <option value="">{ccaa ? "Todas" : "Elige antes una comunidad"}</option>
              {provinces.map((value) => (
                <option key={value} value={value}>
                  {placeName(value)}
                </option>
              ))}
            </select>
          </label>

          {score && (
            <ScoreRange
              min={score.min}
              max={score.max}
              scores={score.values}
              onCommit={(next, top) =>
                onChange({
                  min: next > 0 ? String(next) : null,
                  max: top < 100 ? String(top) : null,
                })
              }
            />
          )}

          {children}

          <div className={styles.actions}>
            <button type="button" onClick={onClear}>
              Quitar filtros
            </button>
            <button type="button" onClick={() => setOpen(false)}>
              Listo
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
