"use client";

import Map from "@/components/Map";
import { StatusLine } from "@/components/hoja/Status";
import { HOJA_MAP_THEME } from "@/lib/mapTheme";
import type { Explorer } from "@/lib/useExplorer";

import styles from "./map-frame.module.css";

/** El mapa del explorador, conectado al estado de la URL. */
export default function ExplorerMap({ explorer }: { explorer: Explorer }) {
  if (explorer.isLoading || explorer.hasError) {
    return (
      <div className={styles.status}>
        <StatusLine
          loading={explorer.isLoading}
          error={explorer.hasError}
          retry={explorer.retry}
        >
          Preparando el mapa de los 306 municipios…
        </StatusLine>
      </div>
    );
  }

  // La capa de calidad no es una presión: va en su propia escala de cuatro
  // niveles y con su propio nombre, para que nadie la lea como un factor más.
  const quality = explorer.layer === "calidad";

  return (
    <Map
      geometry={explorer.geometry.data!}
      values={explorer.values.data!}
      visibleIds={explorer.visibleIds}
      filterActive={explorer.filterActive}
      selectedId={explorer.selected}
      onSelect={(id) => explorer.select(id)}
      colorScale={quality ? "quality" : "sequential"}
      valueLabel={quality ? "Calidad del dato" : "Puntuación"}
      ariaLabel={
        quality
          ? "Mapa interactivo de calidad del dato"
          : "Mapa interactivo de presión sobre la vivienda"
      }
      busy={explorer.isFetching}
      theme={HOJA_MAP_THEME}
    />
  );
}
