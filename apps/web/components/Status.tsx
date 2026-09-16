import styles from "./hoja/status.module.css";

/**
 * Estados compartidos por las páginas, con el tratamiento de «Hoja catastral»:
 * una línea de texto en el sitio del contenido, sin esqueletos ni animaciones.
 */
export function Loading({ label = "Cargando datos…" }: { label?: string }) {
  return (
    <p className={styles.status} role="status" aria-live="polite">
      {label}
    </p>
  );
}

export function ErrorState({
  message = "No se han podido cargar los datos.",
  retry,
}: {
  message?: string;
  retry?: () => void;
}) {
  return (
    <p className={`${styles.status} ${styles.error}`} role="alert">
      {message}{" "}
      {retry && (
        <button type="button" onClick={retry}>
          Reintentar
        </button>
      )}
    </p>
  );
}

export function Empty({ message }: { message: string }) {
  return (
    <p className={styles.status} role="status">
      {message}
    </p>
  );
}
