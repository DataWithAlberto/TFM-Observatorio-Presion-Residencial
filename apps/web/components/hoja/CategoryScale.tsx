import { CATEGORIES } from "@/lib/format";

import styles from "./category-scale.module.css";

/**
 * Escala de las cinco categorías (quintiles de 61–62 municipios) con los
 * colores de la rampa secuencial. La usan la leyenda del mapa y el cajetín.
 */
export default function CategoryScale() {
  return (
    <ul className={styles.scale}>
      {CATEGORIES.map((category, index) => (
        <li key={category.id}>
          <i data-step={index + 1} aria-hidden="true" />
          <span>{category.label}</span>
        </li>
      ))}
    </ul>
  );
}
