-- Una versión vigente por año; sustitución atómica de todos los resultados.
CREATE TABLE IF NOT EXISTS ipr_spatial_global (
    anio SMALLINT PRIMARY KEY CHECK (anio BETWEEN 1900 AND 2200),
    moran_i DOUBLE PRECISION NOT NULL,
    expected_i DOUBLE PRECISION NOT NULL,
    z_score DOUBLE PRECISION NOT NULL,
    p_value DOUBLE PRECISION NOT NULL CHECK (p_value BETWEEN 0 AND 1),
    permutations INTEGER NOT NULL CHECK (permutations >= 99),
    weights_method TEXT NOT NULL,
    calculation_version TEXT NOT NULL,
    calculated_at TIMESTAMPTZ NOT NULL,
    result JSONB NOT NULL,
    metadata JSONB NOT NULL,
    audit JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS ipr_spatial_local (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    anio SMALLINT NOT NULL REFERENCES ipr_spatial_global(anio),
    ipr DOUBLE PRECISION NOT NULL CHECK (ipr BETWEEN 0 AND 100),
    local_moran_i DOUBLE PRECISION,
    p_value DOUBLE PRECISION CHECK (p_value BETWEEN 0 AND 1),
    p_value_fdr DOUBLE PRECISION CHECK (p_value_fdr BETWEEN 0 AND 1),
    quadrant TEXT CHECK (quadrant IN ('HH','LL','HL','LH')),
    cluster_type TEXT NOT NULL CHECK (cluster_type IN ('HH','LL','HL','LH','NS')),
    cluster_type_raw TEXT NOT NULL CHECK (cluster_type_raw IN ('HH','LL','HL','LH','NS')),
    is_significant BOOLEAN NOT NULL,
    is_significant_raw BOOLEAN NOT NULL,
    eligible BOOLEAN NOT NULL,
    exclusion_reason TEXT,
    neighbor_count INTEGER NOT NULL CHECK (neighbor_count >= 0),
    neighbors TEXT[] NOT NULL,
    standardized_ipr DOUBLE PRECISION,
    spatial_lag DOUBLE PRECISION,
    spatial_lag_ipr DOUBLE PRECISION,
    dqs DOUBLE PRECISION,
    dqs_level TEXT,
    calculation_version TEXT NOT NULL,
    calculated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (cod_ine, anio),
    CHECK (neighbor_count = cardinality(neighbors)),
    CHECK (is_significant = (cluster_type <> 'NS')),
    CHECK (is_significant_raw = (cluster_type_raw <> 'NS')),
    CHECK ((eligible AND neighbor_count > 0 AND local_moran_i IS NOT NULL
            AND p_value IS NOT NULL AND p_value_fdr IS NOT NULL AND exclusion_reason IS NULL)
           OR (NOT eligible AND neighbor_count = 0 AND local_moran_i IS NULL
               AND p_value IS NULL AND p_value_fdr IS NULL AND NOT is_significant
               AND NOT is_significant_raw AND exclusion_reason IS NOT NULL))
);
