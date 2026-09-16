from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Product = Literal["observado", "prospectivo"]
DataType = Literal["observado", "estimado", "proyectado"]


class Municipality(BaseModel):
    cod_ine: str
    nombre: str
    provincia: str
    comunidad_autonoma: str | None = None


class LayerValue(BaseModel):
    nombre: str
    score: float | None
    peso: float | None = None
    contribucion: float | None = None
    tipo: DataType


class ComponentQuality(BaseModel):
    component: str
    source_year: int | None
    statistical_period: str
    coverage_score: float = Field(ge=0, le=100)
    recency_score: float | None = Field(ge=0, le=100)
    consistency_score: float | None = Field(ge=0, le=100)
    quality_score: float | None = Field(ge=0, le=100)
    issues: list[str]


class DataQuality(BaseModel):
    score: float | None = Field(ge=0, le=100)
    level: Literal["alta", "media", "baja", "muy_baja"] | None
    coverage: float = Field(ge=0, le=100)
    recency: float | None = Field(ge=0, le=100)
    consistency: float | None = Field(ge=0, le=100)
    scope: Literal["ipr4_observado"]
    calculation_version: str
    calculated_at: datetime
    issues: list[str]
    components: list[ComponentQuality]


class IndexRow(Municipality):
    anio: int
    score: float | None
    percentil: float | None
    categoria: str | None
    ranking: int | None
    producto: Product
    capas_validas: int
    data_quality: DataQuality | None = None


class MunicipalityDetail(IndexRow):
    capas: list[LayerValue]
    metodo: str
    version_metodologia: str


class HistoricalPoint(BaseModel):
    anio: int
    serie: str
    # `valor` es la posición dentro del año (0-100) y `bruto` la puntuación con
    # la que se calculó, para poder leer la serie junto al cuadro de factores.
    valor: float | None
    bruto: float | None = None
    tipo: DataType


class HomogeneousHistory(BaseModel):
    included: bool
    reason: str
    metadata: dict
    items: list[dict]


class Benchmark(BaseModel):
    nivel: Literal["provincia", "ccaa", "espana"]
    territorio: str
    score: float | None
    asequibilidad: float | None
    turismo: float | None
    especulacion: float | None
    gentrificacion: float | None
    riesgo_futuro: float | None


class QualityRow(BaseModel):
    data_quality: DataQuality | None = None
    cod_ine: str
    anio: int
    capas_observadas_validas: int
    cobertura_observada_pct: float
    capas_prospectivas_validas: int
    cobertura_prospectiva_pct: float
    elegible_observado: bool
    elegible_prospectivo: bool
    nulos_prospectivos: int
    imputaciones: int | None
    version_metodologia: str


class SourceItem(BaseModel):
    name: str
    layer: str


class QualitySummary(BaseModel):
    dqs_media: float | None = None
    dqs_niveles: dict[str, int] = Field(default_factory=dict)
    municipios: int
    cobertura_observada_media: float
    cobertura_prospectiva_media: float
    nulos_prospectivos: int
    municipios_observados: int
    municipios_prospectivos: int
    sources: list[SourceItem]


class MapValue(BaseModel):
    cod_ine: str
    valor: float | None
    categoria: str | None
    tipo: Literal["observado", "proyectado"]


class RegionCatalogue(BaseModel):
    comunidad_autonoma: str
    provincias: list[str]


class Catalogue(BaseModel):
    years: list[int]
    regions: list[RegionCatalogue]
    historical: dict = Field(default_factory=dict)


class PaginatedIndex(BaseModel):
    items: list[IndexRow]
    total: int
    year_options: list[int]


class Comparison(BaseModel):
    items: list[MunicipalityDetail] = Field(min_length=2, max_length=4)


class ProspectiveContrastItem(Municipality):
    anio: int
    ipr4_observado: float
    ipr5_prospectivo: float | None
    riesgo_futuro: float | None
    brecha: float | None


class ProspectiveContrastSummary(BaseModel):
    total: int
    comparables: int
    ipr5_mayor: int
    ipr5_menor: int
    igual: int
    sin_contraste: int
    brecha_media: float | None
    brecha_min: float | None
    brecha_max: float | None


class ProspectiveContrast(BaseModel):
    items: list[ProspectiveContrastItem]
    resumen: ProspectiveContrastSummary


class SpatialSummary(BaseModel):
    cluster_type: Literal["HH", "LL", "HL", "LH", "NS"]
    count: int
    raw_count: int
    percentage: float


class SpatialGlobal(BaseModel):
    anio: int
    moran_i: float
    expected_i: float
    p_value: float
    z_score: float
    permutations: int
    seed: int
    alpha: float
    n_municipalities: int
    n_observations: int
    n_islands: int
    weights_method: str
    calculation_version: str
    calculated_at: str
    is_significant: bool
    interpretation: str
    main_correction: str
    summary: list[SpatialSummary]


class SpatialLocal(BaseModel):
    cod_ine: str
    nombre: str
    anio: int
    ipr: float
    local_moran_i: float | None
    p_value: float | None
    p_value_fdr: float | None
    quadrant: Literal["HH", "LL", "HL", "LH"] | None
    cluster_type: Literal["HH", "LL", "HL", "LH", "NS"]
    cluster_type_raw: Literal["HH", "LL", "HL", "LH", "NS"]
    is_significant: bool
    is_significant_raw: bool
    eligible: bool
    exclusion_reason: str | None
    neighbor_count: int
    standardized_ipr: float | None
    spatial_lag: float | None
    spatial_lag_ipr: float | None
    dqs: float | None
    dqs_level: str | None
    calculation_version: str
    calculated_at: str


class SpatialYear(BaseModel):
    global_result: SpatialGlobal
    items: list[SpatialLocal]


class SpatialHistory(BaseModel):
    years: list[SpatialGlobal]
    history_comparable: bool
    dqs_available: bool


class SpatialNeighbor(BaseModel):
    cod_ine: str
    nombre: str
    ipr: float
    weight: float


class SpatialMunicipality(SpatialLocal):
    neighbors: list[SpatialNeighbor]
