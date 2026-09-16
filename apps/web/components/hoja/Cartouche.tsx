import CategoryScale from "@/components/hoja/CategoryScale";

import styles from "./cartouche.module.css";

export type CartoucheCell = {
  label: string;
  value: React.ReactNode;
  /** Ocupa las dos columnas del cajetín completo. */
  wide?: boolean;
};

/**
 * Franja de metadatos al pie de la hoja: el cajetín reducido a una línea.
 * Los metadatos están presentes, pero no son los protagonistas.
 */
export function CartoucheStrip({
  cells,
  sources = "INE · Ministerio de Vivienda · Catastro · Copernicus",
}: {
  cells: CartoucheCell[];
  sources?: React.ReactNode;
}) {
  return (
    <footer className={styles.strip} aria-label="Datos de la hoja">
      {cells.map((cell) => (
        <span key={cell.label}>
          <small>{cell.label}</small>
          <span className={styles.value}>{cell.value}</span>
        </span>
      ))}
      <span className={styles.sources}>
        <small>Fuentes</small>
        <span className={styles.value}>{sources}</span>
      </span>
    </footer>
  );
}

/**
 * Cajetín completo, en rejilla de dos columnas. Solo lo lleva la ficha
 * municipal y las páginas de lectura, donde los metadatos sí son el contenido.
 */
export function Cartouche({
  cells,
  legend = true,
  title = "Observatorio de presión residencial",
}: {
  cells: CartoucheCell[];
  legend?: boolean;
  title?: string;
}) {
  return (
    <div className={styles.cart}>
      <div className={`${styles.cell} ${styles.wide} ${styles.cartTitle}`}>
        <small>Título</small>
        <b>{title}</b>
      </div>
      {cells.map((cell) => (
        <div
          key={cell.label}
          className={`${styles.cell}${cell.wide ? ` ${styles.wide}` : ""}`}
        >
          <small>{cell.label}</small>
          <b>{cell.value}</b>
        </div>
      ))}
      {legend && (
        <div className={`${styles.cell} ${styles.wide}`}>
          <small>Leyenda · quintiles de 61–62 municipios</small>
          <CategoryScale />
        </div>
      )}
    </div>
  );
}
