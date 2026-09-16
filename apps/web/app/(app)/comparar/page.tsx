"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { ComparisonChart } from "@/components/Chart";
import { CartoucheStrip } from "@/components/hoja/Cartouche";
import CategorySwatch from "@/components/hoja/CategorySwatch";
import { StatusLine } from "@/components/hoja/Status";
import TitleBlock from "@/components/hoja/TitleBlock";
import {
  type Detail,
  getJSON,
  type Municipality,
  type Product,
} from "@/lib/api";
import {
  categoryLabel,
  fmt,
  layerLabel,
  placeName,
  PRODUCT_NAMES,
  universe,
} from "@/lib/format";

import styles from "./comparar.module.css";

/**
 * Frase de lectura: una comparación directa de los datos cargados. Con dos
 * municipios se cuenta en cuántos factores gana uno; con más, se da el rango.
 */
function readingFor(items: Detail[]): string {
  const scored = items.filter((item): item is Detail & { score: number } => item.score != null);
  if (scored.length < 2) {
    return scored.length === 1
      ? `Solo ${placeName(scored[0].nombre)} tiene puntuación en este resultado.`
      : "No hay puntuaciones disponibles para los municipios elegidos.";
  }

  if (scored.length === 2) {
    const [a, b] = [...scored].sort((x, y) => y.score - x.score);
    const factors = a.capas.filter((capa) => {
      const other = b.capas.find((item) => item.nombre === capa.nombre);
      return capa.score != null && other?.score != null && capa.score > other.score;
    }).length;
    const total = a.capas.filter((capa) => {
      const other = b.capas.find((item) => item.nombre === capa.nombre);
      return capa.score != null && other?.score != null;
    }).length;
    return `${placeName(a.nombre)} supera a ${placeName(b.nombre)} en ${factors} de ${total} factores.`;
  }

  const ordered = [...scored].sort((x, y) => y.score - x.score);
  const top = ordered[0];
  const bottom = ordered[ordered.length - 1];
  return `${placeName(top.nombre)} obtiene ${fmt(top.score)} y ${placeName(
    bottom.nombre,
  )}, ${fmt(bottom.score)}: ${fmt(top.score - bottom.score)} puntos de diferencia.`;
}

function Compare() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const product: Product =
    searchParams.get("producto") === "prospectivo" ? "prospectivo" : "observado";
  const codes = [...new Set(searchParams.getAll("municipio"))].slice(0, 4);
  const selectedCodes =
    codes.length === 0 && !searchParams.has("municipio") ? ["28079", "08019"] : codes;

  const municipalities = useQuery({
    queryKey: ["municipalities"],
    queryFn: () => getJSON<Municipality[]>("/api/v1/municipios"),
    staleTime: 300_000,
  });
  const comparison = useQuery({
    queryKey: ["comparison", selectedCodes, product],
    queryFn: () => {
      const query = new URLSearchParams({ producto: product });
      selectedCodes.forEach((code) => query.append("cod_ine", code));
      return getJSON<{ items: Detail[] }>(`/api/v1/comparacion?${query}`);
    },
    enabled: selectedCodes.length >= 2,
  });

  const setCodes = (nextCodes: string[], nextProduct = product) => {
    const query = new URLSearchParams({ producto: nextProduct });
    nextCodes
      .filter(Boolean)
      .slice(0, 4)
      .forEach((code) => query.append("municipio", code));
    router.replace(`/comparar?${query}`, { scroll: false });
  };

  const options = municipalities.data ?? [];
  const items = comparison.data?.items ?? [];
  const layerNames = items[0]?.capas.map((layer) => layer.nombre) ?? [];

  return (
    <div className={styles.compare}>
      <div className={styles.controls}>
        {[0, 1, 2, 3].map((position) => (
          <label className={styles.field} key={position}>
            <span>
              Municipio {position + 1}
              {position > 1 ? " (opcional)" : ""}
            </span>
            <select
              value={selectedCodes[position] ?? ""}
              onChange={(event) => {
                const next = [...selectedCodes];
                if (event.target.value) next[position] = event.target.value;
                else next.splice(position, 1);
                setCodes([...new Set(next)]);
              }}
            >
              <option value="">
                {position < 2 ? "Selecciona un municipio" : "Ninguno"}
              </option>
              {options.map((municipality) => (
                <option
                  key={municipality.cod_ine}
                  value={municipality.cod_ine}
                  disabled={
                    selectedCodes.includes(municipality.cod_ine) &&
                    selectedCodes[position] !== municipality.cod_ine
                  }
                >
                  {placeName(municipality.nombre)} · {placeName(municipality.provincia)}
                </option>
              ))}
            </select>
          </label>
        ))}

        <div className={styles.productSwitch} role="group" aria-label="Tipo de resultado">
          {(["observado", "prospectivo"] as Product[]).map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={product === option}
              onClick={() => setCodes(selectedCodes, option)}
            >
              <span>{PRODUCT_NAMES[option].name}</span>
              <small>
                {PRODUCT_NAMES[option].code} · {universe(option)}
              </small>
            </button>
          ))}
        </div>
      </div>

      <section className={styles.main} aria-labelledby="titulo-de-vista">
        <TitleBlock
          title="Compara entre 2 y 4 municipios"
          reading={
            comparison.isLoading || items.length < 2
              ? "Elige al menos dos municipios distintos."
              : readingFor(items)
          }
          hint="Los factores se dibujan en la misma escala, de 0 a 100."
        />

        {comparison.isLoading || comparison.isError ? (
          <StatusLine
            loading={comparison.isLoading}
            error={comparison.isError}
            retry={() => comparison.refetch()}
          >
            Cargando la comparación…
          </StatusLine>
        ) : items.length < 2 ? (
          <p className={styles.empty}>Selecciona al menos dos municipios distintos.</p>
        ) : (
          <div className={styles.content}>
            {/* Una hoja pequeña por municipio: la comparación se lee en vertical. */}
            <ul className={styles.sheets}>
              {items.map((item) => (
                <li key={item.cod_ine} className={styles.sheet}>
                  <p className={styles.rank}>
                    {item.ranking == null
                      ? "Sin puesto"
                      : `Nº ${item.ranking} de ${universe(product)}`}
                  </p>
                  <h2>{placeName(item.nombre)}</h2>
                  <p className={styles.place}>{placeName(item.provincia)}</p>

                  <strong className={styles.score}>{fmt(item.score)}</strong>
                  <p className={styles.category}>
                    <CategorySwatch category={item.categoria} />
                    {item.score == null ? "No se puede comparar" : categoryLabel(item.categoria)}
                  </p>

                  <ul className={styles.factors}>
                    {item.capas.map((capa) => (
                      <li key={capa.nombre}>
                        <span>{layerLabel(capa.nombre, true)}</span>
                        <b>{fmt(capa.score)}</b>
                        <i style={{ "--v": `${capa.score ?? 0}%` } as React.CSSProperties} />
                      </li>
                    ))}
                  </ul>

                  <Link
                    className={styles.sheetLink}
                    href={`/municipio/${item.cod_ine}?producto=${product}`}
                  >
                    Abrir la hoja del municipio
                  </Link>
                </li>
              ))}
            </ul>

            <section className={styles.block}>
              <h2 className={styles.blockTitle}>Comparación por factores</h2>
              <ComparisonChart items={items} />
            </section>

            <section className={styles.block}>
              <h2 className={styles.blockTitle}>Cifras</h2>
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th scope="col">Factor</th>
                      {items.map((item) => (
                        <th scope="col" key={item.cod_ine} className={styles.num}>
                          {placeName(item.nombre)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <th scope="row">Puntuación total</th>
                      {items.map((item) => (
                        <td key={item.cod_ine} className={styles.num}>
                          {fmt(item.score)}
                        </td>
                      ))}
                    </tr>
                    {layerNames.map((layerName) => (
                      <tr key={layerName}>
                        <th scope="row">{layerLabel(layerName)}</th>
                        {items.map((item) => (
                          <td key={item.cod_ine} className={styles.num}>
                            {fmt(
                              item.capas.find((layer) => layer.nombre === layerName)?.score,
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        )}
      </section>

      <CartoucheStrip
        cells={[
          { label: "Resultado", value: PRODUCT_NAMES[product].code },
          { label: "Corte", value: 2023 },
          { label: "Municipios", value: `${items.length} de ${universe(product)}` },
          { label: "Referencia", value: "WGS84" },
        ]}
      />
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<StatusLine loading>Cargando la comparación…</StatusLine>}>
      <Compare />
    </Suspense>
  );
}
