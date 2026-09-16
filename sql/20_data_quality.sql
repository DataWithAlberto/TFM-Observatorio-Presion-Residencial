CREATE TABLE IF NOT EXISTS data_quality_municipal (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    anio SMALLINT NOT NULL CHECK (anio BETWEEN 1900 AND 2100),
    calculation_version TEXT NOT NULL,
    dqs_score DOUBLE PRECISION CHECK (dqs_score BETWEEN 0 AND 100),
    quality_level TEXT,
    coverage_score DOUBLE PRECISION NOT NULL CHECK (coverage_score BETWEEN 0 AND 100),
    recency_score DOUBLE PRECISION CHECK (recency_score BETWEEN 0 AND 100),
    consistency_score DOUBLE PRECISION CHECK (consistency_score BETWEEN 0 AND 100),
    calculated_at TIMESTAMPTZ NOT NULL,
    details JSONB NOT NULL,
    PRIMARY KEY (cod_ine, anio, calculation_version),
    CHECK ((dqs_score IS NULL AND quality_level IS NULL) OR
      (dqs_score IS NOT NULL AND quality_level IS NOT NULL AND quality_level = CASE
        WHEN dqs_score >= 85 THEN 'alta' WHEN dqs_score >= 70 THEN 'media'
        WHEN dqs_score >= 50 THEN 'baja' ELSE 'muy_baja' END)),
    CHECK (dqs_score IS NULL OR (coverage_score > 0 AND recency_score IS NOT NULL)),
    CHECK (jsonb_typeof(details->'components') = 'array' AND jsonb_array_length(details->'components') = 4)
);
