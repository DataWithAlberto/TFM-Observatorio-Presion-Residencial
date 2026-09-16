"use client";

import Link from "next/link";

import type { IndexRow } from "@/lib/api";
import { fmt, placeName } from "@/lib/format";

import styles from "./side.module.css";

/**
 * Los diez primeros de la vista. Es lo que ocupa la columna lateral mientras
 * no hay municipio elegido: o esto, o su ficha, nunca las dos cosas.
 */
export default function TopTen({
  items,
  loading,
  title,
  listHref,
  onSelect,
}: {
  items: IndexRow[];
  loading: boolean;
  title: string;
  listHref: string;
  onSelect: (codIne: string) => void;
}) {
  return (
    <section className={styles.topBox}>
      <h2 className={styles.sideTitle}>{title}</h2>
      <ol className={styles.topList}>
        {items.slice(0, 10).map((row) => (
          <li key={row.cod_ine}>
            <button type="button" onClick={() => onSelect(row.cod_ine)}>
              <span className={styles.rank}>
                {String(row.ranking ?? "—").padStart(2, "0")}
              </span>
              <span>
                <b>{placeName(row.nombre)}</b>
                <small>{placeName(row.provincia)}</small>
              </span>
              <strong className={styles.figure}>{fmt(row.score)}</strong>
            </button>
          </li>
        ))}
      </ol>
      {!loading && items.length === 0 && (
        <p className={styles.empty}>Ningún municipio cumple los filtros.</p>
      )}
      <Link href={listHref} className={styles.moreLink}>
        Ver la relación completa ({items.length})
      </Link>
      <p className={styles.hint}>
        Pulsa un municipio en el mapa o en la lista para ver su detalle.
      </p>
    </section>
  );
}
