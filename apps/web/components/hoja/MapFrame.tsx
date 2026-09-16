import CategoryScale from "@/components/hoja/CategoryScale";

import styles from "./map-frame.module.css";

/**
 * Marco del mapa con los elementos que van encima: flecha de norte y leyenda.
 * La leyenda vive sobre el mapa, junto a lo que explica, no en un lateral.
 */
export default function MapFrame({
  legendTitle,
  legend,
  children,
}: {
  /** Título de la leyenda de quintiles; si falta, se pasa `legend` a medida. */
  legendTitle?: string;
  legend?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className={styles.frame}>
      {children}
      <span className={styles.north} aria-hidden="true">
        <i />N
      </span>
      {legend ?? (
        <div className={styles.legend} aria-label="Leyenda">
          <small>{legendTitle}</small>
          <CategoryScale />
        </div>
      )}
    </div>
  );
}
