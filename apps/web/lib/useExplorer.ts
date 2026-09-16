"use client";

import { useCallback, useDeferredValue, useMemo } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";

import {
  Benchmark,
  Catalogue,
  Detail,
  getJSON,
  HistoricalPoint,
  IndexRow,
  LayerName,
  Product,
} from "@/lib/api";

import { isLayer, universe } from "@/lib/format";

export type MapValue = {
  cod_ine: string;
  valor: number | null;
  categoria: string | null;
};

export type ExplorerView = "mapa" | "lista";

const SELECTION_KEYS = [
  "capa",
  "producto",
  "anio",
  "ccaa",
  "provincia",
  "min",
  "max",
  "buscar",
];

/** La hoja municipal vive fuera del explorador, en su propia ruta. */
const FICHA_BASE = "/municipio";

/**
 * Estado del explorador: la URL es la fuente de verdad, de modo que cualquier
 * vista se puede compartir y recargar tal cual.
 */
export function useExplorer(basePath: string) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const rawLayer = searchParams.get("capa");
  const layer: LayerName = isLayer(rawLayer) ? rawLayer : "ipr";
  const product: Product =
    searchParams.get("producto") === "prospectivo" ? "prospectivo" : "observado";
  const year = Number(searchParams.get("anio") || 2023);
  const ccaa = searchParams.get("ccaa") || "";
  const province = searchParams.get("provincia") || "";
  const minScore = Math.min(100, Math.max(0, Number(searchParams.get("min") || 0)));
  const maxScore = Math.min(
    100,
    Math.max(minScore, Number(searchParams.get("max") || 100)),
  );
  const search = searchParams.get("buscar") || "";
  const deferredSearch = useDeferredValue(search);
  const selected = searchParams.get("municipio");
  const view: ExplorerView = searchParams.get("vista") === "lista" ? "lista" : "mapa";

  const queryProduct: Product =
    layer === "ipr" ? product : layer === "riesgo_futuro" ? "prospectivo" : "observado";
  const detailProduct: Product = layer === "riesgo_futuro" ? "prospectivo" : product;

  const update = useCallback(
    (changes: Record<string, string | null>) => {
      const params = new URLSearchParams(searchParams);
      const changesSelection = Object.keys(changes).some((key) =>
        SELECTION_KEYS.includes(key),
      );
      if (changesSelection && !("municipio" in changes)) params.delete("municipio");
      Object.entries(changes).forEach(([key, value]) => {
        if (!value) params.delete(key);
        else params.set(key, value);
      });
      const query = params.toString();
      router.replace(query ? `${basePath}?${query}` : basePath, { scroll: false });
    },
    [basePath, router, searchParams],
  );

  const clear = useCallback(() => {
    router.replace(view === "lista" ? `${basePath}?vista=lista` : basePath, {
      scroll: false,
    });
  }, [basePath, router, view]);

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

  const baseQuery = new URLSearchParams({
    anio: String(year),
    producto: queryProduct,
    capa: layer,
  });
  if (ccaa) baseQuery.set("ccaa", ccaa);
  if (province) baseQuery.set("provincia", province);

  const query = new URLSearchParams(baseQuery);
  query.set("min_score", String(minScore));
  query.set("max_score", String(maxScore));
  if (deferredSearch) query.set("search", deferredSearch);

  const index = useQuery({
    queryKey: [
      "index",
      year,
      queryProduct,
      layer,
      ccaa,
      province,
      minScore,
      maxScore,
      deferredSearch,
    ],
    queryFn: () =>
      getJSON<{ items: IndexRow[]; total: number; year_options: number[] }>(
        `/api/v1/indice?${query}`,
      ),
    placeholderData: keepPreviousData,
  });

  const mapQuery = new URLSearchParams(query);
  mapQuery.delete("search");
  const values = useQuery({
    queryKey: ["map-values", year, queryProduct, layer, ccaa, province, minScore, maxScore],
    queryFn: () => getJSON<MapValue[]>(`/api/v1/mapa/valores?${mapQuery}`),
    placeholderData: keepPreviousData,
  });

  // Distribución sin el filtro de puntuación, para los histogramas.
  const distributionQuery = new URLSearchParams(baseQuery);
  distributionQuery.set("min_score", "0");
  distributionQuery.set("max_score", "100");
  const distribution = useQuery({
    queryKey: ["map-values", year, queryProduct, layer, ccaa, province, 0, 100],
    queryFn: () => getJSON<MapValue[]>(`/api/v1/mapa/valores?${distributionQuery}`),
    placeholderData: keepPreviousData,
  });

  const items = useMemo(() => index.data?.items ?? [], [index.data?.items]);
  const visibleIds = useMemo(() => items.map((item) => item.cod_ine), [items]);
  const scores = useMemo(
    () =>
      (distribution.data ?? [])
        .map((item) => item.valor)
        .filter((value): value is number => value != null),
    [distribution.data],
  );
  const provinces = useMemo(
    () =>
      catalogue.data?.regions.find((region) => region.comunidad_autonoma === ccaa)
        ?.provincias ?? [],
    [catalogue.data, ccaa],
  );
  const filterActive =
    Boolean(ccaa || province || deferredSearch) || minScore > 0 || maxScore < 100;
  const mean =
    items.length > 0
      ? items.reduce((total, item) => total + (item.score ?? 0), 0) / items.length
      : null;
  const selectedItem = items.find((item) => item.cod_ine === selected) ?? null;

  const fichaHref = useCallback(
    (codIne: string) => {
      const params = new URLSearchParams(searchParams);
      params.set("municipio", codIne);
      params.set("producto", layer === "riesgo_futuro" ? "prospectivo" : product);
      return `${FICHA_BASE}/${codIne}?${params}`;
    },
    [layer, product, searchParams],
  );

  const viewHref = useCallback(
    (next: ExplorerView) => {
      const params = new URLSearchParams(searchParams);
      if (next === "lista") params.set("vista", "lista");
      else params.delete("vista");
      const query = params.toString();
      return query ? `${basePath}?${query}` : basePath;
    },
    [basePath, searchParams],
  );

  return {
    viewHref,
    layer,
    product,
    year,
    ccaa,
    province,
    minScore,
    maxScore,
    search,
    selected,
    view,
    queryProduct,
    detailProduct,
    update,
    clear,
    select: (codIne: string | null) => update({ municipio: codIne }),
    setView: (next: ExplorerView) => update({ vista: next === "lista" ? "lista" : null }),
    catalogue,
    geometry,
    index,
    values,
    items,
    visibleIds,
    scores,
    provinces,
    filterActive,
    mean,
    selectedItem,
    universe: universe(queryProduct),
    isLoading: index.isLoading || values.isLoading || geometry.isLoading,
    hasError: index.isError || values.isError || geometry.isError,
    isFetching: index.isFetching || values.isFetching,
    retry: () => {
      geometry.refetch();
      values.refetch();
      index.refetch();
    },
    fichaHref,
  };
}

export type Explorer = ReturnType<typeof useExplorer>;

export function useMunicipality(
  codIne: string | null,
  product: Product,
  options: { history?: boolean; benchmarks?: boolean } = {},
) {
  const detail = useQuery({
    queryKey: ["detail", codIne, product],
    queryFn: () => getJSON<Detail>(`/api/v1/municipios/${codIne}?producto=${product}`),
    enabled: Boolean(codIne),
    placeholderData: keepPreviousData,
  });
  const history = useQuery({
    queryKey: ["history", codIne],
    queryFn: () => getJSON<HistoricalPoint[]>(`/api/v1/municipios/${codIne}/historico`),
    enabled: Boolean(codIne && options.history),
  });
  const benchmarks = useQuery({
    queryKey: ["benchmarks", codIne, product],
    queryFn: () =>
      getJSON<Benchmark[]>(`/api/v1/municipios/${codIne}/comparativas?producto=${product}`),
    enabled: Boolean(codIne && options.benchmarks),
  });
  return { detail, history, benchmarks };
}

/** Parámetros de la ficha: producto y vuelta al explorador con el mismo estado. */
export function useFichaParams(basePath: string) {
  const searchParams = useSearchParams();
  const product: Product =
    searchParams.get("producto") === "prospectivo" ? "prospectivo" : "observado";
  const back = new URLSearchParams(searchParams);
  const productHref = (codIne: string, next: Product) => {
    const params = new URLSearchParams(searchParams);
    params.set("producto", next);
    return `${FICHA_BASE}/${codIne}?${params}`;
  };
  return {
    product,
    backHref: `${basePath}?${back}`,
    productHref,
  };
}
