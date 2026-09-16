"use client";

import { useRef } from "react";

import type { LayerName } from "@/lib/api";
import { LAYERS } from "@/lib/format";

import styles from "./layer-tabs.module.css";

/**
 * Las seis capas como pestañas. Es un `radiogroup`: se recorre con las flechas
 * y solo la activa entra en el orden de tabulación, de modo que el teclado no
 * tiene que atravesar seis controles para llegar al mapa.
 */
export default function LayerTabs({
  value,
  onChange,
  label = "Qué quieres ver",
}: {
  value: LayerName;
  onChange: (layer: LayerName) => void;
  label?: string;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const move = (from: number, step: number) => {
    const next = (from + step + LAYERS.length) % LAYERS.length;
    onChange(LAYERS[next].id);
    refs.current[next]?.focus();
  };

  return (
    <div className={styles.tabs} role="radiogroup" aria-label={label}>
      {LAYERS.map((layer, index) => (
        <button
          key={layer.id}
          ref={(element) => {
            refs.current[index] = element;
          }}
          type="button"
          role="radio"
          aria-checked={layer.id === value}
          tabIndex={layer.id === value ? 0 : -1}
          className={styles.tab}
          onClick={() => onChange(layer.id)}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown" || event.key === "ArrowRight") {
              event.preventDefault();
              move(index, 1);
            } else if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
              event.preventDefault();
              move(index, -1);
            }
          }}
        >
          {layer.short}
        </button>
      ))}
    </div>
  );
}
