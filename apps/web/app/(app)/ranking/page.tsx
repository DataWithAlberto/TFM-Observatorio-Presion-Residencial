"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo } from "react";

import ActiveChips, { type Chip } from "@/components/hoja/ActiveChips";
import { CartoucheStrip } from "@/components/hoja/Cartouche";
import FiltersPanel from "@/components/hoja/FiltersPanel";
import LayerTabs from "@/components/hoja/LayerTabs";
import RelationTable, { type Sort, type SortKey } from "@/components/hoja/RelationTable";
import { StatusLine } from "@/components/hoja/Status";
import TitleBlock from "@/components/hoja/TitleBlock";
import {
  API,
  type Catalogue,
  getJSON,
  type IndexRow,
  type LayerName,
  type Product,
} from "@/lib/api";
import { isLayer, placeName, PRODUCT_NAMES, universe } from "@/lib/format";

import styles from "./ranking.module.css";

/** Las cuatro ordenaciones que ofrece el selector, con su rótulo. */
const SORT_OPTIONS: { value: string; label: string }[] = [
  { value: "ranking", label: "Puesto" },
  { value: "score_desc", label: "Mayor puntuación" },
  { value: "score_asc", label: "Menor puntuación" },
  { value: "nombre", label: "Nombre A–Z" },
];

const SORT_KEYS: SortKey[] = [
  "ranking",
  "nombre",
  "provincia",
  "comunidad_autonoma",
  "score",
];

/**
 * `orden` admite los cuatro valores del selector y, además, cualquier columna
 * con sufijo `_desc`, que es lo que producen las cabeceras de la tabla.
 */
function parseSort(raw: string | null): Sort {
  const value = raw ?? "ranking";
  const desc = value.endsWith("_desc");
  const key = value.replace(/_(desc|asc)$/, "") as SortKey;
  if (!SORT_KEYS.includes(key)) return { key: "ranking", dir: 1 };
  return { key, dir: desc ? -1 : 1 };
}

function serializeSort(sort: Sort): string | null {
  if (sort.key === "ranking" && sort.dir === 1) return null;
  return sort.dir === -1 ? `${sort.key}_desc` : `${sort.key}_asc`;
}

/** Frase de lectura: cuántos municipios se ven y con qué orden. */
function readingFor(count: number, sort: Sort): string {
  const noun = count === 1 ? "municipio" : "municipios";
  const option = SORT_OPTIONS.find((item) => serializeSort(parseSort(item.value)) === serializeSort(sort));
  const order = option ? option.label.toLowerCase() : "la columna elegida";
  if (count === 0) return "Ningún municipio cumple los filtros.";
  return `${count} ${noun} · ordenados por ${order}.`;
}

function Relation() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const rawLayer = searchParams.get("capa");
  const layer: LayerName = isLayer(rawLayer) ? rawLayer : "ipr";
  const product: Product =
    searchParams.get("producto") === "prospectivo" ? "prospectivo" : "observado";
  const queryProduct: Product =
    layer === "ipr" ? product : layer === "riesgo_futuro" ? "prospectivo" : "observado";
  const detailProduct: Product = layer === "riesgo_futuro" ? "prospectivo" : product;
  const ccaa = searchParams.get("ccaa") || "";
  const province = searchParams.get("provincia") || "";
  // `search` se sigue leyendo por compatibilidad con enlaces antiguos.
  const search = searchParams.get("buscar") || searchParams.get("search") || "";
  const minScore = Math.min(100, Math.max(0, Number(searchParams.get("min") || 0)));
  const maxScore = Math.min(100, Math.max(minScore, Number(searchParams.get("max") || 100)));
  const sort = parseSort(searchParams.get("orden"));

  const update = (changes: Record<string, string | null>) => {
    const query = new URLSearchParams(searchParams);
    Object.entries(changes).forEach(([key, value]) => {
      if (!value) query.delete(key);
      else query.set(key, value);
    });
    const next = query.toString();
    router.replace(next ? `/ranking?${next}` : "/ranking", { scroll: false });
  };

  const catalogue = useQuery({
    queryKey: ["catalogue"],
    queryFn: () => getJSON<Catalogue>("/api/v1/catalogo"),
    staleTime: 300_000,
  });
  const regions = catalogue.data?.regions.map((region) => region.comunidad_autonoma) ?? [];
  const provinces =
    catalogue.data?.regions.find((region) => region.comunidad_autonoma === ccaa)
      ?.provincias ?? [];

  const apiQuery = new URLSearchParams({
    producto: queryProduct,
    capa: layer,
    min_score: String(minScore),
    max_score: String(maxScore),
  });
  if (ccaa) apiQuery.set("ccaa", ccaa);
  if (province) apiQuery.set("provincia", province);
  if (search) apiQuery.set("search", search);

  const ranking = useQuery({
    queryKey: ["ranking", queryProduct, layer, ccaa, province, search, minScore, maxScore],
    queryFn: () => getJSON<IndexRow[]>(`/api/v1/ranking?${apiQuery}`),
  });
  const items = useMemo(() => ranking.data ?? [], [ranking.data]);

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
  if (minScore > 0 || maxScore < 100) {
    chips.push({
      key: "rango",
      label: `Puntuación ${minScore}–${maxScore}`,
      onRemove: () => update({ min: null, max: null }),
    });
  }
  if (search) {
    chips.push({
      key: "buscar",
      label: `«${search}»`,
      onRemove: () => update({ buscar: null, search: null }),
    });
  }
  const filterCount = chips.filter((chip) => chip.key !== "buscar").length;

  const fichaHref = (codIne: string) => `/municipio/${codIne}?producto=${detailProduct}`;

  return (
    <div className={styles.relation} data-sheet="fixed">
      <div className={styles.tabs}>
        <LayerTabs value={layer} onChange={(capa) => update({ capa })} />
        <a className={styles.download} href={`${API}/api/v1/ranking?${exportQuery}`}>
          Descargar tabla (.csv)
        </a>
        <FiltersPanel
          ccaa={ccaa}
          province={province}
          regions={regions}
          provinces={provinces}
          score={{
            min: minScore,
            max: maxScore,
            values: items
              .map((item) => item.score)
              .filter((value): value is number => value != null),
          }}
          count={filterCount}
          onChange={update}
          onClear={() => router.replace("/ranking", { scroll: false })}
        >
          <label className={styles.sortField}>
            <span>Ordenar</span>
            <select
              value={serializeSort(sort) ?? "ranking"}
              onChange={(event) => update({ orden: event.target.value || null })}
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </FiltersPanel>
      </div>

      <section className={styles.main} aria-labelledby="titulo-de-vista">
        <TitleBlock
          title="Relación de municipios"
          reading={readingFor(items.length, sort)}
          hint="Pulsa un municipio para abrir su hoja."
          chips={<ActiveChips chips={chips} />}
        />

        <div className={styles.tableFrame}>
          <StatusLine
            loading={ranking.isLoading}
            error={ranking.isError}
            retry={() => ranking.refetch()}
          />
          <RelationTable
            items={items}
            selected={null}
            onSelect={(codIne) => router.push(fichaHref(codIne))}
            fichaHref={fichaHref}
            scoreLabel={PRODUCT_NAMES[queryProduct].code}
            sort={sort}
            onSortChange={(next) => update({ orden: serializeSort(next) })}
          />
        </div>
      </section>

      <CartoucheStrip
        cells={[
          { label: "Resultado", value: PRODUCT_NAMES[queryProduct].code },
          { label: "Corte", value: 2023 },
          { label: "Municipios", value: `${items.length} de ${universe(queryProduct)}` },
          { label: "Referencia", value: "WGS84" },
        ]}
      />
    </div>
  );
}

export default function RankingPage() {
  return (
    <Suspense fallback={<StatusLine loading>Cargando la relación…</StatusLine>}>
      <Relation />
    </Suspense>
  );
}
