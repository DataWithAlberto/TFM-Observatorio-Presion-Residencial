import { categoryIndex } from "@/lib/format";

import styles from "./category-swatch.module.css";

/**
 * Cuadrado del color de la categoría. El color sale de la rampa de
 * `tokens.css` a través del identificador que devuelve la API, así que un
 * municipio sin dato queda en gris en lugar de fingir un valor bajo.
 */
export default function CategorySwatch({
  category,
  size = "small",
}: {
  category: string | null | undefined;
  size?: "small" | "large";
}) {
  const step = categoryIndex(category) + 1;
  return (
    <i
      className={`${styles.swatch} ${size === "large" ? styles.large : ""}`}
      data-step={step > 0 ? step : undefined}
      aria-hidden="true"
    />
  );
}
