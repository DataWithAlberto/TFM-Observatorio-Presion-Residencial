import styles from "./sheet.module.css";

/**
 * Marco de doble filete que envuelve cada página, como una hoja cartográfica.
 *
 * La hoja mide al menos el alto de la ventana y reparte sus filas en cabecera
 * y cuerpo. El explorador llena ese cuerpo con un mapa que se encoge y una
 * columna con scroll propio, así que la página no llega a desbordar; las
 * páginas de lectura simplemente crecen por debajo del mínimo.
 *
 * Todos los hijos directos llevan `min-width: 0` para que ninguna rejilla se
 * ensanche con su contenido.
 */
export default function Sheet({ children }: { children: React.ReactNode }) {
  return (
    <div className={styles.page}>
      <div className={styles.sheet}>{children}</div>
    </div>
  );
}

/** Cuerpo de la hoja. Se separa para que el layout no tenga que estilarlo. */
export function SheetBody({ children }: { children: React.ReactNode }) {
  return (
    <main id="contenido" className={styles.body}>
      {children}
    </main>
  );
}
