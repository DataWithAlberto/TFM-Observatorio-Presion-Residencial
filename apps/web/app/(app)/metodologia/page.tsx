"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { Cartouche } from "@/components/hoja/Cartouche";
import TitleBlock from "@/components/hoja/TitleBlock";
import { getJSON, type LayerName, type QualitySummary } from "@/lib/api";
import { LAYERS, layerLabel } from "@/lib/format";

import styles from "./metodologia.module.css";

/** Peso de cada factor en el IPR-5 y qué mide, en palabras de vecino. */
const FACTORS: Partial<Record<LayerName, { weight: string; type: string; what: string }>> = {
  ipr: { weight: "—", type: "—", what: "" },
  asequibilidad: {
    weight: "30 %",
    type: "Dato observado",
    what: "Compara el precio de la vivienda con los ingresos de los hogares.",
  },
  turismo: {
    weight: "20 %",
    type: "Dato observado",
    what: "Mide cuántas viviendas turísticas hay en relación con la población y el tamaño del municipio.",
  },
  especulacion: {
    weight: "20 %",
    type: "Dato observado",
    what: "Observa cambios rápidos en compraventas y precios, sobre todo cuando los precios se alejan de los ingresos.",
  },
  gentrificacion: {
    weight: "15 %",
    type: "Estimación",
    what: "Estima si los cambios sociales y residenciales pueden aumentar el riesgo de que parte de la población tenga que marcharse.",
  },
  riesgo_futuro: {
    weight: "15 %",
    type: "Escenario futuro",
    what: "Añade posibles efectos del clima entre 2041 y 2060 y tendencias que pueden mantener la presión.",
  },
};

const SECTIONS = [
  { id: "resultados", title: "La situación actual y el escenario con riesgo futuro" },
  { id: "factor", title: "Se añade un factor; no se predice el futuro" },
  { id: "factores", title: "Los factores" },
  { id: "union", title: "Cómo unimos datos diferentes" },
  { id: "limites", title: "Lo que esta puntuación no dice" },
];

export default function MethodologyPage() {
  // Las fuentes vienen de la API para no repetirlas a mano en dos páginas.
  const quality = useQuery({
    queryKey: ["quality-summary"],
    queryFn: () => getJSON<QualitySummary>("/api/v1/calidad/resumen"),
    staleTime: 300_000,
  });
  const sourceFor = (layer: string) =>
    quality.data?.sources.find((source) => source.layer === layer)?.name;

  return (
    <div className={styles.page}>
      <nav className={styles.index} aria-label="Secciones de la página">
        <p className={styles.indexTitle}>En esta página</p>
        <ol>
          {SECTIONS.map((section) => (
            <li key={section.id}>
              <a href={`#${section.id}`}>{section.title}</a>
            </li>
          ))}
        </ol>
      </nav>

      <article className={styles.prose}>
        <TitleBlock
          title="Cómo obtenemos la puntuación"
          reading="El Índice de Presión Residencial reúne cinco aspectos de la vivienda en una puntuación de 0 a 100."
          hint="Cuanto más alta, más presión frente al resto de los 306 municipios estudiados."
        />

        <section className={styles.block} id="resultados">
          <h2 className={styles.blockTitle}>{SECTIONS[0].title}</h2>
          <p>
            La situación actual (IPR-4) combina cuatro factores medidos o estimados con
            datos de 2023. El escenario con riesgo futuro (IPR-5) parte de esa misma
            información y añade un quinto factor sobre clima y tendencias.
          </p>
          <details className={styles.details}>
            <summary>Ver la fórmula exacta</summary>
            <p className={styles.formula}>IPR-5 = 0,30A + 0,20T + 0,20E + 0,15G + 0,15R</p>
            <p className={styles.small}>
              Para el IPR-4 observado se excluye R y se renormalizan los cuatro pesos
              restantes: 35,29 / 23,53 / 23,53 / 17,65.
            </p>
          </details>
        </section>

        <section className={styles.block} id="factor">
          <h2 className={styles.blockTitle}>{SECTIONS[1].title}</h2>
          <p>
            Ambos resultados usan la misma base de 2023. El segundo reserva un 15 % de la
            puntuación al riesgo futuro, de modo que se puede ver cuánto cambia el
            resultado al tener en cuenta ese factor adicional.
          </p>
          <p>
            La diferencia no indica cómo evolucionará un municipio. Tampoco demuestra que
            el clima sea la causa de la presión residencial.
          </p>
          <details className={styles.details}>
            <summary>Ver la relación matemática</summary>
            <p className={styles.formula}>IPR-5 = 0,85 × IPR-4 + 0,15 × R</p>
            <p className={styles.small}>
              Como el IPR-4 renormaliza los cuatro factores de 2023, la diferencia
              IPR-5 − IPR-4 equivale a 0,15 × (R − IPR-4).
            </p>
          </details>
          <Link className={styles.link} href="/prospectiva">
            Comparar los dos resultados
          </Link>
        </section>

        <section className={styles.block} id="factores">
          <h2 className={styles.blockTitle}>{SECTIONS[2].title}</h2>
          <dl className={styles.factors}>
            {LAYERS.filter((layer) => layer.id !== "ipr" && layer.id !== "calidad").map((layer) => {
              const factor = FACTORS[layer.id];
              const source = sourceFor(layer.id);
              if (!factor) return null;
              return (
                <div key={layer.id}>
                  <dt>{layerLabel(layer.id)}</dt>
                  <dd>
                    <p className={styles.factorMeta}>
                      <span className={styles.mono}>{factor.weight}</span> del IPR-5 ·{" "}
                      {factor.type}
                      {source ? ` · ${source}` : ""}
                    </p>
                    <p>{factor.what}</p>
                  </dd>
                </div>
              );
            })}
          </dl>
        </section>

        <section className={styles.block} id="union">
          <h2 className={styles.blockTitle}>{SECTIONS[3].title}</h2>
          <ol className={styles.steps}>
            <li>
              <b>Un mismo sentido:</b> ajustamos cada dato para que un valor mayor siempre
              signifique más presión.
            </li>
            <li>
              <b>Una misma escala:</b> convertimos los datos a valores de 0 a 100 para
              poder compararlos.
            </li>
            <li>
              <b>Una puntuación conjunta:</b> cada factor aporta el porcentaje indicado y
              después se suman.
            </li>
            <li>
              <b>Cinco niveles:</b> agrupamos los resultados desde presión muy baja hasta
              muy alta.
            </li>
            <li>
              <b>Comprobaciones:</b> revisamos que el resultado sea coherente y que no
              dependa demasiado de una sola decisión de cálculo.
            </li>
          </ol>
          <details className={styles.details}>
            <summary>Ver las comprobaciones técnicas</summary>
            <p className={styles.small}>
              La escala 0–100 se obtiene con percentiles nacionales robustos. La validación
              incluye correlaciones, VIF, PCA y sensibilidad de pesos.
            </p>
          </details>
        </section>

        <section className={styles.block} id="limites">
          <h2 className={styles.blockTitle}>{SECTIONS[4].title}</h2>
          <ul className={styles.limits}>
            <li>No es una estadística oficial.</li>
            <li>
              Compara 306 municipios seleccionados, no todos los municipios de España.
            </li>
            <li>
              El posible desplazamiento vecinal es una estimación de riesgo; no demuestra
              por sí solo una relación de causa y efecto.
            </li>
            <li>
              El IPR-5 es un escenario para explorar riesgos, no un dato observado en el
              futuro.
            </li>
            <li>
              Los promedios de provincias y comunidades sirven como contexto; no son nuevas
              puntuaciones oficiales.
            </li>
          </ul>
        </section>

        <Cartouche
          legend={false}
          cells={[
            { label: "Método", value: "versión 2.0" },
            { label: "Corte", value: 2023 },
            { label: "Universo", value: "306 con IPR-4 · 303 con IPR-5" },
            { label: "Escala", value: "0 menor · 100 mayor" },
            {
              label: "Nota",
              value:
                "El IPR-5 añade el escenario climático 2041–2060; no es un dato de 2023.",
              wide: true,
            },
          ]}
        />
      </article>
    </div>
  );
}
