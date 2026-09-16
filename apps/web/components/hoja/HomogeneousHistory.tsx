"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import LineChart from "@/components/hoja/LineChart";
import { StatusLine } from "@/components/hoja/Status";
import {
  getJSON,
  type HistoricalPoint,
  type HistoricalRank,
  type HomogeneousHistory as History,
} from "@/lib/api";
import { fmt, layerLabel, placeName } from "@/lib/format";

import styles from "./homogeneous-history.module.css";

const ORDERS = [
  { id: "ranking", label: "Mayor presión" },
  { id: "incremento", label: "Mayores incrementos" },
  { id: "descenso", label: "Mayores descensos" },
  { id: "subida_ranking", label: "Mayores subidas de puesto" },
  { id: "bajada_ranking", label: "Mayores bajadas de puesto" },
];

const signed = (value: number | null | undefined, digits = 1) =>
  value == null
    ? "—"
    : `${value > 0 ? "+" : value < 0 ? "−" : ""}${Math.abs(value).toFixed(digits)}`;

/**
 * El IPR-4 histórico relativo: un panel fijo de municipios y cuatro años con
 * la misma definición, para que las puntuaciones sean comparables entre sí.
 * Es un producto distinto del corte nacional de 2023 y se lee por separado.
 */
export default function HomogeneousHistory({ codIne }: { codIne: string }) {
  const [year, setYear] = useState("");
  const [order, setOrder] = useState("ranking");

  const history = useQuery({
    queryKey: ["homogeneous-history", codIne],
    queryFn: () =>
      getJSON<History>(`/api/v1/municipios/${codIne}/historico?serie=homogenea`),
  });
  const data = history.data;
  const years = data?.metadata.years ?? [];
  const selectedYear = year || String(years.at(-1) ?? "");
  const ranking = useQuery({
    queryKey: ["historical-ranking", selectedYear, order],
    queryFn: () =>
      getJSON<HistoricalRank[]>(
        `/api/v1/ranking?producto=historico&anio=${selectedYear}&orden=${order}`,
      ),
    enabled: Boolean(selectedYear),
  });

  if (!data) {
    return (
      <StatusLine
        loading={history.isLoading}
        error={history.isError}
        retry={() => history.refetch()}
      >
        Cargando la evolución del índice…
      </StatusLine>
    );
  }

  const selected = data.items.find((item) => String(item.anio) === selectedYear);
  const iprSeries: HistoricalPoint[] = data.items.map((item) => ({
    anio: item.anio,
    serie: "ipr_historico",
    valor: item.ipr_score,
    tipo: "observado",
  }));
  const componentSeries: HistoricalPoint[] = data.items.flatMap((item) =>
    item.components.map((component) => ({
      anio: item.anio,
      serie: component.component,
      valor: component.value,
      bruto: component.layer_score,
      tipo: "observado" as const,
    })),
  );

  return (
    <div className={styles.history}>
      <p className={styles.intro}>
        Panel fijo de {data.metadata.municipality_count ?? "—"} municipios entre{" "}
        {years[0]} y {years.at(-1)}. Un aumento indica más presión relativa dentro de
        ese mismo grupo: una subida general de precios puede no reflejarse. Se
        calcula aparte del resultado nacional de 2023.
      </p>

      {!data.included ? (
        <p className={styles.notice} role="status">
          Este municipio queda fuera del panel histórico: falta cobertura suficiente en
          alguna variable o en los años necesarios para calcular sus variaciones.
          {data.reason && ` Motivo registrado: ${data.reason}.`}
        </p>
      ) : (
        <>
          <LineChart points={iprSeries} height={200} valueName="puntuación" />
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">Año</th>
                  <th scope="col" className={styles.num}>IPR</th>
                  <th scope="col" className={styles.num}>Cambio anual</th>
                  <th scope="col" className={styles.num}>Desde el inicio</th>
                  <th scope="col" className={styles.num}>Puesto</th>
                  <th scope="col" className={styles.num}>Cambio de puesto</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.anio}>
                    <th scope="row">{item.anio}</th>
                    <td className={styles.num}>{fmt(item.ipr_score)}</td>
                    <td className={styles.num}>{signed(item.delta_ipr)}</td>
                    <td className={styles.num}>{signed(item.delta_since_start)}</td>
                    <td className={styles.num}>{item.rank}</td>
                    <td className={styles.num}>{signed(item.rank_change, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className={styles.small}>
            El puesto 1 tiene la mayor presión. Un cambio de puesto positivo indica
            menor presión relativa. Cuatro años con ventanas solapadas no bastan para
            identificar un cambio estructural.
          </p>
        </>
      )}

      {years.length > 0 && (
        <>
          <div className={styles.controls}>
            <label>
              Año del panel
              <select
                aria-label="Año del panel histórico"
                value={selectedYear}
                onChange={(event) => setYear(event.target.value)}
              >
                {years.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Relación del panel
              <select
                aria-label="Orden del ranking histórico"
                value={order}
                onChange={(event) => setOrder(event.target.value)}
              >
                {ORDERS.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {selected && (
            <section className={styles.sub}>
              <h3 className={styles.subTitle}>
                Qué componente explica el cambio · {selectedYear}
              </h3>
              <p className={styles.small}>
                Comparación con el año anterior. Son contribuciones aritméticas al
                índice, sin atribución causal. El panel se construye con la posición
                dentro de sus {data.metadata.municipality_count ?? "—"} municipios, así
                que es esa columna la que multiplica el peso y forma el aporte. La
                puntuación del factor es la misma magnitud que el cuadro de factores de
                esta hoja y aquí solo acompaña.
              </p>
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th scope="col">Componente</th>
                      <th scope="col" className={styles.num}>Posición en el panel</th>
                      <th scope="col" className={styles.num}>Puntuación del factor</th>
                      <th scope="col" className={styles.num}>Aporte al IPR</th>
                      <th scope="col" className={styles.num}>Cambio del aporte</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selected.components.map((component) => (
                      <tr key={component.component}>
                        <th scope="row">{layerLabel(component.component, true)}</th>
                        <td className={styles.num}>{fmt(component.value)}</td>
                        <td className={styles.num}>{fmt(component.layer_score)}</td>
                        <td className={styles.num}>{fmt(component.contribution)}</td>
                        <td className={styles.num}>
                          {signed(component.delta_contribution)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <details className={styles.details}>
                <summary>Ver la evolución de los componentes</summary>
                <LineChart points={componentSeries} height={220} />
              </details>
            </section>
          )}

          <details className={styles.details}>
            <summary>
              Relación del panel en {selectedYear} ·{" "}
              {ORDERS.find((option) => option.id === order)?.label.toLowerCase()}
            </summary>
            {ranking.data ? (
              ranking.data.length === 0 ? (
                <p className={styles.small}>
                  No hay cambios anuales disponibles para esta selección.
                </p>
              ) : (
                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th scope="col" className={styles.num}>Puesto</th>
                        <th scope="col">Municipio</th>
                        <th scope="col" className={styles.num}>IPR</th>
                        <th scope="col" className={styles.num}>Cambio anual</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ranking.data.slice(0, 10).map((row) => (
                        <tr key={row.cod_ine}>
                          <td className={styles.num}>{row.ranking}</td>
                          <td>
                            <Link href={`/municipio/${row.cod_ine}`}>
                              {placeName(row.nombre)}
                            </Link>
                          </td>
                          <td className={styles.num}>{fmt(row.score)}</td>
                          <td className={styles.num}>{signed(row.delta_ipr)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
            ) : (
              <StatusLine
                loading={ranking.isLoading}
                error={ranking.isError}
                retry={() => ranking.refetch()}
              />
            )}
          </details>
        </>
      )}
    </div>
  );
}
