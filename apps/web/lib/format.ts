import type { LayerName, Product } from "@/lib/api";

export const LAYERS: { id: LayerName; label: string; short: string }[] = [
  { id: "ipr", label: "Presión residencial total", short: "Presión total" },
  {
    id: "asequibilidad",
    label: "Dificultad para pagar la vivienda",
    short: "Dificultad para pagar",
  },
  {
    id: "turismo",
    label: "Presión de las viviendas turísticas",
    short: "Viviendas turísticas",
  },
  { id: "especulacion", label: "Señales de especulación", short: "Especulación" },
  {
    id: "gentrificacion",
    label: "Cambios y desplazamiento vecinal",
    short: "Desplazamiento vecinal",
  },
  {
    id: "riesgo_futuro",
    label: "Riesgo futuro: clima y tendencias",
    short: "Riesgo futuro",
  },
  {
    id: "calidad",
    label: "Calidad del dato del IPR-4",
    short: "Calidad del dato",
  },
];

/** Etiqueta de cada nivel del DQS. */
export const QUALITY_LEVELS: Record<string, string> = {
  alta: "Alta",
  media: "Media",
  baja: "Baja",
  muy_baja: "Muy baja",
};

export function qualityLabel(level: string | null | undefined): string {
  return level ? (QUALITY_LEVELS[level] ?? level) : "Sin dato";
}

export function isLayer(value: string | null): value is LayerName {
  return LAYERS.some((layer) => layer.id === value);
}

const SERIES_LABELS: Record<string, string> = {
  ipr_observado: "Índice total (IPR-4)",
  ipr_prospectivo: "Índice con riesgo futuro (IPR-5)",
  ipr_historico: "IPR-4 histórico relativo",
};

export function layerLabel(id: string, short = false): string {
  const layer = LAYERS.find((item) => item.id === id);
  return layer ? (short ? layer.short : layer.label) : (SERIES_LABELS[id] ?? id);
}

export const CATEGORIES = [
  { id: "muy_baja", label: "Muy baja" },
  { id: "baja", label: "Baja" },
  { id: "media", label: "Media" },
  { id: "alta", label: "Alta" },
  { id: "muy_alta", label: "Muy alta" },
];

export function categoryLabel(id: string | null | undefined): string {
  return CATEGORIES.find((item) => item.id === id)?.label ?? "Sin categoría";
}

export function categoryIndex(id: string | null | undefined): number {
  return CATEGORIES.findIndex((item) => item.id === id);
}

export const TYPE_LABELS: Record<string, string> = {
  observado: "Dato observado",
  estimado: "Estimación",
  proyectado: "Escenario futuro",
};

export const PRODUCT_NAMES: Record<Product, { name: string; code: string }> = {
  observado: { name: "Situación actual", code: "IPR-4" },
  prospectivo: { name: "Con riesgo futuro", code: "IPR-5" },
};

export function universe(product: Product): number {
  return product === "prospectivo" ? 303 : 306;
}

export function fmt(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString("es-ES", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function percent(value: number | null | undefined): string {
  return value == null ? "—" : `${fmt(value * 100, 0)} %`;
}

const ACCENTED: Record<string, string> = {
  ALMERIA: "Almería",
  "ARABA/ALAVA": "Araba/Álava",
  AVILA: "Ávila",
  "BALEARS, ILLES": "Illes Balears",
  CACERES: "Cáceres",
  CADIZ: "Cádiz",
  "CASTELLON/CASTELLO": "Castellón/Castelló",
  CORDOBA: "Córdoba",
  "CORUNA, A": "A Coruña",
  JAEN: "Jaén",
  LEON: "León",
  MALAGA: "Málaga",
  "VALENCIA/VALENCIA": "Valencia/València",
};

const PARTICLES = new Set(["de", "del", "la", "las", "los", "y", "i", "el"]);

function titleCase(value: string): string {
  return value
    .toLowerCase()
    .split(" ")
    .map((word, index) =>
      index > 0 && PARTICLES.has(word)
        ? word
        : word.replace(/(^|[/-])(\p{L})/gu, (_, sep, char) => sep + char.toUpperCase()),
    )
    .join(" ");
}

/** Convierte «PALMAS, LAS» o «Campello, el» en «Las Palmas» y «El Campello». */
export function placeName(raw: string | null | undefined): string {
  if (!raw) return "";
  const upper = raw === raw.toUpperCase();
  const accented = ACCENTED[raw];
  if (accented) return accented;
  const inverted = raw.match(/^(.*),\s*(el|la|los|las|l'|els|les|o|a|os|as|es|sa)$/i);
  if (inverted) {
    const article = inverted[2];
    const lead = article.charAt(0).toUpperCase() + article.slice(1).toLowerCase();
    const rest = upper ? titleCase(inverted[1]) : inverted[1];
    return lead.endsWith("'") ? `${lead}${rest}` : `${lead} ${rest}`;
  }
  return upper ? titleCase(raw) : raw;
}

/**
 * Paso de la rampa secuencial (1–5) que corresponde a una puntuación de 0 a
 * 100. Permite pintar barras y cuadros con los colores de `tokens.css` en vez
 * de interpolar un color literal en el marcado.
 */
export function rampStep(value: number | null | undefined): number | undefined {
  if (value == null || Number.isNaN(value)) return undefined;
  return Math.min(5, Math.max(1, Math.floor(value / 20) + 1));
}

function hexToRgb(hex: string): number[] {
  return [1, 3, 5].map((index) => parseInt(hex.slice(index, index + 2), 16));
}

/** Color de una rampa para una posición entre 0 y 1. */
export function rampColor(colors: string[], position: number): string {
  const clamped = Math.max(0, Math.min(1, position)) * (colors.length - 1);
  const index = Math.min(Math.floor(clamped), colors.length - 2);
  const mix = clamped - index;
  const from = hexToRgb(colors[index]);
  const to = hexToRgb(colors[index + 1]);
  return `#${from
    .map((value, channel) =>
      Math.round(value + (to[channel] - value) * mix)
        .toString(16)
        .padStart(2, "0"),
    )
    .join("")}`;
}
