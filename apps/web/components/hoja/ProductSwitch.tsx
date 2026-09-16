"use client";

import type { LayerName, Product } from "@/lib/api";
import { PRODUCT_NAMES, universe } from "@/lib/format";

import styles from "./product-switch.module.css";

/**
 * Conmutador entre los dos resultados. Solo aparece en la capa «Presión
 * total»: los factores sueltos forman parte de los dos, así que ahí se
 * sustituye por una nota. El universo va junto al código porque no coinciden:
 * el IPR-4 cubre 306 municipios y el IPR-5, 303.
 */
export default function ProductSwitch({
  layer,
  product,
  onChange,
}: {
  layer: LayerName;
  product: Product;
  onChange: (product: Product) => void;
}) {
  if (layer !== "ipr") {
    return (
      <p className={styles.note}>
        {layer === "riesgo_futuro"
          ? "Escenario climático 2041–2060 · 303 municipios"
          : layer === "calidad"
            ? "Calidad de las cuatro capas observadas · IPR-4"
            : "Este factor forma parte de los dos resultados"}
      </p>
    );
  }

  return (
    <div className={styles.group} role="group" aria-label="Tipo de resultado">
      {(["observado", "prospectivo"] as Product[]).map((option) => (
        <button
          key={option}
          type="button"
          className={styles.option}
          aria-pressed={product === option}
          onClick={() => onChange(option)}
        >
          <span>{PRODUCT_NAMES[option].name}</span>
          <small>
            {PRODUCT_NAMES[option].code} · {universe(option)}
          </small>
        </button>
      ))}
    </div>
  );
}
