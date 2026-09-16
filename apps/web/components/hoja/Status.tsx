import styles from "./status.module.css";

/**
 * Estados de carga y error como una línea de texto, sin esqueletos animados:
 * el movimiento distrae y aquí no aporta nada. El error dice qué ha pasado y
 * ofrece la única acción útil.
 */
export function StatusLine({
  loading,
  error,
  retry,
  children,
}: {
  loading?: boolean;
  error?: boolean;
  retry?: () => void;
  children?: React.ReactNode;
}) {
  if (loading) {
    return (
      <p className={styles.status} role="status">
        {children ?? "Cargando datos…"}
      </p>
    );
  }
  if (error) {
    return (
      <p className={`${styles.status} ${styles.error}`} role="alert">
        No se han podido cargar los datos.{" "}
        {retry && (
          <button type="button" onClick={retry}>
            Reintentar
          </button>
        )}
      </p>
    );
  }
  return null;
}

export default StatusLine;
