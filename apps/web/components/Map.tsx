"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { HOJA_MAP_THEME, type MapTheme } from "@/lib/mapTheme";
import maplibregl, {
  type LayerSpecification,
  LngLatBounds,
  Map as MLMap,
  Popup,
  type StyleSpecification,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

type Value = {
  cod_ine: string;
  valor: number | null;
  categoria: string | null;
};

export type MapColorScale = "sequential" | "divergent" | "quality" | "lisa";

export type { MapTheme };

export type MapTooltipDetails = {
  ipr4: number | null;
  ipr5: number | null;
  riesgoFuturo: number | null;
};

export type MapProps = {
  geometry: GeoJSON.FeatureCollection;
  values: Value[];
  visibleIds: string[];
  filterActive: boolean;
  selectedId?: string | null;
  colorScale?: MapColorScale;
  valueLabel?: string;
  busy?: boolean;
  tooltipDetails?: Record<string, MapTooltipDetails>;
  theme?: MapTheme;
  /** Nombre accesible de la región del mapa. */
  ariaLabel?: string;
  onSelect: (id: string) => void;
};

type ViewKey = "peninsula" | "canarias" | "espana";
type Bounds = [[number, number], [number, number]];
type FillLayer = Extract<LayerSpecification, { type: "fill" }>;
type FillColor = NonNullable<
  NonNullable<FillLayer["paint"]>["fill-color"]
>;

const BASEMAP_STYLE = "https://tiles.openfreemap.org/styles/positron";
const BASEMAP_TIMEOUT_MS = 8_000;
const VIEW_PRESETS: Record<
  ViewKey,
  { label: string; bounds: Bounds; maxZoom: number }
> = {
  peninsula: {
    label: "Península",
    bounds: [[-10.2, 35], [5.1, 44.4]],
    maxZoom: 6.2,
  },
  canarias: {
    label: "Canarias",
    bounds: [[-18.5, 27.35], [-13.15, 29.65]],
    maxZoom: 7.2,
  },
  espana: {
    label: "España completa",
    bounds: [[-18.7, 27.1], [5.3, 44.6]],
    maxZoom: 5.2,
  },
};

const FALLBACK_STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [
    {
      id: "background",
      type: "background",
      paint: { "background-color": HOJA_MAP_THEME.fallbackBackground! },
    },
  ],
};

/** Sin tema explícito el mapa se pinta como el resto de la hoja. */
const DEFAULT_SEQUENTIAL = HOJA_MAP_THEME.sequential!;
const DEFAULT_DIVERGENT = HOJA_MAP_THEME.divergent!;

function rampStops(colors: string[], min: number, max: number) {
  return colors.flatMap((color, index) => [
    min + ((max - min) * index) / (colors.length - 1),
    color,
  ]);
}

function scoreRamp(theme: MapTheme | undefined, colorScale: MapColorScale) {
  return colorScale === "divergent"
    ? rampStops(theme?.divergent ?? DEFAULT_DIVERGENT, -15, 15)
    : rampStops(theme?.sequential ?? DEFAULT_SEQUENTIAL, 0, 100);
}

/**
 * Color de un municipio con dato según la escala: rampa continua para
 * puntuaciones, cuatro escalones para la calidad del dato y categorías
 * fijas para las asociaciones LISA, que viajan en `feature-state.category`.
 */
function colorForScale(theme: MapTheme | undefined, colorScale: MapColorScale) {
  if (colorScale === "quality") {
    const q = theme?.quality ?? HOJA_MAP_THEME.quality!;
    return ["step", ["feature-state", "score"], q[0], 50, q[1], 70, q[2], 85, q[3]];
  }
  if (colorScale === "lisa") {
    const l = theme?.lisa ?? HOJA_MAP_THEME.lisa!;
    return [
      "match",
      ["feature-state", "category"],
      "HH", l.HH, "LL", l.LL, "HL", l.HL, "LH", l.LH, "NS", l.NS,
      l.NE,
    ];
  }
  return [
    "interpolate",
    ["linear"],
    ["feature-state", "score"],
    ...scoreRamp(theme, colorScale),
  ];
}

function fillColor(
  colorScale: MapColorScale,
  theme?: MapTheme,
): FillColor {
  const missing = theme?.missing ?? HOJA_MAP_THEME.missing!;
  return [
    "case",
    ["!", ["boolean", ["feature-state", "inScope"], true]],
    missing,
    ["boolean", ["feature-state", "hasData"], false],
    colorForScale(theme, colorScale),
    missing,
  ] as unknown as FillColor;
}

function centroids(geometry: GeoJSON.FeatureCollection) {
  return {
    type: "FeatureCollection",
    features: geometry.features.flatMap((feature) => {
      if (!feature.geometry || !("coordinates" in feature.geometry)) return [];
      const bounds = new LngLatBounds();
      extendBounds(bounds, feature.geometry.coordinates);
      if (bounds.isEmpty()) return [];
      return [
        {
          type: "Feature",
          properties: { ...feature.properties },
          geometry: { type: "Point", coordinates: bounds.getCenter().toArray() },
        },
      ];
    }),
  } as GeoJSON.FeatureCollection;
}

function graticuleLines(): GeoJSON.FeatureCollection {
  const features: GeoJSON.Feature[] = [];
  for (let lon = -20; lon <= 6; lon += 2) {
    features.push({
      type: "Feature",
      properties: {},
      geometry: { type: "LineString", coordinates: [[lon, 26], [lon, 46]] },
    });
  }
  for (let lat = 26; lat <= 46; lat += 2) {
    const coordinates: [number, number][] = [];
    for (let lon = -20; lon <= 6; lon += 0.5) coordinates.push([lon, lat]);
    features.push({
      type: "Feature",
      properties: {},
      geometry: { type: "LineString", coordinates },
    });
  }
  return { type: "FeatureCollection", features };
}

function paintBasemap(map: MLMap, paint: NonNullable<MapTheme["basemapPaint"]>) {
  const roads =
    /(road|street|highway|motorway|trunk|transport|bridge|tunnel|rail|aeroway)/i;
  const landuse = /(landuse|landcover|park|building|aeroway|wood|grass|sand|ice)/i;
  map.getStyle().layers.forEach((layer) => {
    const key = `${layer.id} ${sourceLayerName(layer)}`;
    if (layer.type === "background" && paint.background) {
      map.setPaintProperty(layer.id, "background-color", paint.background);
    } else if (layer.type === "symbol" && paint.hideLabels) {
      map.setLayoutProperty(layer.id, "visibility", "none");
    } else if (layer.type === "symbol" && paint.labelsMinZoom) {
      map.setLayerZoomRange(
        layer.id,
        Math.max(layer.minzoom ?? 0, paint.labelsMinZoom),
        layer.maxzoom ?? 24,
      );
    } else if (layer.type === "fill" && /water/i.test(key) && paint.water) {
      map.setPaintProperty(layer.id, "fill-color", paint.water);
    } else if (layer.type === "fill" && landuse.test(key) && paint.hideLanduse) {
      map.setLayoutProperty(layer.id, "visibility", "none");
    } else if (layer.type === "line" && /water/i.test(key) && paint.water) {
      map.setPaintProperty(layer.id, "line-color", paint.water);
    } else if (layer.type === "line" && /(boundary|admin)/i.test(key)) {
      if (paint.boundary) {
        map.setPaintProperty(layer.id, "line-color", paint.boundary);
      }
    } else if (layer.type === "line" && roads.test(key) && paint.hideRoads) {
      map.setLayoutProperty(layer.id, "visibility", "none");
    }
  });
}

type CircleLayer = Extract<LayerSpecification, { type: "circle" }>;
type CirclePaint = NonNullable<CircleLayer["paint"]>;

function pointColor(theme: MapTheme | undefined, colorScale: MapColorScale) {
  return colorForScale(theme, colorScale) as unknown as CirclePaint["circle-color"];
}

const SCORE = ["feature-state", "score"];
const IN_SCOPE = ["boolean", ["feature-state", "inScope"], true];
const HAS_DATA = ["boolean", ["feature-state", "hasData"], false];
const SELECTED = ["boolean", ["feature-state", "selected"], false];

function byZoom(low: unknown, high: unknown) {
  return ["interpolate", ["linear"], ["zoom"], 4, low, 9, high];
}

function installPointLayers(
  map: MLMap,
  geometry: GeoJSON.FeatureCollection,
  theme: MapTheme,
  colorScale: MapColorScale,
  beforeId: string | undefined,
) {
  map.addSource("municipios-pts", {
    type: "geojson",
    data: centroids(geometry),
    promoteId: "cod_ine",
  });
  const visible = (value: unknown) => [
    "case",
    ["all", IN_SCOPE, HAS_DATA],
    value,
    ["all", ["!", IN_SCOPE], HAS_DATA],
    0.08,
    0,
  ];

  if (theme.points === "glow") {
    map.addLayer(
      {
        id: "municipios-glow",
        type: "circle",
        source: "municipios-pts",
        paint: {
          "circle-color": pointColor(theme, colorScale),
          "circle-radius": byZoom(
            ["+", 5, ["*", SCORE, 0.2]],
            ["+", 14, ["*", SCORE, 0.5]],
          ),
          "circle-blur": 1,
          "circle-opacity": visible([
            "interpolate", ["linear"], SCORE, 0, 0.3, 100, 0.95,
          ]),
        } as unknown as CirclePaint,
      },
      beforeId,
    );
    map.addLayer(
      {
        id: "municipios-core",
        type: "circle",
        source: "municipios-pts",
        paint: {
          "circle-color": pointColor(theme, colorScale),
          "circle-radius": byZoom(
            ["+", 1.4, ["*", SCORE, 0.025]],
            ["+", 3, ["*", SCORE, 0.07]],
          ),
          "circle-opacity": visible(1),
          "circle-stroke-color": theme.lineSelected ?? HOJA_MAP_THEME.lineSelected!,
          "circle-stroke-width": ["case", SELECTED, 3, 0],
        } as unknown as CirclePaint,
      },
      beforeId,
    );
    return;
  }

  map.addLayer(
    {
      id: "municipios-dots",
      type: "circle",
      source: "municipios-pts",
      paint: {
        "circle-color": theme.pointColor ?? HOJA_MAP_THEME.sequential![4],
        "circle-radius": byZoom(
          ["+", 1.5, ["*", SCORE, 0.08]],
          ["+", 4, ["*", SCORE, 0.22]],
        ),
        "circle-opacity": visible(0.9),
        "circle-stroke-color": theme.lineSelected ?? HOJA_MAP_THEME.lineSelected!,
        "circle-stroke-width": ["case", SELECTED, 3.5, 0],
      } as unknown as CirclePaint,
    },
    beforeId,
  );
  map.addLayer(
    {
      id: "municipios-overprint",
      type: "circle",
      source: "municipios-pts",
      paint: {
        "circle-color": theme.overprintColor ?? HOJA_MAP_THEME.sequential![3],
        "circle-radius": byZoom(
          ["+", 0.8, ["*", SCORE, 0.04]],
          ["+", 2, ["*", SCORE, 0.11]],
        ),
        "circle-translate": [1.5, 1.5],
        "circle-opacity": [
          "case",
          ["all", IN_SCOPE, ["==", ["feature-state", "category"], "muy_alta"]],
          0.95,
          0,
        ],
      } as unknown as CirclePaint,
    },
    beforeId,
  );
}

function sourceLayerName(layer: LayerSpecification): string {
  if (!("source-layer" in layer)) return "";
  return String(layer["source-layer"] ?? "");
}

function findFillInsertionLayer(layers: LayerSpecification[]): string | undefined {
  const roadsOrBoundaries =
    /(road|street|highway|motorway|trunk|transport|boundary|admin|bridge|tunnel)/i;
  return layers.find(
    (layer) =>
      layer.type === "line" &&
      roadsOrBoundaries.test(`${layer.id} ${sourceLayerName(layer)}`),
  )?.id;
}

function findLabelInsertionLayer(
  layers: LayerSpecification[],
): string | undefined {
  return layers.find((layer) => layer.type === "symbol")?.id;
}

function extendBounds(bounds: LngLatBounds, coordinates: unknown): void {
  if (
    Array.isArray(coordinates) &&
    coordinates.length === 2 &&
    typeof coordinates[0] === "number" &&
    typeof coordinates[1] === "number"
  ) {
    bounds.extend(coordinates as [number, number]);
    return;
  }
  if (Array.isArray(coordinates)) {
    coordinates.forEach((item) => extendBounds(bounds, item));
  }
}

function formatValue(value: number | null): string {
  return value == null ? "Sin dato" : value.toFixed(1);
}

function tooltipContent(
  nameValue: unknown,
  provinceValue: unknown,
  scoreValue: string,
  valueLabel?: string,
  details?: MapTooltipDetails,
) {
  const tooltip = document.createElement("div");
  tooltip.className = "map-tooltip";
  if (details) tooltip.classList.add("with-details");
  const name = document.createElement("strong");
  name.textContent = String(nameValue ?? "");
  const province = document.createElement("span");
  province.className = "map-tooltip-province";
  province.textContent = String(provinceValue ?? "");
  const score = document.createElement("b");
  score.className = "map-tooltip-value";
  score.textContent = valueLabel ? `${valueLabel}: ${scoreValue}` : scoreValue;
  tooltip.append(name, province, score);
  if (details) {
    const rows: [string, number | null][] = [
      ["Situación actual", details.ipr4],
      ["Con riesgo futuro", details.ipr5],
      ["Riesgo futuro", details.riesgoFuturo],
    ];
    rows.forEach(([label, value]) => {
      const row = document.createElement("span");
      row.className = "map-tooltip-detail";
      row.textContent = `${label}: ${formatValue(value)}`;
      tooltip.append(row);
    });
  }
  return tooltip;
}

export default function Map({
  geometry,
  values,
  visibleIds,
  filterActive,
  selectedId,
  colorScale = "sequential",
  valueLabel,
  busy = false,
  tooltipDetails,
  theme,
  ariaLabel = "Mapa interactivo de presión sobre la vivienda",
  onSelect,
}: MapProps) {
  const themeRef = useRef(theme);
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const popupRef = useRef<Popup | null>(null);
  const previousSelected = useRef<string | null>(null);
  const hoveredIdRef = useRef<string | null>(null);
  const onSelectRef = useRef(onSelect);
  const selectedIdRef = useRef(selectedId);
  const valuesRef = useRef(new globalThis.Map<string, Value>());
  const visibleIdsRef = useRef(new Set<string>());
  const filterActiveRef = useRef(filterActive);
  const colorScaleRef = useRef(colorScale);
  const valueLabelRef = useRef(valueLabel);
  const tooltipDetailsRef = useRef(tooltipDetails);
  const styleReadyRef = useRef(false);
  const fallbackUsedRef = useRef(false);
  const interactionsBoundRef = useRef(false);
  const [activeView, setActiveView] = useState<ViewKey | null>("peninsula");
  const [basemapUnavailable, setBasemapUnavailable] = useState(false);
  const [mapReady, setMapReady] = useState(false);
  const [mapContextReady, setMapContextReady] = useState(false);

  const valueMap = useMemo(
    () => new globalThis.Map(values.map((value) => [value.cod_ine, value])),
    [values],
  );
  const visibleIdSet = useMemo(() => new Set(visibleIds), [visibleIds]);
  const accessibleFeatures = useMemo(
    () =>
      geometry.features
        .map((feature) => {
          const id = String(feature.properties?.cod_ine ?? "");
          const name = String(feature.properties?.nombre ?? id);
          const province = String(feature.properties?.provincia ?? "");
          const value = valueMap.get(id)?.valor ?? null;

          return { id, name, province, value };
        })
        .filter(
          (item) =>
            item.id &&
            (filterActive || visibleIdSet.size > 0
              ? visibleIdSet.has(item.id)
              : true),
        )
        .sort((a, b) => a.name.localeCompare(b.name, "es")),
    [filterActive, geometry, valueMap, visibleIdSet],
  );

  useEffect(() => {
    valuesRef.current = valueMap;
  }, [valueMap]);
  useEffect(() => {
    visibleIdsRef.current = visibleIdSet;
    filterActiveRef.current = filterActive;
  }, [visibleIdSet, filterActive]);
  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);
  useEffect(() => {
    selectedIdRef.current = selectedId;
  }, [selectedId]);
  useEffect(() => {
    colorScaleRef.current = colorScale;
  }, [colorScale]);
  useEffect(() => {
    valueLabelRef.current = valueLabel;
  }, [valueLabel]);
  useEffect(() => {
    tooltipDetailsRef.current = tooltipDetails;
  }, [tooltipDetails]);

  const applyValues = useCallback(
    (map: MLMap) => {
      const hasPoints = Boolean(map.getSource("municipios-pts"));
      geometry.features.forEach((feature) => {
        const id = String(feature.properties?.cod_ine);
        const entry = valuesRef.current.get(id);
        const inScope =
          !filterActiveRef.current || visibleIdsRef.current.has(id);
        const state = {
          score: entry?.valor ?? 0,
          hasData: entry?.valor != null,
          category: entry?.categoria ?? "",
          inScope,
        };
        map.setFeatureState({ source: "municipios", id }, state);
        if (hasPoints) {
          map.setFeatureState({ source: "municipios-pts", id }, state);
        }
      });
    },
    [geometry],
  );

  const setSelectedState = useCallback(
    (map: MLMap, id: string, selected: boolean) => {
      map.setFeatureState({ source: "municipios", id }, { selected });
      if (map.getSource("municipios-pts")) {
        map.setFeatureState({ source: "municipios-pts", id }, { selected });
      }
    },
    [],
  );

  const fitView = useCallback((view: ViewKey, duration = 650) => {
    const map = mapRef.current;
    setActiveView(view);
    if (!map) return;
    const preset = VIEW_PRESETS[view];
    map.fitBounds(preset.bounds, {
      padding: 34,
      maxZoom: preset.maxZoom,
      duration,
    });
  }, []);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const activeTheme = themeRef.current;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASEMAP_STYLE,
      bounds: VIEW_PRESETS.peninsula.bounds,
      fitBoundsOptions: {
        padding: 34,
        maxZoom: VIEW_PRESETS.peninsula.maxZoom,
      },
      attributionControl: false,
      cooperativeGestures: activeTheme?.cooperativeGestures ?? true,
    });
    styleReadyRef.current = false;
    fallbackUsedRef.current = false;
    interactionsBoundRef.current = false;
    setMapReady(false);
    setMapContextReady(false);
    setBasemapUnavailable(false);

    let basemapWarningTimer: number | undefined;
    let resizeFrame = 0;
    let basemapErrorCount = 0;

    const useFallbackStyle = () => {
      if (styleReadyRef.current || fallbackUsedRef.current) return;
      fallbackUsedRef.current = true;
      setBasemapUnavailable(true);
      map.setStyle(
        activeTheme?.fallbackBackground
          ? {
              ...FALLBACK_STYLE,
              layers: [
                {
                  id: "background",
                  type: "background",
                  paint: {
                    "background-color": activeTheme.fallbackBackground,
                  },
                },
              ],
            }
          : FALLBACK_STYLE,
      );
    };

    const basemapTimeout = window.setTimeout(
      useFallbackStyle,
      BASEMAP_TIMEOUT_MS,
    );

    const resizeObserver = new ResizeObserver(() => {
      window.cancelAnimationFrame(resizeFrame);
      resizeFrame = window.requestAnimationFrame(() => map.resize());
    });
    resizeObserver.observe(containerRef.current);

    map.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "top-right",
    );
    map.addControl(
      new maplibregl.AttributionControl({ compact: true }),
      "bottom-right",
    );
    if (activeTheme?.scaleBar) {
      map.addControl(
        new maplibregl.ScaleControl({ unit: "metric", maxWidth: 140 }),
        "bottom-left",
      );
    }

    const installMunicipalLayer = () => {
      if (map.getSource("municipios")) return;
      if (activeTheme?.basemapPaint && !fallbackUsedRef.current) {
        paintBasemap(map, activeTheme.basemapPaint);
      }
      map.getStyle().layers.forEach((layer) => {
        if (
          layer.type === "symbol" &&
          "source-layer" in layer &&
          layer["source-layer"] === "place"
        ) {
          map.setLayoutProperty(layer.id, "text-field", [
            "coalesce",
            ["get", "name_es"],
            ["get", "name"],
            ["get", "name_en"],
          ]);
        }
      });
      const styleLayers = map.getStyle().layers;
      const fillInsertionId = findFillInsertionLayer(styleLayers);
      const labelInsertionId = findLabelInsertionLayer(styleLayers);

      map.addSource("municipios", {
        type: "geojson",
        data: geometry,
        promoteId: "cod_ine",
      });
      if (activeTheme?.graticule) {
        map.addSource("graticula", { type: "geojson", data: graticuleLines() });
        map.addLayer(
          {
            id: "graticula",
            type: "line",
            source: "graticula",
            paint: {
              "line-color": activeTheme.graticule,
              "line-width": 0.8,
              "line-dasharray": [4, 3],
            },
          },
          fillInsertionId ?? labelInsertionId,
        );
      }
      const baseOpacity = activeTheme?.fillOpacity ?? 0.72;
      map.addLayer(
        {
          id: "municipios-fill",
          type: "fill",
          source: "municipios",
          paint: {
            "fill-color": fillColor(colorScaleRef.current, activeTheme),
            "fill-opacity": [
              "case",
              ["boolean", ["feature-state", "selected"], false],
              activeTheme?.fillOpacityActive ?? Math.max(baseOpacity, 0.9),
              ["boolean", ["feature-state", "hovered"], false],
              activeTheme?.fillOpacityActive ?? Math.max(baseOpacity, 0.84),
              ["!", ["boolean", ["feature-state", "inScope"], true]],
              Math.min(baseOpacity, 0.2),
              ["boolean", ["feature-state", "hasData"], false],
              baseOpacity,
              Math.min(baseOpacity, 0.42),
            ],
          },
        },
        fillInsertionId ?? labelInsertionId,
      );
      map.addLayer(
        {
          id: "municipios-line",
          type: "line",
          source: "municipios",
          paint: {
            "line-color": [
              "case",
              ["boolean", ["feature-state", "selected"], false],
              activeTheme?.lineSelected ?? "#0b2239",
              ["boolean", ["feature-state", "hovered"], false],
              activeTheme?.lineHover ?? "#ef5b38",
              activeTheme?.lineBase ?? "#fffaf0",
            ],
            "line-width": [
              "case",
              ["boolean", ["feature-state", "selected"], false],
              3.2,
              ["boolean", ["feature-state", "hovered"], false],
              2.2,
              activeTheme?.lineBaseWidth ?? 0.7,
            ],
            "line-opacity": [
              "case",
              ["boolean", ["feature-state", "selected"], false],
              1,
              ["boolean", ["feature-state", "hovered"], false],
              1,
              ["boolean", ["feature-state", "inScope"], true],
              0.86,
              0.32,
            ],
          },
        },
        labelInsertionId,
      );
      if (activeTheme?.points) {
        installPointLayers(
          map,
          geometry,
          activeTheme,
          colorScaleRef.current,
          labelInsertionId,
        );
      }

      applyValues(map);
      if (selectedIdRef.current) {
        setSelectedState(map, selectedIdRef.current, true);
        previousSelected.current = selectedIdRef.current;
      }

      if (!interactionsBoundRef.current) {
        interactionsBoundRef.current = true;
        map.on("mousemove", "municipios-fill", (event) => {
          const feature = event.features?.[0];
          const code = String(feature?.properties?.cod_ine ?? "");
          const inScope =
            !filterActiveRef.current || visibleIdsRef.current.has(code);
          map.getCanvas().style.cursor = inScope ? "pointer" : "";

          if (hoveredIdRef.current && hoveredIdRef.current !== code) {
            map.setFeatureState(
              { source: "municipios", id: hoveredIdRef.current },
              { hovered: false },
            );
          }
          if (inScope && code) {
            map.setFeatureState(
              { source: "municipios", id: code },
              { hovered: true },
            );
            hoveredIdRef.current = code;
          }

          const entry = valuesRef.current.get(code);
          const score = !inScope
            ? "Fuera del filtro"
            : entry?.valor == null
              ? "Sin dato"
              : colorScaleRef.current === "divergent" && entry.valor > 0
                ? `+${entry.valor.toFixed(1)}`
                : entry.valor.toFixed(1);
          popupRef.current?.remove();
          popupRef.current = new maplibregl.Popup({
            closeButton: false,
            closeOnClick: false,
            offset: 12,
          })
            .setLngLat(event.lngLat)
            .setDOMContent(
              tooltipContent(
                feature?.properties?.nombre,
                feature?.properties?.provincia,
                score,
                valueLabelRef.current,
                inScope ? tooltipDetailsRef.current?.[code] : undefined,
              ),
            )
            .addTo(map);
        });
        map.on("mouseleave", "municipios-fill", () => {
          map.getCanvas().style.cursor = "";
          if (hoveredIdRef.current) {
            map.setFeatureState(
              { source: "municipios", id: hoveredIdRef.current },
              { hovered: false },
            );
            hoveredIdRef.current = null;
          }
          popupRef.current?.remove();
        });
        map.on("click", "municipios-fill", (event) => {
          const id = String(
            event.features?.[0]?.properties?.cod_ine ?? "",
          );
          const inScope =
            !filterActiveRef.current || visibleIdsRef.current.has(id);
          if (id && inScope) onSelectRef.current(id);
        });
      }
      setMapReady(true);
    };

    map.on("style.load", () => {
      styleReadyRef.current = true;
      window.clearTimeout(basemapTimeout);
      if (!fallbackUsedRef.current) setBasemapUnavailable(false);
      installMunicipalLayer();
    });
    map.on("error", () => {
      if (!styleReadyRef.current || fallbackUsedRef.current) return;
      basemapErrorCount += 1;
      if (basemapErrorCount < 4 || basemapWarningTimer !== undefined) return;
      basemapWarningTimer = window.setTimeout(() => {
        setBasemapUnavailable(true);
        basemapWarningTimer = undefined;
      }, 2_000);
    });
    map.on("idle", () => {
      setMapContextReady(true);
      if (fallbackUsedRef.current) return;
      basemapErrorCount = 0;
      if (basemapWarningTimer !== undefined) {
        window.clearTimeout(basemapWarningTimer);
        basemapWarningTimer = undefined;
      }
      setBasemapUnavailable(false);
    });

    mapRef.current = map;
    return () => {
      window.clearTimeout(basemapTimeout);
      if (basemapWarningTimer !== undefined) {
        window.clearTimeout(basemapWarningTimer);
      }
      resizeObserver.disconnect();
      window.cancelAnimationFrame(resizeFrame);
      popupRef.current?.remove();
      map.remove();
      mapRef.current = null;
      interactionsBoundRef.current = false;
    };
  }, [geometry, applyValues, setSelectedState]);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map?.getSource("municipios")) return;
    applyValues(map);
  }, [
    valueMap,
    visibleIdSet,
    filterActive,
    geometry,
    applyValues,
    mapReady,
  ]);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map?.getLayer("municipios-fill")) return;
    map.setPaintProperty(
      "municipios-fill",
      "fill-color",
      fillColor(colorScale, themeRef.current),
    );
    if (map.getLayer("municipios-glow")) {
      const color = pointColor(themeRef.current, colorScale);
      map.setPaintProperty("municipios-glow", "circle-color", color);
      map.setPaintProperty("municipios-core", "circle-color", color);
    }
  }, [colorScale, mapReady]);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map?.getSource("municipios") || selectedId) return;
    if (!filterActive) {
      const preset = VIEW_PRESETS.peninsula;
      map.once("moveend", () => setActiveView("peninsula"));
      map.fitBounds(preset.bounds, {
        padding: 34,
        maxZoom: preset.maxZoom,
        duration: 650,
      });
      return;
    }
    if (visibleIdSet.size === 0) return;
    const bounds = new maplibregl.LngLatBounds();
    geometry.features.forEach((feature) => {
      const id = String(feature.properties?.cod_ine ?? "");
      if (
        visibleIdSet.has(id) &&
        feature.geometry &&
        "coordinates" in feature.geometry
      ) {
        extendBounds(bounds, feature.geometry.coordinates);
      }
    });
    if (!bounds.isEmpty()) {
      map.once("moveend", () => setActiveView(null));
      map.fitBounds(bounds, {
        padding: 70,
        maxZoom: visibleIdSet.size === 1 ? 9 : 7.2,
        duration: 650,
      });
    }
  }, [
    filterActive,
    visibleIdSet,
    selectedId,
    geometry,
    fitView,
    mapReady,
  ]);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map?.getSource("municipios")) return;
    if (previousSelected.current) {
      setSelectedState(map, previousSelected.current, false);
    }
    if (selectedId) {
      setSelectedState(map, selectedId, true);
      const feature = geometry.features.find(
        (item) => String(item.properties?.cod_ine) === selectedId,
      );
      if (feature?.geometry && "coordinates" in feature.geometry) {
        const bounds = new maplibregl.LngLatBounds();
        extendBounds(bounds, feature.geometry.coordinates);
        if (!bounds.isEmpty()) {
          map.once("moveend", () => setActiveView(null));
          map.fitBounds(bounds, {
            padding: 90,
            maxZoom: 9,
            duration: 650,
          });
        }
      }
    }
    previousSelected.current = selectedId ?? null;
  }, [selectedId, geometry, mapReady, setSelectedState]);

  return (
    <div className="map-shell">
      <div
        ref={containerRef}
        className="map"
        role="region"
        aria-label={ariaLabel}
      />
      <div
        className="map-view-controls"
        role="group"
        aria-label="Vista territorial del mapa"
      >
        {(Object.keys(VIEW_PRESETS) as ViewKey[]).map((view) => (
          <button
            key={view}
            className={activeView === view ? "active" : ""}
            aria-pressed={activeView === view}
            disabled={!mapReady || !mapContextReady}
            onClick={() => fitView(view)}
          >
            {VIEW_PRESETS[view].label}
          </button>
        ))}
      </div>
      {(!mapReady || !mapContextReady) && (
        <div className="map-state-overlay" role="status" aria-live="polite">
          <strong>Preparando el mapa</strong>
          <span>Cargando calles, límites y municipios…</span>
        </div>
      )}
      {mapReady && filterActive && visibleIds.length === 0 && (
        <div className="map-state-overlay map-state-overlay-empty" role="status">
          <strong>No hay municipios con estos filtros</strong>
          <span>Prueba a ampliar la puntuación o quitar algún filtro.</span>
        </div>
      )}
      {mapReady && busy && (
        <span className="map-refresh-indicator" role="status">
          Actualizando el mapa…
        </span>
      )}
      {basemapUnavailable && (
        <span className="map-context-warning" role="status">
          No se ha podido cargar el mapa de calles. Los municipios siguen
          disponibles.
        </span>
      )}
      <details className="map-keyboard-picker">
        <summary>
          Elegir municipio en lista ({accessibleFeatures.length})
        </summary>
        <ul className="map-keyboard-list">
          {accessibleFeatures.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                aria-pressed={selectedId === item.id}
                onClick={() => onSelect(item.id)}
              >
                <span>{item.name}</span>
                <small>
                  {item.province}
                  {item.value !== null
                    ? ` · ${formatValue(item.value)}`
                    : " · Sin dato"}
                </small>
              </button>
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
