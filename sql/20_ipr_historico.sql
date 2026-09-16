CREATE TABLE IF NOT EXISTS ipr_historical_runs (
    calculation_version TEXT PRIMARY KEY,
    dataset_sha256 TEXT NOT NULL,
    metadata JSONB NOT NULL,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS historical_municipality_universe (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    calculation_version TEXT NOT NULL REFERENCES ipr_historical_runs(calculation_version),
    nombre TEXT NOT NULL,
    included BOOLEAN NOT NULL,
    reason TEXT NOT NULL,
    start_year SMALLINT NOT NULL,
    end_year SMALLINT NOT NULL CHECK (end_year > start_year),
    PRIMARY KEY (cod_ine, calculation_version),
    CHECK (included OR reason <> '')
);

CREATE TABLE IF NOT EXISTS ipr_historical_scores (
    cod_ine CHAR(5) NOT NULL,
    anio SMALLINT NOT NULL,
    ipr_score DOUBLE PRECISION NOT NULL CHECK (ipr_score BETWEEN 0 AND 100),
    ipr_percentile DOUBLE PRECISION NOT NULL CHECK (ipr_percentile BETWEEN 0 AND 100),
    rank INTEGER NOT NULL CHECK (rank > 0),
    delta_ipr DOUBLE PRECISION,
    delta_since_start DOUBLE PRECISION NOT NULL,
    rank_change INTEGER,
    calculation_version TEXT NOT NULL,
    dataset_sha256 TEXT NOT NULL,
    PRIMARY KEY (cod_ine, anio, calculation_version),
    FOREIGN KEY (cod_ine, calculation_version)
        REFERENCES historical_municipality_universe(cod_ine, calculation_version)
);

CREATE TABLE IF NOT EXISTS ipr_historical_components (
    cod_ine CHAR(5) NOT NULL,
    anio SMALLINT NOT NULL,
    component TEXT NOT NULL CHECK (component IN ('asequibilidad','turismo','especulacion','gentrificacion')),
    value DOUBLE PRECISION NOT NULL CHECK (value BETWEEN 0 AND 100),
    layer_score DOUBLE PRECISION NOT NULL CHECK (layer_score BETWEEN 0 AND 100),
    weight DOUBLE PRECISION NOT NULL CHECK (weight > 0 AND weight < 1),
    contribution DOUBLE PRECISION NOT NULL CHECK (contribution BETWEEN 0 AND 100),
    raw_values TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_key TEXT NOT NULL,
    delta_component DOUBLE PRECISION,
    delta_contribution DOUBLE PRECISION,
    calculation_version TEXT NOT NULL,
    PRIMARY KEY (cod_ine, anio, component, calculation_version),
    FOREIGN KEY (cod_ine, anio, calculation_version)
        REFERENCES ipr_historical_scores(cod_ine, anio, calculation_version)
);
