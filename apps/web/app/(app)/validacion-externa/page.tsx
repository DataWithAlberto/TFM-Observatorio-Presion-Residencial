import Image from "next/image";
import Link from "next/link";

import { Cartouche } from "@/components/hoja/Cartouche";
import TitleBlock from "@/components/hoja/TitleBlock";
import results from "@/public/validacion-externa/resultados.json";

import styles from "./validacion.module.css";

const num = (value: number | null | undefined, digits = 3) =>
  value == null ? "No estimable" : value.toLocaleString("es-ES", { maximumFractionDigits: digits });
const pValue = (value: number | null | undefined) =>
  value == null ? "No estimable" : value.toLocaleString("es-ES", { maximumFractionDigits: 5 });

const primary = results.correlaciones[0];
const config = results.protocolo;

/**
 * Contraste del índice con una variable que no interviene en su cálculo: el
 * alquiler declarado. Es una página de lectura, construida con el resultado
 * ya calculado por el pipeline, sin llamadas a la API.
 */
export default function ExternalValidationPage() {
  return (
    <div className={styles.page}>
      <article className={styles.prose}>
        <TitleBlock
          title="Validación externa del índice"
          reading={`Spearman ρ = ${num(primary.rho)} entre el IPR-4 y el alquiler declarado de ${primary.periodo_externo}, con ${primary.n} de ${primary.universo} municipios.`}
          hint="Una asociación positiva es coherente con la hipótesis; no certifica que el índice sea correcto ni implica causalidad."
        />

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Qué comparamos y por qué</h2>
          <p>
            <b>{config.indicador}</b>, en euros al mes, frente al IPR-4 observado de{" "}
            {config.periodo_ipr}. La competencia por la vivienda puede acompañarse de
            mayores costes de alquiler, y esa relación permite contrastar una dimensión de
            la presión residencial con un dato ajeno al índice.
          </p>
          <p>
            Fuente: <a href={config.url}>{config.fuente}</a>. Son alquileres habituales
            declarados de vivienda colectiva: no son precios de anuncios, ni esfuerzo de
            los hogares, ni recuentos de desahucios. La hipótesis previa esperaba una
            asociación positiva; los componentes y pesos del índice no se tocan.
          </p>
          <dl className={styles.metrics}>
            <div>
              <dt>Periodo</dt>
              <dd>{primary.periodo_externo}</dd>
            </div>
            <div>
              <dt>Cobertura</dt>
              <dd>{num(primary.cobertura * 100, 1)} %</dd>
            </div>
            <div>
              <dt>Spearman ρ</dt>
              <dd>{num(primary.rho)}</dd>
            </div>
            <div>
              <dt>p bilateral</dt>
              <dd>{pValue(primary.p_value)}</dd>
            </div>
            <div>
              <dt>Municipios</dt>
              <dd>
                {primary.n} de {primary.universo}
              </dd>
            </div>
          </dl>
          <p>{results.interpretacion}</p>
          <p className={styles.small}>
            p-valor por {config.permutaciones.toLocaleString("es-ES")} permutaciones; el
            mínimo posible es {pValue(1 / (config.permutaciones + 1))}. Alfa{" "}
            {num(config.alpha, 2)}. Se supone independencia entre municipios; la
            dependencia territorial puede hacer el p-valor optimista.
          </p>
        </section>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Índice y coste del alquiler</h2>
          <Image
            className={styles.figure}
            src="/validacion-externa/dispersion.svg"
            width={900}
            height={500}
            unoptimized
            alt={`Dispersión de ${primary.n} municipios entre el IPR-4 y el alquiler mensual; Spearman ρ ${num(primary.rho)}.`}
          />
          <p className={styles.small}>
            Cada punto es un municipio. Entran todos los valores disponibles, también los
            extremos.
          </p>
        </section>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Alquiler por nivel de presión</h2>
          <Image
            className={styles.figure}
            src="/validacion-externa/cuartiles.svg"
            width={900}
            height={500}
            unoptimized
            alt="Distribución del alquiler en los cuatro cuartiles del índice; medianas y rangos en la tabla siguiente."
          />
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <caption className={styles.caption}>
                Cuartiles fijados sobre los 306 municipios; Q1 menor presión, Q4 mayor
              </caption>
              <thead>
                <tr>
                  <th scope="col">Grupo</th>
                  <th scope="col" className={styles.num}>Municipios</th>
                  <th scope="col" className={styles.num}>Mediana €/mes</th>
                  <th scope="col" className={styles.num}>P25</th>
                  <th scope="col" className={styles.num}>P75</th>
                </tr>
              </thead>
              <tbody>
                {results.grupos.map((group) => (
                  <tr key={group.cuartil}>
                    <th scope="row">{group.cuartil}</th>
                    <td className={styles.num}>{group.n}</td>
                    <td className={styles.num}>{num(group.mediana, 1)}</td>
                    <td className={styles.num}>{num(group.p25, 1)}</td>
                    <td className={styles.num}>{num(group.p75, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className={styles.small}>
            Kruskal–Wallis global, exploratorio: H = {num(results.kruskal_wallis.h)}, p ={" "}
            {results.kruskal_wallis.p_value?.toExponential(2) ?? "No estimable"}. Este
            contraste no identifica por sí solo una diferencia entre Q1 y Q4.
          </p>
        </section>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Robustez y límites</h2>
          <p>{results.limitaciones}</p>
          <p className={styles.small}>Pearson: {results.pearson}</p>
          <details className={styles.details}>
            <summary>Ver las comprobaciones exploratorias</summary>
            <p className={styles.small}>
              Se retiran los extremos P1–P99, se compara con el IPR-5 y se varía el año del
              alquiler manteniendo el índice de 2023, siempre sobre una muestra común. No
              son pruebas confirmatorias ni validan predicciones.
            </p>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th scope="col">Análisis</th>
                    <th scope="col" className={styles.num}>Alquiler</th>
                    <th scope="col" className={styles.num}>N</th>
                    <th scope="col" className={styles.num}>ρ</th>
                    <th scope="col" className={styles.num}>p</th>
                  </tr>
                </thead>
                <tbody>
                  {results.correlaciones.slice(1).map((row, index) => (
                    <tr key={`${row.analisis}-${index}`}>
                      <th scope="row">{row.analisis.replaceAll("_", " ")}</th>
                      <td className={styles.num}>{row.periodo_externo}</td>
                      <td className={styles.num}>{row.n}</td>
                      <td className={styles.num}>{num(row.rho)}</td>
                      <td className={styles.num}>{pValue(row.p_value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
          <details className={styles.details}>
            <summary>
              Municipios sin alquiler publicado en el corte ({results.ausentes.length})
            </summary>
            <p className={styles.small}>
              Sin imputación ni sustitución por cero: la ausencia de dato no indica ausencia
              de tensión.
            </p>
            <ul className={styles.list}>
              {results.ausentes.map((row) => (
                <li key={row.cod_ine}>
                  {row.nombre} <span className={styles.mono}>{row.cod_ine}</span>
                </li>
              ))}
            </ul>
          </details>
          <p className={styles.small}>
            Se publican igualmente los resultados débiles, negativos o no significativos.
            Pueden reflejar conceptos distintos, cobertura, periodos o límites del índice.
          </p>
        </section>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Datos del contraste</h2>
          <p>
            Instantánea generada por el análisis reproducible del proyecto. Descarga de la
            fuente: {results.fuente.downloaded_at.slice(0, 10)}.
          </p>
          <p className={styles.links}>
            <a href="/validacion-externa/pares_ipr_alquiler_2023.csv" download>
              Descargar los pares en CSV
            </a>
            <a href="/validacion-externa/resultados.json" download>
              Resultados y protocolo en JSON
            </a>
            <Link href="/metodologia">Cómo se calcula el índice</Link>
          </p>
        </section>

        <Cartouche
          legend={false}
          cells={[
            { label: "Producto", value: "IPR-4 observado" },
            { label: "Corte", value: config.periodo_ipr },
            { label: "Externo", value: `Alquiler ${primary.periodo_externo}` },
            { label: "Municipios", value: `${primary.n} de ${primary.universo}` },
            { label: "Contraste", value: "Spearman · permutación" },
            { label: "Fuente", value: config.fuente, wide: true },
          ]}
        />
      </article>
    </div>
  );
}
