"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useDeferredValue, useMemo } from "react";

import { ProspectiveScatterChart } from "@/components/Chart";
import Map from "@/components/Map";
import ActiveChips, { type Chip } from "@/components/hoja/ActiveChips";
import { CartoucheStrip } from "@/components/hoja/Cartouche";
import FiltersPanel from "@/components/hoja/FiltersPanel";
import MapFrame from "@/components/hoja/MapFrame";
import { StatusLine } from "@/components/hoja/Status";
import TitleBlock from "@/components/hoja/TitleBlock";
import {
  API,
  type Catalogue,
  getJSON,
  type ProspectiveContrast,
  type ProspectiveContrastRow,
} from "@/lib/api";
import { fmt, placeName } from "@/lib/format";
import { HOJA_MAP_THEME } from "@/lib/mapTheme";

import styles from "./prospectiva.module.css";

const DOMAIN_MIN = -15;
const DOMAIN_MAX = 15;

type View = "mapa" | "cambios" | "dispersion" | "tabla";

const VIEWS: { id: View; label: string }[] = [
  { id: "mapa", label: "Mapa de diferencias" },
  { id: "cambios", label: "Dónde más cambia" },
  { id: "dispersion", label: "Relación entre resultados" },
  { id: "tabla", label: "Tabla" },
];

function boundedNumber(value: string | null, fallback: number) {
  const parsed = Number(value ?? fallback);
  return Number.isFinite(parsed)
    ? Math.min(DOMAIN_MAX, Math.max(DOMAIN_MIN, parsed))
    : fallback;
}

/** Diferencia con signo explícito: un «+0,4» no se confunde con un «−0,4». */
function formatGap(value: number | null, suffix = " puntos") {
  if (value == null) return "—";
  return `${value > 0 ? "+" : value < 0 ? "−" : ""}${fmt(Math.abs(value))}${suffix}`;
}

function Prospective() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const ccaa = searchParams.get("ccaa") || "";
  const province = searchParams.get("provincia") || "";
  const search = searchParams.get("buscar") || "";
  const deferredSearch = useDeferredValue(search);
  const minGap = boundedNumber(searchParams.get("min"), DOMAIN_MIN);
  const maxGap = Math.max(minGap, boundedNumber(searchParams.get("max"), DOMAIN_MAX));
  const selected = searchParams.get("municipio");
  const rawView = searchParams.get("vista");
  const view: View = VIEWS.some((item) => item.id === rawView) ? (rawView as View) : "mapa";

  const update = useCallback(
    (changes: Record<string, string | null>) => {
      const params = new URLSearchParams(searchParams);
      const changesSelection = Object.keys(changes).some((key) =>
        ["ccaa", "provincia", "buscar", "min", "max"].includes(key),
      );
      if (changesSelection && !("municipio" in changes)) params.delete("municipio");
      Object.entries(changes).forEach(([key, value]) => {
        if (!value) params.delete(key);
        else params.set(key, value);
      });
      const query = params.toString();
      router.replace(query ? `/prospectiva?${query}` : "/prospectiva", { scroll: false });
    },
    [router, searchParams],
  );

  const catalogue = useQuery({
    queryKey: ["catalogue"],
    queryFn: () => getJSON<Catalogue>("/api/v1/catalogo"),
    staleTime: 300_000,
  });
  const geometry = useQuery({
    queryKey: ["geometry"],
    queryFn: () => getJSON<GeoJSON.FeatureCollection>("/api/v1/mapa/geometrias"),
    staleTime: 86_400_000,
  });
  const regions = catalogue.data?.regions.map((region) => region.comunidad_autonoma) ?? [];
  const provinces = useMemo(
    () =>
      catalogue.data?.regions.find((region) => region.comunidad_autonoma === ccaa)
        ?.provincias ?? [],
    [catalogue.data, ccaa],
  );

  const apiQuery = new URLSearchParams({
    min_brecha: String(minGap),
    max_brecha: String(maxGap),
  });
  if (ccaa) apiQuery.set("ccaa", ccaa);
  if (province) apiQuery.set("provincia", province);
  if (deferredSearch) apiQuery.set("search", deferredSearch);

  const contrast = useQuery({
    queryKey: ["prospective-contrast", ccaa, province, deferredSearch, minGap, maxGap],
    queryFn: () => getJSON<ProspectiveContrast>(`/api/v1/prospectiva?${apiQuery}`),
    placeholderData: keepPreviousData,
  });

  const items = useMemo(() => contrast.data?.items ?? [], [contrast.data?.items]);
  const summary = contrast.data?.resumen;
  const visibleIds = useMemo(() => items.map((item) => item.cod_ine), [items]);
  const selectedItem = items.find((item) => item.cod_ine === selected);
  const mapValues = useMemo(
    () =>
      items.map((item) => ({
        cod_ine: item.cod_ine,
        valor: item.brecha,
        categoria: null,
      })),
    [items],
  );
  const tooltipDetails = useMemo(
    () =>
      Object.fromEntries(
        items.map((item) => [
          item.cod_ine,
          {
            ipr4: item.ipr4_observado,
            ipr5: item.ipr5_prospectivo,
            riesgoFuturo: item.riesgo_futuro,
          },
        ]),
      ),
    [items],
  );

  const withGap = (direction: 1 | -1) =>
    items
      .filter(
        (item): item is ProspectiveContrastRow & { brecha: number } =>
          item.brecha != null && item.brecha * direction > 0,
      )
      .sort((a, b) => (b.brecha - a.brecha) * direction)
      .slice(0, 5);
  const rising = withGap(1);
  const falling = withGap(-1);

  const filterActive =
    Boolean(ccaa || province || deferredSearch) || minGap > DOMAIN_MIN || maxGap < DOMAIN_MAX;
  const exportQuery = new URLSearchParams(apiQuery);
  exportQuery.set("formato", "csv");

  const chips: Chip[] = [];
  if (ccaa) {
    chips.push({
      key: "ccaa",
      label: ccaa,
      onRemove: () => update({ ccaa: null, provincia: null }),
    });
  }
  if (province) {
    chips.push({
      key: "provincia",
      label: placeName(province),
      onRemove: () => update({ provincia: null }),
    });
  }
  if (minGap > DOMAIN_MIN || maxGap < DOMAIN_MAX) {
    chips.push({
      key: "rango",
      label: `Diferencia ${formatGap(minGap, "")} a ${formatGap(maxGap, "")}`,
      onRemove: () => update({ min: null, max: null }),
    });
  }
  if (search) {
    chips.push({
      key: "buscar",
      label: `«${search}»`,
      onRemove: () => update({ buscar: null }),
    });
  }
  const filterCount = chips.filter((chip) => chip.key !== "buscar").length;

  // Frase de lectura: el recuento real de los municipios comparables.
  const reading = summary
    ? `De ${summary.comparables} municipios comparables, ${summary.ipr5_mayor} suben y ${summary.ipr5_menor} bajan al añadir el riesgo.`
    : "Cargando la comparación…";

  const loading = geometry.isLoading || contrast.isLoading;
  const failed = geometry.isError || contrast.isError;

  return (
    <div className={styles.prospective} data-sheet="fixed">
      <div className={styles.tabs}>
        <div className={styles.views} role="radiogroup" aria-label="Qué quieres ver">
          {VIEWS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="radio"
              aria-checked={view === item.id}
              tabIndex={view === item.id ? 0 : -1}
              className={styles.view}
              onClick={() => update({ vista: item.id === "mapa" ? null : item.id, municipio: selected })}
            >
              {item.label}
            </button>
          ))}
        </div>
        <a className={styles.download} href={`${API}/api/v1/prospectiva?${exportQuery}`}>
          Descargar datos
        </a>
        <FiltersPanel
          ccaa={ccaa}
          province={province}
          regions={regions}
          provinces={provinces}
          count={filterCount}
          onChange={update}
          onClear={() => router.replace("/prospectiva", { scroll: false })}
        >
          <div className={styles.gapField}>
            <span>
              Diferencia de {formatGap(minGap)} a {formatGap(maxGap)}
            </span>
            <div>
              <input
                aria-label="Diferencia mínima"
                type="number"
                min={DOMAIN_MIN}
                max={maxGap}
                step="0.5"
                value={minGap}
                onChange={(event) => update({ min: event.target.value })}
              />
              <input
                aria-label="Diferencia máxima"
                type="number"
                min={minGap}
                max={DOMAIN_MAX}
                step="0.5"
                value={maxGap}
                onChange={(event) => update({ max: event.target.value })}
              />
            </div>
          </div>
        </FiltersPanel>
      </div>

      <div className={styles.body}>
        <section className={styles.main} aria-labelledby="titulo-de-vista">
          <TitleBlock
            title="Cómo cambia el resultado al añadir el riesgo futuro"
            reading={reading}
            hint="No dice cómo será el municipio en el futuro."
            chips={<ActiveChips chips={chips} />}
          />

          {loading || failed ? (
            <StatusLine
              loading={loading}
              error={failed}
              retry={() => {
                geometry.refetch();
                contrast.refetch();
              }}
            >
              Preparando la comparación…
            </StatusLine>
          ) : view === "mapa" ? (
            <MapFrame
              legend={
                <div className={styles.legend} aria-label="Leyenda">
                  <small>Diferencia IPR-5 − IPR-4</small>
                  <div className={styles.ramp}>
                    <span>−15</span>
                    <i />
                    <span>+15</span>
                  </div>
                  <p className={styles.missing}>
                    <b /> No se puede comparar
                  </p>
                  <details className={styles.explainer}>
                    <summary>Ver cómo se calcula</summary>
                    <p className={styles.formula}>
                      IPR-5 = 0,85 × IPR-4 + 0,15 × riesgo futuro
                    </p>
                  </details>
                </div>
              }
            >
              <Map
                geometry={geometry.data!}
                values={mapValues}
                visibleIds={visibleIds}
                filterActive={filterActive}
                selectedId={selectedItem?.cod_ine ?? null}
                onSelect={(id) => update({ municipio: id })}
                colorScale="divergent"
                valueLabel="Diferencia"
                busy={contrast.isFetching}
                tooltipDetails={tooltipDetails}
                theme={HOJA_MAP_THEME}
              />
            </MapFrame>
          ) : view === "cambios" ? (
            <div className={styles.frame}>
              <div className={styles.changeColumns}>
                {[
                  { title: "Suben más", rows: rising },
                  { title: "Bajan más", rows: falling },
                ].map((column) => (
                  <div key={column.title}>
                    <h2 className={styles.blockTitle}>{column.title}</h2>
                    <ol className={styles.changeList}>
                      {column.rows.map((item) => (
                        <li key={item.cod_ine}>
                          <button
                            type="button"
                            aria-label={`Seleccionar ${placeName(item.nombre)}`}
                            onClick={() => update({ municipio: item.cod_ine })}
                          >
                            <span>
                              <b>{placeName(item.nombre)}</b>
                              <small>{placeName(item.provincia)}</small>
                            </span>
                            <strong>{formatGap(item.brecha, "")}</strong>
                          </button>
                        </li>
                      ))}
                    </ol>
                  </div>
                ))}
              </div>
            </div>
          ) : view === "dispersion" ? (
            <div className={styles.frame}>
              <ProspectiveScatterChart
                items={items}
                selectedId={selectedItem?.cod_ine ?? null}
              />
            </div>
          ) : (
            <div className={styles.frame}>
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th scope="col">Municipio</th>
                      <th scope="col">Provincia</th>
                      <th scope="col" className={styles.num}>
                        IPR-4
                      </th>
                      <th scope="col" className={styles.num}>
                        Riesgo futuro
                      </th>
                      <th scope="col" className={styles.num}>
                        IPR-5
                      </th>
                      <th scope="col" className={styles.num}>
                        Diferencia
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item) => (
                      <tr
                        key={item.cod_ine}
                        aria-selected={item.cod_ine === selectedItem?.cod_ine}
                      >
                        <td>
                          <button
                            type="button"
                            className={styles.rowSelect}
                            aria-label={`Seleccionar ${placeName(item.nombre)}`}
                            onClick={() => update({ municipio: item.cod_ine })}
                          >
                            {placeName(item.nombre)}
                          </button>
                        </td>
                        <td>{placeName(item.provincia)}</td>
                        <td className={styles.num}>{fmt(item.ipr4_observado)}</td>
                        <td className={styles.num}>{fmt(item.riesgo_futuro)}</td>
                        <td className={styles.num}>{fmt(item.ipr5_prospectivo)}</td>
                        <td className={styles.num}>{formatGap(item.brecha, "")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>

        <aside
          className={styles.side}
          aria-label={selectedItem ? "Municipio seleccionado" : "Resumen de la comparación"}
        >
          {selectedItem ? (
            <section
              className={`${styles.selected} contrast-selected`}
              data-ipr4={selectedItem.ipr4_observado}
              data-ipr5={selectedItem.ipr5_prospectivo ?? ""}
              data-gap={selectedItem.brecha ?? ""}
              aria-live="polite"
            >
              <button
                type="button"
                className={styles.backLink}
                onClick={() => update({ municipio: null })}
              >
                ← El resumen
              </button>
              <h2>{placeName(selectedItem.nombre)}</h2>
              <p className={styles.place}>{placeName(selectedItem.provincia)}</p>
              <dl className={styles.values}>
                <div>
                  <dt>Situación actual · IPR-4</dt>
                  <dd>{fmt(selectedItem.ipr4_observado)}</dd>
                </div>
                <div>
                  <dt>Riesgo futuro</dt>
                  <dd>{fmt(selectedItem.riesgo_futuro)}</dd>
                </div>
                <div>
                  <dt>Con riesgo futuro · IPR-5</dt>
                  <dd>{fmt(selectedItem.ipr5_prospectivo)}</dd>
                </div>
                <div className={styles.gapRow}>
                  <dt>Diferencia</dt>
                  <dd>{formatGap(selectedItem.brecha, "")}</dd>
                </div>
              </dl>
              <p className={styles.note}>
                {selectedItem.brecha == null
                  ? "No se puede comparar: falta el dato de riesgo futuro y no lo rellenamos con una estimación."
                  : "Esta diferencia aparece al reservar un 15 % de la puntuación al riesgo futuro. No representa un cambio a lo largo del tiempo."}
              </p>
              <Link
                className={styles.sideLink}
                href={`/municipio/${selectedItem.cod_ine}?producto=prospectivo`}
              >
                Abrir la hoja del municipio
              </Link>
            </section>
          ) : (
            <section className={styles.summary}>
              <h2 className={styles.blockTitle}>Resumen de la comparación</h2>
              <dl className={styles.values}>
                <div>
                  <dt>Se pueden comparar</dt>
                  <dd>{summary?.comparables ?? "—"}</dd>
                </div>
                <div>
                  <dt>Suben</dt>
                  <dd>{summary?.ipr5_mayor ?? "—"}</dd>
                </div>
                <div>
                  <dt>Bajan</dt>
                  <dd>{summary?.ipr5_menor ?? "—"}</dd>
                </div>
                <div>
                  <dt>Diferencia media</dt>
                  <dd>{formatGap(summary?.brecha_media ?? null, "")}</dd>
                </div>
              </dl>
              <p className={styles.note}>
                303 con ambas puntuaciones · 3 sin datos suficientes
              </p>
              <p className={styles.hint}>
                Pulsa un municipio en el mapa o en las listas para ver su detalle.
              </p>
            </section>
          )}
        </aside>
      </div>

      <CartoucheStrip
        cells={[
          { label: "Resultado", value: "IPR-5 − IPR-4" },
          { label: "Corte", value: 2023 },
          {
            label: "Municipios",
            value: `${summary?.comparables ?? "—"} de 303 comparables`,
          },
          { label: "Escenario", value: "2041–2060" },
        ]}
      />
    </div>
  );
}

export default function ProspectivePage() {
  return (
    <Suspense fallback={<StatusLine loading>Cargando la comparación…</StatusLine>}>
      <Prospective />
    </Suspense>
  );
}
