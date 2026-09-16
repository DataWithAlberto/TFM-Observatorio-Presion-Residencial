"use client";

import { Suspense } from "react";

import ActiveChips, { type Chip } from "@/components/hoja/ActiveChips";
import { CartoucheStrip } from "@/components/hoja/Cartouche";
import ExplorerMap from "@/components/hoja/ExplorerMap";
import FiltersPanel from "@/components/hoja/FiltersPanel";
import LayerTabs from "@/components/hoja/LayerTabs";
import MapFrame from "@/components/hoja/MapFrame";
import mapStyles from "@/components/hoja/map-frame.module.css";
import QualityScale from "@/components/hoja/QualityScale";
import MunicipalityPanel from "@/components/hoja/MunicipalityPanel";
import ProductSwitch from "@/components/hoja/ProductSwitch";
import RelationTable from "@/components/hoja/RelationTable";
import { StatusLine } from "@/components/hoja/Status";
import TitleBlock from "@/components/hoja/TitleBlock";
import TopTen from "@/components/hoja/TopTen";
import { layerLabel, placeName, PRODUCT_NAMES } from "@/lib/format";
import { readingFor } from "@/lib/reading";
import { useExplorer, useMunicipality } from "@/lib/useExplorer";

import styles from "./observatorio.module.css";

const BASE = "/observatorio";

function Explorer() {
  const explorer = useExplorer(BASE);
  const { detail } = useMunicipality(explorer.selected, explorer.detailProduct);

  const regions =
    explorer.catalogue.data?.regions.map((region) => region.comunidad_autonoma) ?? [];
  const selectedDetail =
    explorer.selected && detail.data?.cod_ine === explorer.selected ? detail.data : null;
  const isTotal = explorer.layer === "ipr";
  const isQuality = explorer.layer === "calidad";
  const reading = readingFor(explorer.items, explorer.ccaa, explorer.layer);

  const chips: Chip[] = [];
  if (explorer.ccaa) {
    chips.push({
      key: "ccaa",
      label: explorer.ccaa,
      onRemove: () => explorer.update({ ccaa: null, provincia: null }),
    });
  }
  if (explorer.province) {
    chips.push({
      key: "provincia",
      label: placeName(explorer.province),
      onRemove: () => explorer.update({ provincia: null }),
    });
  }
  if (explorer.minScore > 0 || explorer.maxScore < 100) {
    chips.push({
      key: "rango",
      label: `Puntuación ${explorer.minScore}–${explorer.maxScore}`,
      onRemove: () => explorer.update({ min: null, max: null }),
    });
  }
  if (explorer.search) {
    chips.push({
      key: "buscar",
      label: `«${explorer.search}»`,
      onRemove: () => explorer.update({ buscar: null }),
    });
  }
  const filterCount = chips.filter((chip) => chip.key !== "buscar").length;

  return (
    <div className={styles.explorer} data-sheet="fixed">
      <div className={styles.tabs}>
        <LayerTabs value={explorer.layer} onChange={(capa) => explorer.update({ capa })} />
        <FiltersPanel
          ccaa={explorer.ccaa}
          province={explorer.province}
          regions={regions}
          provinces={explorer.provinces}
          score={{
            min: explorer.minScore,
            max: explorer.maxScore,
            values: explorer.scores,
          }}
          count={filterCount}
          onChange={explorer.update}
          onClear={explorer.clear}
        />
      </div>

      <div className={styles.body}>
        <section className={styles.main} aria-labelledby="titulo-de-vista">
          <TitleBlock
            title={layerLabel(explorer.layer)}
            aside={
              <ProductSwitch
                layer={explorer.layer}
                product={explorer.product}
                onChange={(producto) => explorer.update({ producto, municipio: null })}
              />
            }
            reading={reading}
            hint={
              isQuality
                ? "Cuanto más oscuro, mayor cobertura y actualidad de los datos del IPR-4. No mide presión."
                : `Cuanto más oscuro, ${
                    isTotal ? "más presión" : "más alto el valor"
                  } frente al resto de municipios estudiados.`
            }
            chips={<ActiveChips chips={chips} />}
          />

          {explorer.view === "mapa" ? (
            <MapFrame
              legendTitle={`${isTotal ? "Presión" : "Valor"} · quintiles`}
              legend={
                isQuality ? (
                  <div className={mapStyles.legend} aria-label="Leyenda">
                    <small>Calidad del dato · niveles</small>
                    <QualityScale />
                  </div>
                ) : undefined
              }
            >
              <ExplorerMap explorer={explorer} />
            </MapFrame>
          ) : (
            <div className={styles.listFrame}>
              <StatusLine
                loading={explorer.index.isLoading}
                error={explorer.index.isError}
                retry={explorer.retry}
              />
              <RelationTable
                items={explorer.items}
                selected={explorer.selected}
                onSelect={(codIne) => explorer.select(codIne)}
                fichaHref={explorer.fichaHref}
                scoreLabel={PRODUCT_NAMES[explorer.queryProduct].code}
              />
            </div>
          )}
        </section>

        <aside
          className={styles.side}
          aria-label={explorer.selected ? "Municipio seleccionado" : "Primeros puestos"}
        >
          {explorer.selected ? (
            <MunicipalityPanel
              codIne={explorer.selected}
              item={explorer.selectedItem}
              detail={selectedDetail}
              universe={explorer.universe}
              fichaHref={explorer.fichaHref(explorer.selected)}
              onBack={() => explorer.select(null)}
            />
          ) : (
            <TopTen
              items={explorer.items}
              loading={explorer.index.isLoading}
              title={`Los diez ${
                isTotal
                  ? "con más presión"
                  : isQuality
                    ? "con mayor calidad del dato"
                    : "con valores más altos"
              }`}
              listHref={explorer.viewHref("lista")}
              onSelect={(codIne) => explorer.select(codIne)}
            />
          )}
        </aside>
      </div>

      <CartoucheStrip
        cells={[
          { label: "Resultado", value: PRODUCT_NAMES[explorer.queryProduct].code },
          { label: "Corte", value: explorer.year },
          {
            label: "Municipios",
            value: `${explorer.items.length} de ${explorer.universe}`,
          },
          { label: "Referencia", value: "WGS84" },
        ]}
      />
    </div>
  );
}

export default function ObservatoryPage() {
  return (
    <Suspense fallback={<StatusLine loading>Cargando el explorador…</StatusLine>}>
      <Explorer />
    </Suspense>
  );
}
