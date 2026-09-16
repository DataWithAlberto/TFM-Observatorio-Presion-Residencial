/** Tipos del análisis espacial, tal como los devuelve la API. */

export type Cluster = "HH" | "LL" | "HL" | "LH" | "NS";

export type SpatialGlobal = {
  anio: number;
  moran_i: number;
  expected_i: number;
  p_value: number;
  z_score: number;
  permutations: number;
  seed: number;
  alpha: number;
  n_municipalities: number;
  n_observations: number;
  n_islands: number;
  weights_method: string;
  calculation_version: string;
  calculated_at: string;
  is_significant: boolean;
  interpretation: string;
  main_correction: string;
  summary: { cluster_type: Cluster; count: number; raw_count: number; percentage: number }[];
};

export type SpatialLocal = {
  cod_ine: string;
  nombre: string;
  anio: number;
  ipr: number;
  local_moran_i: number | null;
  p_value: number | null;
  p_value_fdr: number | null;
  quadrant: Exclude<Cluster, "NS"> | null;
  cluster_type: Cluster;
  cluster_type_raw: Cluster;
  is_significant: boolean;
  is_significant_raw: boolean;
  eligible: boolean;
  exclusion_reason: string | null;
  neighbor_count: number;
  standardized_ipr: number | null;
  spatial_lag: number | null;
  spatial_lag_ipr: number | null;
  dqs: number | null;
  dqs_level: string | null;
  calculation_version: string;
  calculated_at: string;
};

export type SpatialYear = { global_result: SpatialGlobal; items: SpatialLocal[] };

export type SpatialHistory = {
  years: SpatialGlobal[];
  history_comparable: boolean;
  dqs_available: boolean;
};

export type SpatialMunicipality = SpatialLocal & {
  neighbors: { cod_ine: string; nombre: string; ipr: number; weight: number }[];
};

export const formatSpatial = (value: number | null, digits = 3) =>
  value == null ? "No evaluable" : value.toFixed(digits);
