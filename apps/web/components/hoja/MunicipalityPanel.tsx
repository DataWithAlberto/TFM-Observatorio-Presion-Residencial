"use client";

import Link from "next/link";

import type { Detail, IndexRow } from "@/lib/api";
import CategorySwatch from "@/components/hoja/CategorySwatch";
import { categoryLabel, fmt, layerLabel, placeName, qualityLabel } from "@/lib/format";

import styles from "./side.module.css";

/**
 * Ficha breve del municipio elegido, en la columna lateral. Sustituye a la
 * lista de los diez primeros: una cosa cada vez.
 *
 * El percentil se trunca, nunca se redondea: decir que un municipio supera al
 * 100 % de los municipios sería falso mientras haya alguno por encima.
 */
export default function MunicipalityPanel({
  codIne,
  item,
  detail,
  universe,
  fichaHref,
  onBack,
}: {
  codIne: string;
  item: IndexRow | null;
  detail: Detail | null;
  universe: number;
  fichaHref: string;
  onBack: () => void;
}) {
  const name = placeName(item?.nombre ?? detail?.nombre);
  const province = placeName(item?.provincia ?? detail?.provincia);
  const region = item?.comunidad_autonoma ?? detail?.comunidad_autonoma;
  const category = item?.categoria ?? detail?.categoria;

  return (
    <section className={styles.fichaBox} aria-live="polite">
      <button type="button" className={styles.backLink} onClick={onBack}>
        ← Los diez primeros
      </button>
      <p className={styles.fichaCode}>
        Nº {item?.ranking ?? "—"} de {universe} ·{" "}
        <span className={styles.mono}>{codIne}</span>
      </p>
      <h2>{name}</h2>
      <p className={styles.fichaMeta}>
        {province} · {region}
      </p>

      <div className={styles.fichaScore}>
        <strong className={styles.figure}>{fmt(item?.score)}</strong>
        <span>
          <CategorySwatch category={category} size="large" />
          {categoryLabel(category)}
          {item?.percentil != null && (
            <small>Supera al {Math.floor(item.percentil)} % de los municipios</small>
          )}
        </span>
      </div>

      {item?.data_quality !== undefined && (
        <p className={styles.quality}>
          Calidad del dato · IPR-4:{" "}
          <b className={styles.figure}>{fmt(item.data_quality?.score)}</b> ·{" "}
          {qualityLabel(item.data_quality?.level)}
        </p>
      )}

      {detail && (
        <>
          <h3 className={styles.sideTitle}>Qué la compone</h3>
          <ul className={styles.factors}>
            {detail.capas.map((capa) => (
              <li key={capa.nombre}>
                <span>{layerLabel(capa.nombre, true)}</span>
                <b className={styles.figure}>{fmt(capa.score)}</b>
                <i style={{ "--v": `${capa.score ?? 0}%` } as React.CSSProperties} />
              </li>
            ))}
          </ul>
        </>
      )}

      <Link href={fichaHref} className={styles.fichaLink}>
        Abrir la hoja del municipio
      </Link>
    </section>
  );
}
