"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Map from "@/components/Map";
import { CartoucheStrip } from "@/components/hoja/Cartouche";
import LisaLegend, { LISA_LABELS } from "@/components/hoja/LisaLegend";
import MapFrame from "@/components/hoja/MapFrame";
import mapStyles from "@/components/hoja/map-frame.module.css";
import MoranScatter from "@/components/hoja/MoranScatter";
import { StatusLine } from "@/components/hoja/Status";
import TitleBlock from "@/components/hoja/TitleBlock";
import { getJSON } from "@/lib/api";
import { fmt, placeName } from "@/lib/format";
import { HOJA_MAP_THEME } from "@/lib/mapTheme";
import {
  formatSpatial,
  type SpatialHistory,
  type SpatialMunicipality,
  type SpatialYear,
} from "@/lib/spatial";

import styles from "./espacial.module.css";

/** Ficha breve del municipio elegido: su asociación local y sus vecinos. */
function MunicipalityDetail({
  codIne,
  year,
  corrected,
  onBack,
}: {
  codIne: string;
  year: number;
  corrected: boolean;
  onBack: () => void;
}) {
  const detail = useQuery({
    queryKey: ["spatial-municipality", codIne, year],
    queryFn: () =>
      getJSON<SpatialMunicipality>(`/api/v1/municipios/${codIne}/espacial?anio=${year}`),
  });
  const row = detail.data;

  if (!row) {
    return (
      <StatusLine
        loading={detail.isLoading}
        error={detail.isError}
        retry={() => detail.refetch()}
      >
        Cargando la asociación local…
      </StatusLine>
    );
  }

  const kind = corrected ? row.cluster_type : row.cluster_type_raw;
  const significant = corrected ? row.is_significant : row.is_significant_raw;

  return (
    <section className={styles.detail} aria-label="Resultado espacial del municipio">
      <button type="button" className={styles.backLink} onClick={onBack}>
        ← Todos los municipios
      </button>
      <p className={styles.detailCode}>
        {year} · <span className={styles.mono}>{row.cod_ine}</span>
      </p>
      <h2>{placeName(row.nombre)}</h2>
      <p className={styles.cluster}>
        <i data-cluster={row.eligible ? kind : "NE"} aria-hidden="true" />
        {row.eligible ? LISA_LABELS[kind] : LISA_LABELS.NE}
      </p>
      {!row.eligible && (
        <p className={styles.notice}>
          No comparte frontera ni vértice con otro municipio de la muestra. Se conserva
          su puntuación; no se calcula significación local.
        </p>
      )}
      <dl className={styles.facts}>
        <div>
          <dt>IPR-4 observado</dt>
          <dd>{fmt(row.ipr)}</dd>
        </div>
        <div>
          <dt>I de Moran local</dt>
          <dd>{formatSpatial(row.local_moran_i)}</dd>
        </div>
        <div>
          <dt>p sin corrección</dt>
          <dd>{formatSpatial(row.p_value)}</dd>
        </div>
        <div>
          <dt>p ajustado (FDR)</dt>
          <dd>{formatSpatial(row.p_value_fdr)}</dd>
        </div>
        <div>
          <dt>Asociación significativa</dt>
          <dd>{row.eligible ? (significant ? "Sí" : "No") : "No evaluable"}</dd>
        </div>
        <div>
          <dt>Vecinos</dt>
          <dd>{row.neighbor_count}</dd>
        </div>
        <div>
          <dt>IPR medio de los vecinos</dt>
          <dd>{formatSpatial(row.spatial_lag_ipr, 1)}</dd>
        </div>
        <div>
          <dt>Calidad del dato</dt>
          <dd>{row.dqs == null ? "No disponible" : fmt(row.dqs)}</dd>
        </div>
      </dl>
      {row.neighbor_count > 0 && (
        <details className={styles.details}>
          <summary>Ver los vecinos y sus valores</summary>
          <ul className={styles.neighbors}>
            {row.neighbors.map((neighbor) => (
              <li key={neighbor.cod_ine}>
                <span>{placeName(neighbor.nombre)}</span>
                <b className={styles.mono}>{fmt(neighbor.ipr)}</b>
              </li>
            ))}
          </ul>
        </details>
      )}
      <Link href={`/municipio/${codIne}`} className={styles.fichaLink}>
        Abrir la hoja del municipio
      </Link>
    </section>
  );
}

export default function SpatialPage() {
  const [year, setYear] = useState<number | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [corrected, setCorrected] = useState(true);

  const history = useQuery({
    queryKey: ["spatial-history"],
    queryFn: () => getJSON<SpatialHistory>("/api/v1/espacial/historico"),
    staleTime: 300_000,
  });
  const selectedYear = year ?? history.data?.years[0]?.anio ?? null;
  const analysis = useQuery({
    queryKey: ["spatial", selectedYear],
    queryFn: () => getJSON<SpatialYear>(`/api/v1/espacial?anio=${selectedYear}`),
    enabled: selectedYear != null,
  });
  const geometry = useQuery({
    queryKey: ["geometry"],
    queryFn: () => getJSON<GeoJSON.FeatureCollection>("/api/v1/mapa/geometrias"),
    staleTime: 86_400_000,
  });

  if (!history.data || !analysis.data || !geometry.data) {
    const empty = history.data && history.data.years.length === 0;
    return (
      <div className={styles.page}>
        <TitleBlock
          title="Patrones espaciales del IPR-4"
          reading={
            empty
              ? "No hay análisis espacial precalculado."
              : "Cargando el análisis espacial…"
          }
        />
        {!empty && (
          <StatusLine
            loading={history.isLoading || analysis.isLoading || geometry.isLoading}
            error={history.isError || analysis.isError || geometry.isError}
            retry={() => {
              history.refetch();
              analysis.refetch();
              geometry.refetch();
            }}
          />
        )}
      </div>
    );
  }

  const data = analysis.data;
  const result = data.global_result;
  const summary = result.summary;
  const rawCount = summary
    .filter((row) => row.cluster_type !== "NS")
    .reduce((total, row) => total + row.raw_count, 0);
  const fdrCount = summary
    .filter((row) => row.cluster_type !== "NS")
    .reduce((total, row) => total + row.count, 0);
  const values = data.items.map((row) => ({
    cod_ine: row.cod_ine,
    valor: row.ipr,
    categoria: !row.eligible ? "NE" : corrected ? row.cluster_type : row.cluster_type_raw,
  }));
  const lowQuality = data.items.some(
    (row) => (corrected ? row.is_significant : row.is_significant_raw) && row.dqs_level === "bajo",
  );
  const sorted = [...data.items].sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));

  return (
    <div className={styles.page}>
      <TitleBlock
        title="Patrones espaciales del IPR-4"
        reading={`${result.interpretation.charAt(0).toUpperCase()}${result.interpretation.slice(1)} en ${result.anio}: I de Moran ${result.moran_i.toFixed(3)}, p = ${result.p_value.toFixed(3)}.`}
        hint="Moran mide si los municipios parecidos están juntos; LISA localiza dónde y contrasta cada uno con sus vecinos."
      />

      <div className={styles.controls}>
        <label>
          Año
          <select
            aria-label="Año del análisis"
            value={result.anio}
            onChange={(event) => setYear(Number(event.target.value))}
          >
            {history.data.years.map((row) => (
              <option key={row.anio} value={row.anio}>
                {row.anio}
              </option>
            ))}
          </select>
        </label>
        <label>
          Significación local
          <select
            aria-label="Significación local"
            value={corrected ? "fdr" : "raw"}
            onChange={(event) => setCorrected(event.target.value === "fdr")}
          >
            <option value="fdr">Con corrección FDR (Benjamini–Hochberg)</option>
            <option value="raw">Sin corrección · exploratorio</option>
          </select>
        </label>
        <label>
          Municipio
          <select
            aria-label="Consultar municipio"
            value={selected ?? ""}
            onChange={(event) => setSelected(event.target.value || null)}
          >
            <option value="">Elegir en el mapa o en la lista</option>
            {sorted.map((row) => (
              <option key={row.cod_ine} value={row.cod_ine}>
                {placeName(row.nombre)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <ul className={styles.stats} aria-label="Moran global">
        <li>
          <small>Autocorrelación espacial</small>
          <strong>I = {result.moran_i.toFixed(3)}</strong>
          <span>{result.interpretation}</span>
        </li>
        <li>
          <small>p bilateral por permutaciones</small>
          <strong>{result.p_value.toFixed(3)}</strong>
          <span>
            {result.permutations} permutaciones · α = {result.alpha}
          </span>
        </li>
        <li>
          <small>Municipios evaluados</small>
          <strong>
            {result.n_observations} de {result.n_municipalities}
          </strong>
          <span>{result.n_islands} sin vecinos en la muestra</span>
        </li>
      </ul>

      <p className={styles.notice}>
        La muestra es discontinua: solo entran en el cálculo los municipios que comparten
        frontera o vértice con otro de los 306. No representa toda España. Los{" "}
        {result.n_islands} sin vecinos se ven en el mapa como no evaluables.
      </p>

      <div className={styles.body}>
        <section className={styles.main} aria-label="Mapa de asociaciones locales">
          <MapFrame
            legend={
              <div className={mapStyles.legend} aria-label="Leyenda">
                <small>
                  LISA · {result.anio} · {corrected ? "con FDR" : "sin corrección"}
                </small>
                <LisaLegend compact />
              </div>
            }
          >
            <Map
              geometry={geometry.data}
              values={values}
              visibleIds={data.items.map((row) => row.cod_ine)}
              filterActive={false}
              selectedId={selected}
              onSelect={setSelected}
              colorScale="lisa"
              valueLabel="IPR"
              ariaLabel="Mapa interactivo de asociaciones locales LISA"
              theme={HOJA_MAP_THEME}
            />
          </MapFrame>
        </section>

        <aside
          className={styles.side}
          aria-label={selected ? "Municipio seleccionado" : "Cómo leer el mapa"}
        >
          {selected ? (
            <MunicipalityDetail
              key={`${selected}-${result.anio}`}
              codIne={selected}
              year={result.anio}
              corrected={corrected}
              onBack={() => setSelected(null)}
            />
          ) : (
            <section className={styles.detail}>
              <h2 className={styles.sideTitle}>Cómo leer el mapa</h2>
              <p>
                Pulsa un municipio para ver su puntuación, su asociación local, la
                significación y sus vecinos.
              </p>
              <p>
                <b>Alto entre altos</b> y <b>bajo entre bajos</b>: valores parecidos a los
                de sus vecinos, con asociación significativa según el criterio elegido.
              </p>
              <p>
                <b>Alto entre bajos</b> y <b>bajo entre altos</b>: municipios que contrastan
                con su entorno; posibles excepciones espaciales.
              </p>
              <p>
                <b>Sin asociación significativa</b> no equivale a presión baja: solo no
                hay evidencia suficiente de asociación local.
              </p>
            </section>
          )}
        </aside>
      </div>

      <div className={styles.columns}>
        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Diagrama de Moran · {result.anio}</h2>
          <MoranScatter data={data} />
        </section>

        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Comparaciones múltiples</h2>
          <p>
            Sin corrección hay <b>{rawCount}</b> asociaciones locales; con FDR quedan{" "}
            <b>{fdrCount}</b>. La vista principal aplica FDR para no dar por descubierto lo
            que aparece por contrastar muchos municipios a la vez.
          </p>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">Categoría</th>
                  <th scope="col" className={styles.num}>Con FDR</th>
                  <th scope="col" className={styles.num}>% del total</th>
                  <th scope="col" className={styles.num}>Sin corrección</th>
                </tr>
              </thead>
              <tbody>
                {summary.map((row) => (
                  <tr key={row.cluster_type}>
                    <th scope="row">
                      {row.cluster_type} · {LISA_LABELS[row.cluster_type]}
                    </th>
                    <td className={styles.num}>{row.count}</td>
                    <td className={styles.num}>{row.percentage.toFixed(1)} %</td>
                    <td className={styles.num}>{row.raw_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className={styles.small}>
            La fila NS incluye los {result.n_islands} municipios no evaluables. Los
            porcentajes usan los {result.n_municipalities} municipios.
          </p>
          {!history.data.dqs_available && (
            <p className={styles.small}>
              Calidad del dato no disponible en este corte; presión y LISA se muestran por
              separado.
            </p>
          )}
          {lowQuality && (
            <p className={styles.notice}>
              Hay asociaciones significativas con calidad del dato baja. Revisa la ficha
              antes de interpretar el clúster.
            </p>
          )}
        </section>
      </div>

      {history.data.history_comparable && (
        <section className={styles.block}>
          <h2 className={styles.blockTitle}>Evolución de la estructura espacial</h2>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">Año</th>
                  <th scope="col" className={styles.num}>I de Moran</th>
                  <th scope="col" className={styles.num}>p</th>
                  <th scope="col">Lectura</th>
                </tr>
              </thead>
              <tbody>
                {history.data.years.map((row) => (
                  <tr key={row.anio}>
                    <th scope="row">{row.anio}</th>
                    <td className={styles.num}>{row.moran_i.toFixed(3)}</td>
                    <td className={styles.num}>{row.p_value.toFixed(3)}</td>
                    <td>{row.interpretation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className={styles.small}>
            Más I de Moran es más estructura espacial, no necesariamente más presión.
          </p>
        </section>
      )}

      <section className={styles.block}>
        <h2 className={styles.blockTitle}>Cómo interpretar este análisis</h2>
        <p>
          Una I de Moran positiva sugiere que los valores parecidos se agrupan; una
          negativa, que los vecinos contrastan. La conclusión depende también del p-valor,
          y un resultado no significativo no prueba que no haya estructura.
        </p>
        <p>
          Que exista autocorrelación indica que la distribución del índice no es
          independiente de la geografía. No demuestra relaciones causales entre
          municipios ni dibuja fronteras de zonas homogéneas.
        </p>
        <details className={styles.details}>
          <summary>Parámetros y límites del cálculo</summary>
          <p>
            Vecindad {result.weights_method} con pesos normalizados por fila, semilla{" "}
            {result.seed}, {result.permutations} permutaciones. E[I] ={" "}
            {result.expected_i.toFixed(5)}; z de permutaciones = {result.z_score.toFixed(3)}.
            Versión {result.calculation_version}.
          </p>
          <p>
            Contrastes bilaterales con corrección +1. LISA usa permutación condicional y la
            corrección FDR se aplica por año a todos los municipios evaluables. Los
            municipios sin vecinos no se conectan por cercanía: la proximidad entre
            puntos no garantiza continuidad territorial, sobre todo a través del mar.
          </p>
        </details>
        <Link href="/metodologia" className={styles.link}>
          Cómo se calcula el índice
        </Link>
      </section>

      <CartoucheStrip
        cells={[
          { label: "Corte", value: result.anio },
          { label: "Vecindad", value: result.weights_method },
          { label: "Permutaciones", value: result.permutations },
          { label: "Alfa", value: result.alpha },
          { label: "Corrección", value: result.main_correction },
          {
            label: "Evaluados",
            value: `${result.n_observations} de ${result.n_municipalities}`,
          },
          { label: "Versión", value: result.calculation_version },
        ]}
      />
    </div>
  );
}
