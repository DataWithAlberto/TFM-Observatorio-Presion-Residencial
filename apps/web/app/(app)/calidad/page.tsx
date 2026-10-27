"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { Cartouche } from "@/components/hoja/Cartouche";
import { StatusLine } from "@/components/hoja/Status";
import TitleBlock from "@/components/hoja/TitleBlock";
import { getJSON, type LayerName, type QualitySummary } from "@/lib/api";
import { fmt, layerLabel, QUALITY_LEVELS } from "@/lib/format";

import styles from "./calidad.module.css";

/** Tipo de dato de cada factor, con el mismo vocabulario que la ficha. */
const TYPE_BY_LAYER: Partial<Record<LayerName, string>> = {
  asequibilidad: "Dato observado",
  turismo: "Dato observado",
  especulacion: "Dato observado",
  gentrificacion: "Estimación",
  riesgo_futuro: "Escenario futuro",
};

const DEFINITIONS = [
  {
    term: "Dato observado",
    what: "Procede directamente de una fuente o se calcula con datos históricos publicados.",
  },
  {
    term: "Estimación",
    what: "Aproxima una situación difícil de medir directamente, como el riesgo de desplazamiento vecinal.",
  },
  {
    term: "Escenario futuro",
    what: "Explora un posible riesgo posterior; no es un dato ya observado ni una predicción exacta.",
  },
];

export default function QualityPage() {
  const summary = useQuery({
    queryKey: ["quality-summary"],
    queryFn: () => getJSON<QualitySummary>("/api/v1/calidad/resumen"),
  });

  if (!summary.data) {
    return (
      <StatusLine
        loading={summary.isLoading}
        error={summary.isError}
        retry={() => summary.refetch()}
      >
        Cargando información sobre los datos…
      </StatusLine>
    );
  }

  const data = summary.data;

  return (
    <div className={styles.page}>
      <article className={styles.prose}>
        <TitleBlock
          title="Qué datos usamos y qué información falta"
          reading={`${data.municipios_observados} municipios tienen el resultado observado y ${data.municipios_prospectivos}, el resultado con riesgo futuro.`}
          hint="Cuando falta información la mostramos como no disponible: nunca la convertimos en cero."
        />

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Fuente de cada factor</h2>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">Factor</th>
                  <th scope="col">Fuente</th>
                  <th scope="col">Tipo de dato</th>
                </tr>
              </thead>
              <tbody>
                {data.sources.map((source) => (
                  <tr key={source.layer}>
                    <th scope="row">{layerLabel(source.layer)}</th>
                    <td>{source.name}</td>
                    <td>{TYPE_BY_LAYER[source.layer as LayerName] ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className={styles.block} id="procedencia">
          <h2 className={styles.blockTitle}>Procedencia y reutilización</h2>
          <p>Consulta los recursos utilizados, sus condiciones conocidas y las verificaciones pendientes.</p>
          <Link className={styles.link} href="/fuentes">Ver fuentes y condiciones</Link>
        </section>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Cobertura de los datos</h2>
          <ul className={styles.coverage}>
            <li>
              <span>Situación actual · IPR-4</span>
              <b className={styles.mono}>{fmt(data.cobertura_observada_media)} %</b>
              <i style={{ "--v": `${data.cobertura_observada_media}%` } as React.CSSProperties} />
              <small>
                {data.municipios_observados} de {data.municipios} municipios
              </small>
            </li>
            <li>
              <span>Con riesgo futuro · IPR-5</span>
              <b className={styles.mono}>{fmt(data.cobertura_prospectiva_media)} %</b>
              <i
                style={{ "--v": `${data.cobertura_prospectiva_media}%` } as React.CSSProperties}
              />
              <small>
                {data.municipios_prospectivos} de {data.municipios} municipios
              </small>
            </li>
          </ul>
          <p className={styles.note}>
            La cobertura es la media de factores con dato de cada municipio. Es la única
            que publica la API: no hay un desglose por factor.
          </p>
        </section>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Calidad del dato del IPR-4 (DQS)</h2>
          <p className={styles.dqsHeadline}>
            <b className={styles.mono}>{fmt(data.dqs_media)}</b> / 100 de media entre los{" "}
            {data.municipios} municipios.
          </p>
          <ul className={styles.levels}>
            {["alta", "media", "baja", "muy_baja", "sin_dato"].map((level) => (
              <li key={level}>
                <i data-level={level} aria-hidden="true" />
                <span>{QUALITY_LEVELS[level] ?? "Sin dato"}</span>
                <b className={styles.mono}>{data.dqs_niveles?.[level] ?? 0}</b>
              </li>
            ))}
          </ul>
          <p>
            El DQS evalúa cobertura y actualidad de los datos respecto al año del índice.
            La consistencia no se puntúa: no hay evidencia municipal trazable que lo
            permita. No mide presión residencial ni es una probabilidad de acierto.
          </p>
          <p>
            Pesos: cobertura 62,5 % y actualidad 37,5 %. Alta ≥ 85, media ≥ 70, baja ≥
            50, muy baja por debajo. Se admite un año de desfase sin penalización; a
            partir de ahí se descuentan 10 puntos por año. Solo se publica para el IPR-4
            observado: la calidad del escenario climático no se infiere de su año base.
          </p>
          <Link className={styles.link} href="/observatorio?capa=calidad">
            Ver el mapa de calidad del dato
          </Link>
        </section>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Qué significa cada tipo de dato</h2>
          <dl className={styles.definitions}>
            {DEFINITIONS.map((definition) => (
              <div key={definition.term}>
                <dt>{definition.term}</dt>
                <dd>{definition.what}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Los municipios sin riesgo futuro</h2>
          <p>
            Cádiz, San Fernando y Getxo sí tienen una puntuación completa para la
            situación actual. Como no disponemos del factor de riesgo futuro, no
            calculamos para ellos un resultado que podría inducir a error: aparecen como
            «—», nunca como cero.
          </p>
        </section>

        <Cartouche
          legend={false}
          cells={[
            { label: "Universo", value: `${data.municipios} municipios` },
            {
              label: "Con ambos resultados",
              value: `${data.municipios_prospectivos} de ${data.municipios}`,
            },
            { label: "Sin riesgo futuro", value: data.nulos_prospectivos },
            { label: "DQS medio", value: fmt(data.dqs_media) },
            { label: "Corte", value: 2023 },
            {
              label: "Fuentes",
              value: data.sources.map((source) => source.name).join(" · "),
              wide: true,
            },
          ]}
        />
      </article>
    </div>
  );
}
