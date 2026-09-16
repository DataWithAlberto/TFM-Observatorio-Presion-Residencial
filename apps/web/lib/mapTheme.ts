/**
 * Apariencia del mapa: rampa, contornos y mapa base. Sin tema explícito se
 * aplica `HOJA_MAP_THEME`.
 */
export type MapTheme = {
  /** Colores equiespaciados entre 0 y 100. */
  sequential?: string[];
  /** Colores equiespaciados entre -15 y 15. */
  divergent?: string[];
  /** Cuatro niveles del DQS: <50, 50–70, 70–85 y ≥85. */
  quality?: string[];
  /** Categorías LISA; NE es el municipio sin vecinos, no evaluable. */
  lisa?: Record<"HH" | "LL" | "HL" | "LH" | "NS" | "NE", string>;
  missing?: string;
  fallbackBackground?: string;
  basemapPaint?: {
    background?: string;
    water?: string;
    boundary?: string;
    hideLabels?: boolean;
    /** Muestra los rótulos del mapa base solo a partir de este zoom. */
    labelsMinZoom?: number;
    hideRoads?: boolean;
    hideLanduse?: boolean;
  };
  lineBase?: string;
  lineHover?: string;
  lineSelected?: string;
  lineBaseWidth?: number;
  fillOpacity?: number;
  /** Opacidad del municipio seleccionado o bajo el cursor. */
  fillOpacityActive?: number;
  /** Capa de puntos sobre los centroides: halo luminoso o trama de imprenta. */
  points?: "glow" | "halftone";
  pointColor?: string;
  overprintColor?: string;
  graticule?: string;
  scaleBar?: boolean;
  cooperativeGestures?: boolean;
};

/**
 * Tema cartográfico del sistema «Hoja catastral».
 *
 * Es, junto a `tokens.css`, el único sitio donde viven colores fijos: MapLibre
 * necesita valores literales en su especificación de estilo y no resuelve
 * `var(--…)`. Los tonos coinciden con las rampas de `tokens.css`.
 */
export const HOJA_MAP_THEME: MapTheme = {
  sequential: ["#EEDDE4", "#DDA3BA", "#C4608C", "#962C5E", "#561238"],
  divergent: ["#2F5E6E", "#9DBCC4", "#F3F4EF", "#DDA3BA", "#962C5E"],
  quality: ["#E8DFC9", "#B9CFC6", "#6F9D8F", "#2F5E6E"],
  lisa: {
    HH: "#962C5E",
    LL: "#2F5E6E",
    HL: "#B0773A",
    LH: "#5A5FA8",
    NS: "#CFD4CE",
    NE: "#EDEFEA",
  },
  missing: "#E2E5DF",
  fallbackBackground: "#F3F4EF",
  basemapPaint: {
    background: "#F3F4EF",
    water: "#DCE4E0",
    boundary: "#9AA59E",
    labelsMinZoom: 7,
    hideRoads: true,
    hideLanduse: true,
  },
  lineBase: "#F3F4EF",
  lineHover: "#17201B",
  lineSelected: "#17201B",
  lineBaseWidth: 0.6,
  fillOpacity: 0.92,
  graticule: "#9AA59E",
  scaleBar: true,
  cooperativeGestures: false,
};

/** Variante para mapas incrustados en una página que hace scroll. */
export const HOJA_MAP_THEME_EMBEDDED: MapTheme = {
  ...HOJA_MAP_THEME,
  cooperativeGestures: true,
};

/** Rampa secuencial, para pintar barras y cuadros de categoría fuera del mapa. */
export const HOJA_RAMP = HOJA_MAP_THEME.sequential as string[];
