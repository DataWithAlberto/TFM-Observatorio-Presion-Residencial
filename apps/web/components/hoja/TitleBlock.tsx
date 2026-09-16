import styles from "./title-block.module.css";

export type TitleBlockProps = {
  /** Qué se ve. Un titular en redonda, nunca en mayúsculas. */
  title: string;
  id?: string;
  /** Conmutador de resultado o nota, a la derecha del titular. */
  aside?: React.ReactNode;
  /** Frase calculada con los datos visibles. */
  reading: React.ReactNode;
  /** Clave de lectura, en gris, a continuación de la frase. */
  hint?: React.ReactNode;
  /** Fichas de filtros activos. */
  chips?: React.ReactNode;
};

/**
 * Encabeza cada vista: un titular que dice qué se ve y una frase de lectura
 * calculada con los datos que hay delante. Nunca texto valorativo.
 */
export default function TitleBlock({
  title,
  id = "titulo-de-vista",
  aside,
  reading,
  hint,
  chips,
}: TitleBlockProps) {
  return (
    <header className={styles.block}>
      <div className={styles.row}>
        <h1 id={id}>{title}</h1>
        {aside}
      </div>
      <p className={styles.reading}>
        <span className={styles.sentence}>{reading}</span>
        {hint && <span className={styles.hint}> {hint}</span>}
      </p>
      {chips}
    </header>
  );
}
