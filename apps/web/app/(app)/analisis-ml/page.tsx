"use client";

import Link from "next/link";
import { useState } from "react";

import { Cartouche } from "@/components/hoja/Cartouche";
import MlCharts, { type MlReport } from "@/components/hoja/MlCharts";
import TitleBlock from "@/components/hoja/TitleBlock";
import report from "@/data/ml_exploratory.json";
import { fmt, placeName } from "@/lib/format";

import styles from "./analisis-ml.module.css";

const data = report as typeof report & MlReport;
const signed = (value: number, digits = 1) =>
  `${value > 0 ? "+" : value < 0 ? "−" : ""}${Math.abs(value).toFixed(digits)}`;
const xgboost = data.metrics.find((metric) => metric.modelo === "xgboost_comparativo");
const dummy = data.metrics.find((metric) => metric.modelo === "dummy_media_cv");

/**
 * Análisis exploratorio con Machine Learning. La página existe para dejar
 * claro lo que este bloque es y lo que no: el índice publicado sale de la
 * fórmula interpretable; el XGBoost solo la reconstruye a partir de sus
 * propios componentes, así que no puede llamarse predicción.
 */
export default function MlPage() {
  const [codIne, setCodIne] = useState(data.rows[0].cod_ine);
  const row = data.rows.find((item) => item.cod_ine === codIne) ?? data.rows[0];
  const contributions = data.features
    .map((feature, index) => ({
      ...feature,
      shap: row.shap[index],
      value: row.feature_values[index] as number | null,
      imputed: row.imputed_values[index],
    }))
    .sort((a, b) => Math.abs(b.shap) - Math.abs(a.shap));
  const sorted = [...data.rows].sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));

  return (
    <div className={styles.page}>
      <article className={styles.prose}>
        <TitleBlock
          title="Análisis exploratorio con Machine Learning"
          reading={`Un XGBoost reconstruye el índice de riesgo futuro con un error medio de ${fmt(xgboost?.mae_cv)} puntos fuera de muestra, frente a ${fmt(dummy?.mae_cv)} de una media constante.`}
          hint="Mide reconstrucción matemática de la fórmula, no capacidad de predicción: las variables de entrada forman parte del propio índice."
        />

        <p className={styles.notice} role="note">
          <b>Índice publicado = fórmula interpretable.</b> {data.notice}
        </p>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Tres referencias para leer la aproximación</h2>
          <p>
            <b>A · Fórmula interpretable:</b> {data.official.formula}. Define la puntuación
            metodológica oficial; no es un modelo entrenado y no tiene error de validación.
          </p>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">Modelo</th>
                  <th scope="col" className={styles.num}>Error medio (puntos)</th>
                  <th scope="col" className={styles.num}>Municipios</th>
                  <th scope="col">Lectura</th>
                </tr>
              </thead>
              <tbody>
                {data.metrics.map((metric) => (
                  <tr key={metric.modelo}>
                    <th scope="row">{metric.label}</th>
                    <td className={styles.num}>{fmt(metric.mae_cv, 2)}</td>
                    <td className={styles.num}>{metric.n}</td>
                    <td>{metric.interpretation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className={styles.small}>
            Cinco particiones idénticas. Cada salida se obtiene con un modelo entrenado sin
            ese municipio. El error es la media del error absoluto de todas esas salidas,
            en puntos del índice. Sin validación temporal ni externa.
          </p>
        </section>

        <div className={styles.columns}>
          <section className={styles.block}>
            <h2 className={styles.blockTitle}>Fórmula frente a salida del modelo</h2>
            <p className={styles.small}>
              Cada punto es un municipio; la diagonal es la coincidencia exacta.
            </p>
            <MlCharts report={data} which="scatter" height={340} />
          </section>
          <section className={styles.block}>
            <h2 className={styles.blockTitle}>Distribución de los errores</h2>
            <p className={styles.small}>
              Error absoluto por municipio fuera de entrenamiento, en intervalos de dos
              puntos.
            </p>
            <MlCharts report={data} which="errors" height={340} />
          </section>
        </div>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Contribución media de cada variable (SHAP)</h2>
          <p>{data.shap_notice}</p>
          <p className={styles.small}>
            Se agregan las contribuciones de los cinco modelos, calculadas sobre los{" "}
            {data.metadata.n_municipalities} municipios fuera de su partición de
            entrenamiento.
          </p>
          <MlCharts report={data} which="global" height={300} />
        </section>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Distribución de las contribuciones</h2>
          <p className={styles.small}>
            Cada punto es un municipio y una variable. A la derecha de cero, la
            contribución eleva la salida del modelo; a la izquierda, la reduce. El color
            es el valor de entrada relativo tras la imputación de su partición.
          </p>
          <MlCharts report={data} which="beeswarm" height={420} />
        </section>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Explicación de un municipio</h2>
          <label className={styles.field}>
            Municipio elegible
            <select value={codIne} onChange={(event) => setCodIne(event.target.value)}>
              {sorted.map((item) => (
                <option key={item.cod_ine} value={item.cod_ine}>
                  {placeName(item.nombre)} · {item.cod_ine}
                </option>
              ))}
            </select>
          </label>
          <dl className={styles.facts}>
            <div>
              <dt>Puntuación por la fórmula</dt>
              <dd>{fmt(row.score)}</dd>
            </div>
            <div>
              <dt>Salida del XGBoost</dt>
              <dd>{fmt(row.xgboost)}</dd>
            </div>
            <div>
              <dt>Diferencia</dt>
              <dd>{signed(row.residual)}</dd>
            </div>
            <div>
              <dt>Error absoluto</dt>
              <dd>{fmt(row.absolute_error)}</dd>
            </div>
          </dl>
          <p className={styles.small}>
            Partición {row.fold}: base del modelo {fmt(row.shap_base)} + suma de
            contribuciones {signed(row.shap.reduce((total, value) => total + value, 0))} =
            salida {fmt(row.xgboost)}, salvo redondeo.
          </p>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">Variable</th>
                  <th scope="col" className={styles.num}>Entrada del modelo</th>
                  <th scope="col" className={styles.num}>Contribución</th>
                </tr>
              </thead>
              <tbody>
                {contributions.map((feature) => (
                  <tr key={feature.name}>
                    <th scope="row">{feature.label}</th>
                    <td className={styles.num}>
                      {feature.value == null
                        ? `${fmt(feature.imputed)} (mediana imputada)`
                        : fmt(feature.value)}
                    </td>
                    <td className={styles.num}>{signed(feature.shap)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className={styles.small}>
            Los municipios sin puntuación oficial elegible no se imputan para incluirlos
            en el experimento.
          </p>
        </section>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Límites del bloque de Machine Learning</h2>
          <p>
            El objetivo deriva de los mismos componentes que las variables de entrada:
            hay fuga de información estructural. La evaluación es transversal sobre un
            único corte; no existe horizonte posterior ni etiqueta externa independiente,
            y no se evalúa la generalización geográfica. Por eso no se afirma capacidad
            predictiva ni causalidad.
          </p>
          <details className={styles.details}>
            <summary>Trazabilidad del experimento</summary>
            <p className={styles.small}>
              Generado el {data.metadata.generated_at.slice(0, 10)}. Versión metodológica{" "}
              {data.metadata.version_metodologia}; semilla {data.metadata.random_state}.
              Municipios {data.metadata.n_municipalities} de {data.metadata.n_universe};
              variables activas {data.metadata.n_features}. La tendencia especulativa se
              excluye por estar completamente ausente.
            </p>
            <p className={styles.small}>
              TreeSHAP exacto de XGBoost; las bases corresponden a cada modelo de
              entrenamiento y la importancia global resume los cinco. Esta página usa un
              artefacto estático, independiente de la API y de los rankings oficiales.
            </p>
            <p className={styles.small}>
              Versiones:{" "}
              {Object.entries(data.metadata.versions)
                .map(([name, version]) => `${name} ${version}`)
                .join(" · ")}
            </p>
          </details>
          <Link href="/metodologia" className={styles.link}>
            Cómo se calcula el índice
          </Link>
        </section>

        <Cartouche
          legend={false}
          cells={[
            { label: "Carácter", value: "Exploratorio" },
            { label: "Corte", value: data.metadata.anio_base },
            {
              label: "Municipios",
              value: `${data.metadata.n_municipalities} de ${data.metadata.n_universe}`,
            },
            { label: "Validación", value: "5 particiones, fuera de muestra" },
            { label: "Explicación", value: "TreeSHAP" },
            { label: "Índice oficial", value: "Fórmula interpretable", wide: true },
          ]}
        />
      </article>
    </div>
  );
}
