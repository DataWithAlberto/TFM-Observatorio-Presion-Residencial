"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense } from "react";

import { Cartouche } from "@/components/hoja/Cartouche";
import CategorySwatch from "@/components/hoja/CategorySwatch";
import DataQualityBlock from "@/components/hoja/DataQualityBlock";
import HomogeneousHistory from "@/components/hoja/HomogeneousHistory";
import DotPlot from "@/components/hoja/DotPlot";
import FactorTable from "@/components/hoja/FactorTable";
import LineChart from "@/components/hoja/LineChart";
import LocatorMap from "@/components/hoja/LocatorMap";
import { StatusLine } from "@/components/hoja/Status";
import type { Detail, Product } from "@/lib/api";
import {
  categoryLabel,
  fmt,
  placeName,
  PRODUCT_NAMES,
  qualityLabel,
  universe,
} from "@/lib/format";
import { useFichaParams, useMunicipality } from "@/lib/useExplorer";

import styles from "./municipio.module.css";

/** Resumen construido con los campos que devuelve la API, sin interpretarlos. */
function Summary({ detail, product }: { detail: Detail; product: Product }) {
  if (detail.score == null) {
    return (
      <p className={styles.summary}>
        No hay puntuación de {placeName(detail.nombre)} para este resultado: falta el
        dato de riesgo futuro y no se ha rellenado con una estimación.
      </p>
    );
  }
  return (
    <p className={styles.summary}>
      {placeName(detail.nombre)} obtiene {fmt(detail.score)} sobre 100: presión{" "}
      {categoryLabel(detail.categoria).toLowerCase()}. Ocupa el puesto{" "}
      {detail.ranking ?? "—"} de {universe(product)}
      {detail.percentil == null
        ? "."
        : ` y supera al ${Math.floor(detail.percentil)} % de los municipios estudiados.`}
    </p>
  );
}

function Ficha() {
  const { codIne } = useParams<{ codIne: string }>();
  const { product, backHref, productHref } = useFichaParams("/observatorio");
  const { detail, history, benchmarks } = useMunicipality(codIne, product, {
    history: true,
    benchmarks: true,
  });

  const data = detail.data?.cod_ine === codIne ? detail.data : null;
  const total = universe(product);

  if (!data) {
    return (
      <StatusLine
        loading={detail.isLoading}
        error={detail.isError}
        retry={() => detail.refetch()}
      >
        Cargando la hoja del municipio…
      </StatusLine>
    );
  }

  const missingProspective = product === "prospectivo" && data.score == null;

  return (
    <div className={styles.page}>
      <div className={styles.main}>
        <nav className={styles.crumbs}>
          <Link href={backHref}>← Volver al mapa</Link>
        </nav>

        <p className={styles.kicker}>
          Hoja municipal · Nº {String(data.ranking ?? "—").padStart(3, "0")} de {total}
        </p>
        <h1 className={styles.title}>{placeName(data.nombre)}</h1>
        <p className={styles.meta}>
          Código INE <span className={styles.mono}>{data.cod_ine}</span> ·{" "}
          {placeName(data.provincia)} · {data.comunidad_autonoma}
        </p>

        <div className={styles.productTabs} role="group" aria-label="Tipo de resultado">
          {(["observado", "prospectivo"] as Product[]).map((option) => (
            <Link
              key={option}
              href={productHref(codIne, option)}
              aria-current={product === option ? "page" : undefined}
              scroll={false}
            >
              {PRODUCT_NAMES[option].code} · {PRODUCT_NAMES[option].name}
            </Link>
          ))}
        </div>

        {missingProspective && (
          <p className={styles.notice} role="status">
            No disponemos del dato de riesgo futuro para este municipio y no lo hemos
            rellenado con una estimación.
          </p>
        )}

        <Summary detail={data} product={product} />

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Cuadro de factores</h2>
          <FactorTable detail={data} />
        </section>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Situación frente al entorno</h2>
          {benchmarks.data ? (
            <>
              <DotPlot detail={data} benchmarks={benchmarks.data} />
              <div className={styles.tableWrap}>
                <table className={styles.benchTable}>
                  <thead>
                    <tr>
                      <th scope="col">Zona</th>
                      <th scope="col" className={styles.num}>
                        Puntuación media
                      </th>
                      <th scope="col" className={styles.num}>
                        Diferencia con {placeName(data.nombre)}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {benchmarks.data.map((item) => (
                      <tr key={item.nivel}>
                        <td>{placeName(item.territorio)}</td>
                        <td className={styles.num}>{fmt(item.score)}</td>
                        <td className={styles.num}>
                          {item.score == null || data.score == null
                            ? "—"
                            : `${data.score - item.score >= 0 ? "+" : "−"}${fmt(
                                Math.abs(data.score - item.score),
                              )}`}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <StatusLine
              loading={benchmarks.isLoading}
              error={benchmarks.isError}
              retry={() => benchmarks.refetch()}
            />
          )}
        </section>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Evolución comparable · IPR-4 histórico 2020–2023</h2>
          <HomogeneousHistory codIne={codIne} />
        </section>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Series originales de los factores</h2>
          <p className={styles.blockNote}>
            Cada factor con los años que tiene, en posición dentro de su año: 100 es el
            municipio con más presión de los estudiados ese año y 0 el que menos. No es
            la puntuación del cuadro de factores, que el punto muestra aparte. Los
            universos cambian de un año a otro, así que estas series no son comparables
            entre sí como el panel anterior, y lo que queda a la derecha del corte es
            dato posterior al índice publicado.
          </p>
          {history.data ? (
            <LineChart points={history.data} cutYear={data.anio} />
          ) : (
            <StatusLine
              loading={history.isLoading}
              error={history.isError}
              retry={() => history.refetch()}
            />
          )}
        </section>
      </div>

      <aside className={styles.side}>
        <div className={styles.bigScore}>
          <small className={styles.mono}>{PRODUCT_NAMES[product].code}</small>
          <strong>{fmt(data.score)}</strong>
          <span>
            <CategorySwatch category={data.categoria} size="large" />
            {data.score == null
              ? "Sin dato"
              : `Presión ${categoryLabel(data.categoria).toLowerCase()}`}
          </span>
        </div>

        <DataQualityBlock quality={data.data_quality} compact />

        <div className={styles.locator}>
          <LocatorMap codIne={codIne} product={product} />
        </div>

        <Cartouche
          cells={[
            { label: "Puesto", value: `${data.ranking ?? "—"} de ${total}` },
            {
              label: "Supera al",
              value: data.percentil == null ? "—" : `${Math.floor(data.percentil)} %`,
            },
            { label: "Corte", value: data.anio },
            {
              label: "Factores con dato",
              value: `${data.capas_validas} de ${product === "prospectivo" ? 5 : 4}`,
            },
            {
              label: "Calidad del dato",
              value:
                data.data_quality?.score == null
                  ? "—"
                  : `${fmt(data.data_quality.score)} · ${qualityLabel(data.data_quality.level)}`,
            },
            { label: "Método", value: `versión ${data.version_metodologia}` },
            { label: "Escala", value: "0 menor · 100 mayor" },
            {
              label: "Nota",
              value:
                "El IPR-5 añade el escenario climático 2041–2060; no es un dato de 2023.",
              wide: true,
            },
          ]}
        />
      </aside>
    </div>
  );
}

export default function MunicipalityPage() {
  return (
    <Suspense
      fallback={<StatusLine loading>Cargando la hoja del municipio…</StatusLine>}
    >
      <Ficha />
    </Suspense>
  );
}
