"use client";

import { useQuery } from "@tanstack/react-query";

import Map from "@/components/Map";
import { StatusLine } from "@/components/hoja/Status";
import { getJSON, type Product } from "@/lib/api";
import { HOJA_MAP_THEME_EMBEDDED } from "@/lib/mapTheme";
import type { MapValue } from "@/lib/useExplorer";

import styles from "./map-frame.module.css";

/**
 * Mapa de situación de la ficha: centra y resalta un municipio. Va con gestos
 * cooperativos porque vive dentro de una página con scroll.
 */
export default function LocatorMap({
  codIne,
  product,
}: {
  codIne: string;
  product: Product;
}) {
  const geometry = useQuery({
    queryKey: ["geometry"],
    queryFn: () => getJSON<GeoJSON.FeatureCollection>("/api/v1/mapa/geometrias"),
    staleTime: 86_400_000,
  });
  const values = useQuery({
    queryKey: ["map-values", 2023, product, "ipr", "", "", 0, 100],
    queryFn: () =>
      getJSON<MapValue[]>(
        `/api/v1/mapa/valores?anio=2023&producto=${product}&capa=ipr&min_score=0&max_score=100`,
      ),
  });

  if (!geometry.data || !values.data) {
    return (
      <div className={styles.status}>
        <StatusLine
          loading={geometry.isLoading || values.isLoading}
          error={geometry.isError || values.isError}
        >
          Cargando el mapa de situación…
        </StatusLine>
      </div>
    );
  }

  return (
    <Map
      geometry={geometry.data}
      values={values.data}
      visibleIds={[]}
      filterActive={false}
      selectedId={codIne}
      onSelect={() => undefined}
      valueLabel="Puntuación"
      theme={HOJA_MAP_THEME_EMBEDDED}
    />
  );
}
