"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { IndexRow } from "@/lib/api";
import CategorySwatch from "@/components/hoja/CategorySwatch";
import { categoryLabel, fmt, placeName } from "@/lib/format";

import styles from "./relation-table.module.css";

export type SortKey = "ranking" | "nombre" | "provincia" | "comunidad_autonoma" | "score";

export type Sort = { key: SortKey; dir: 1 | -1 };

/**
 * La relación completa de municipios. Es el equivalente por teclado del mapa:
 * lo mismo que se puede pulsar sobre el territorio se puede recorrer aquí.
 */
export default function RelationTable({
  items,
  selected,
  onSelect,
  fichaHref,
  scoreLabel = "Puntuación",
  sort: controlledSort,
  onSortChange,
}: {
  items: IndexRow[];
  selected: string | null;
  onSelect: (codIne: string) => void;
  fichaHref: (codIne: string) => string;
  /** Cabecera de la columna numérica: el código del resultado (IPR-4 / IPR-5). */
  scoreLabel?: string;
  /** Orden gobernado desde fuera (la Relación lo guarda en la URL). */
  sort?: Sort;
  onSortChange?: (sort: Sort) => void;
}) {
  const [localSort, setLocalSort] = useState<Sort>({ key: "ranking", dir: 1 });
  const sort = controlledSort ?? localSort;
  const setSort = (next: Sort) => {
    if (onSortChange) onSortChange(next);
    else setLocalSort(next);
  };

  const rows = useMemo(() => {
    const sorted = [...items];
    sorted.sort((a, b) => {
      const left = a[sort.key];
      const right = b[sort.key];
      if (left == null) return 1;
      if (right == null) return -1;
      if (typeof left === "number" && typeof right === "number") {
        return (left - right) * sort.dir;
      }
      return String(left).localeCompare(String(right), "es") * sort.dir;
    });
    return sorted;
  }, [items, sort]);

  const header = (key: SortKey, label: string, numeric = false) => (
    <th
      scope="col"
      className={numeric ? styles.num : undefined}
      aria-sort={sort.key === key ? (sort.dir === 1 ? "ascending" : "descending") : undefined}
    >
      <button
        type="button"
        onClick={() =>
          setSort({
            key,
            dir: sort.key === key ? ((sort.dir * -1) as 1 | -1) : key === "score" ? -1 : 1,
          })
        }
      >
        {label}
        <i aria-hidden="true">{sort.key === key ? (sort.dir === 1 ? "↑" : "↓") : ""}</i>
      </button>
    </th>
  );

  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            {header("ranking", "Puesto", true)}
            {header("nombre", "Municipio")}
            {header("provincia", "Provincia")}
            {header("comunidad_autonoma", "Comunidad")}
            {header("score", scoreLabel, true)}
            <th scope="col">
              <span className={styles.static}>Nivel</span>
            </th>
            <th scope="col">
              <span className="visually-hidden">Ficha</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((item) => (
            <tr key={item.cod_ine} aria-selected={item.cod_ine === selected}>
              <td className={styles.num}>{item.ranking ?? "—"}</td>
              <td>
                <button
                  type="button"
                  className={styles.rowSelect}
                  onClick={() => onSelect(item.cod_ine)}
                >
                  {placeName(item.nombre)}
                </button>
              </td>
              <td>{placeName(item.provincia)}</td>
              <td>{item.comunidad_autonoma ?? "—"}</td>
              <td className={styles.num}>{fmt(item.score)}</td>
              <td>
                <span className={styles.level}>
                  <CategorySwatch category={item.categoria} />
                  {categoryLabel(item.categoria)}
                </span>
              </td>
              <td>
                <Link className={styles.rowLink} href={fichaHref(item.cod_ine)}>
                  Ficha
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
