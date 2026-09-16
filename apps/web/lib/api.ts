export const API =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Product = "observado" | "prospectivo";
export type LayerName =
  | "ipr"
  | "asequibilidad"
  | "turismo"
  | "especulacion"
  | "gentrificacion"
  | "riesgo_futuro"
  | "calidad";

/** Nivel de calidad del dato del IPR-4, de mayor a menor. */
export type QualityLevel = "alta" | "media" | "baja" | "muy_baja";

/**
 * Data Quality Score del IPR-4 observado. Mide cobertura y actualidad de los
 * datos usados; no mide presión ni es una probabilidad de acierto.
 */
export type DataQuality = {
  score: number | null;
  level: QualityLevel | null;
  coverage: number;
  recency: number | null;
  consistency: number | null;
  scope: "ipr4_observado";
  calculation_version: string;
  calculated_at: string;
  issues: string[];
  components: {
    component: string;
    source_year: number | null;
    statistical_period: string;
    coverage_score: number;
    recency_score: number | null;
    consistency_score: number | null;
    quality_score: number | null;
    issues: string[];
  }[];
};

export type Municipality = {
  cod_ine: string;
  nombre: string;
  provincia: string;
  comunidad_autonoma?: string;
};

export type IndexRow = Municipality & {
  data_quality?: DataQuality | null;
  anio: number;
  score: number | null;
  percentil: number | null;
  categoria: string | null;
  ranking: number | null;
  producto: Product;
  capas_validas: number;
};

export type Layer = {
  nombre: string;
  score: number | null;
  peso: number | null;
  contribucion: number | null;
  tipo: "observado" | "estimado" | "proyectado";
};

export type Detail = IndexRow & {
  capas: Layer[];
  metodo: string;
  version_metodologia: string;
};

export type HistoricalPoint = {
  anio: number;
  serie: string;
  /** Posición del municipio dentro del año, de 0 a 100. */
  valor: number | null;
  /** Puntuación con la que se calculó esa posición, cuando la hay. */
  bruto?: number | null;
  tipo: "observado" | "estimado" | "proyectado";
};

/** Un año del IPR-4 histórico relativo, con sus cuatro componentes. */
export type HistoricalYear = {
  anio: number;
  ipr_score: number;
  ipr_percentile: number;
  rank: number;
  delta_ipr: number | null;
  delta_since_start: number;
  rank_change: number | null;
  components: {
    component: string;
    value: number;
    layer_score: number;
    weight: number;
    contribution: number;
    delta_component: number | null;
    delta_contribution: number | null;
  }[];
};

/** Serie homogénea 2020–2023 sobre un panel fijo; distinta del corte nacional. */
export type HomogeneousHistory = {
  included: boolean;
  reason: string;
  metadata: {
    years?: number[];
    municipality_count?: number;
    calculation_version?: string;
  };
  items: HistoricalYear[];
};

export type HistoricalRank = Municipality & {
  anio: number;
  score: number;
  percentil: number;
  ranking: number;
  delta_ipr: number | null;
  delta_since_start: number;
  rank_change: number | null;
};

export type Benchmark = {
  nivel: "provincia" | "ccaa" | "espana";
  territorio: string;
  score: number | null;
  asequibilidad: number | null;
  turismo: number | null;
  especulacion: number | null;
  gentrificacion: number | null;
  riesgo_futuro: number | null;
};

export type Catalogue = {
  years: number[];
  regions: {
    comunidad_autonoma: string;
    provincias: string[];
  }[];
};

export type QualitySummary = {
  dqs_media?: number | null;
  dqs_niveles?: Record<string, number>;
  municipios: number;
  cobertura_observada_media: number;
  cobertura_prospectiva_media: number;
  nulos_prospectivos: number;
  municipios_observados: number;
  municipios_prospectivos: number;
  sources: { name: string; layer: string }[];
};

export type ProspectiveContrastRow = Municipality & {
  anio: number;
  ipr4_observado: number;
  ipr5_prospectivo: number | null;
  riesgo_futuro: number | null;
  brecha: number | null;
};

export type ProspectiveContrastSummary = {
  total: number;
  comparables: number;
  ipr5_mayor: number;
  ipr5_menor: number;
  igual: number;
  sin_contraste: number;
  brecha_media: number | null;
  brecha_min: number | null;
  brecha_max: number | null;
};

export type ProspectiveContrast = {
  items: ProspectiveContrastRow[];
  resumen: ProspectiveContrastSummary;
};

export async function getJSON<T>(path: string): Promise<T> {
  const response = await fetch(`${API}${path}`, { cache: "no-store" });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Error de API (${response.status})`);
  }
  return response.json();
}
