CREATE TABLE IF NOT EXISTS indice_presion_residencial (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    nombre TEXT NOT NULL,
    provincia TEXT,
    score_origen_asequibilidad DOUBLE PRECISION,
    score_origen_turismo DOUBLE PRECISION,
    score_origen_especulacion DOUBLE PRECISION,
    score_origen_gentrificacion DOUBLE PRECISION,
    score_origen_riesgo_futuro DOUBLE PRECISION,
    score_orientado_asequibilidad DOUBLE PRECISION,
    score_orientado_turismo DOUBLE PRECISION,
    score_orientado_especulacion DOUBLE PRECISION,
    score_orientado_gentrificacion DOUBLE PRECISION,
    score_orientado_riesgo_futuro DOUBLE PRECISION,
    score_normalizado_asequibilidad DOUBLE PRECISION,
    score_normalizado_turismo DOUBLE PRECISION,
    score_normalizado_especulacion DOUBLE PRECISION,
    score_normalizado_gentrificacion DOUBLE PRECISION,
    score_normalizado_riesgo_futuro DOUBLE PRECISION,
    anio INTEGER NOT NULL,
    mes_turismo INTEGER NOT NULL,
    capas_validas INTEGER NOT NULL,
    elegible_ipr5_prospectivo BOOLEAN NOT NULL,
    ipr5_prospectivo DOUBLE PRECISION,
    percentil_ipr5_prospectivo DOUBLE PRECISION,
    categoria_ipr5_prospectivo TEXT,
    ranking_ipr5_prospectivo INTEGER,
    peso_asequibilidad DOUBLE PRECISION NOT NULL,
    contribucion_asequibilidad DOUBLE PRECISION,
    peso_turismo DOUBLE PRECISION NOT NULL,
    contribucion_turismo DOUBLE PRECISION,
    peso_especulacion DOUBLE PRECISION NOT NULL,
    contribucion_especulacion DOUBLE PRECISION,
    peso_gentrificacion DOUBLE PRECISION NOT NULL,
    contribucion_gentrificacion DOUBLE PRECISION,
    peso_riesgo_futuro DOUBLE PRECISION NOT NULL,
    contribucion_riesgo_futuro DOUBLE PRECISION,
    ipr4_nacional_observado DOUBLE PRECISION NOT NULL,
    percentil_ipr4 DOUBLE PRECISION NOT NULL,
    categoria_ipr4 TEXT NOT NULL,
    ranking_ipr4 INTEGER NOT NULL,
    ipr5_cota_inferior DOUBLE PRECISION NOT NULL,
    ipr5_cota_superior DOUBLE PRECISION NOT NULL,
    metodo TEXT NOT NULL,
    version_metodologia TEXT NOT NULL,
    PRIMARY KEY (cod_ine, anio),
    CHECK (ipr5_prospectivo IS NULL OR ipr5_prospectivo BETWEEN 0 AND 100),
    CHECK (ipr4_nacional_observado BETWEEN 0 AND 100),
    CHECK (capas_validas BETWEEN 0 AND 5)
);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'indice_presion_residencial'
          AND column_name = 'elegible_ipr5'
    ) THEN
        ALTER TABLE indice_presion_residencial
            RENAME COLUMN elegible_ipr5 TO elegible_ipr5_prospectivo;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'indice_presion_residencial'
          AND column_name = 'ipr5_observado'
    ) THEN
        ALTER TABLE indice_presion_residencial
            RENAME COLUMN ipr5_observado TO ipr5_prospectivo;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'indice_presion_residencial'
          AND column_name = 'percentil_ipr5'
    ) THEN
        ALTER TABLE indice_presion_residencial
            RENAME COLUMN percentil_ipr5 TO percentil_ipr5_prospectivo;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'indice_presion_residencial'
          AND column_name = 'categoria_ipr5'
    ) THEN
        ALTER TABLE indice_presion_residencial
            RENAME COLUMN categoria_ipr5 TO categoria_ipr5_prospectivo;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'indice_presion_residencial'
          AND column_name = 'ranking_ipr5'
    ) THEN
        ALTER TABLE indice_presion_residencial
            RENAME COLUMN ranking_ipr5 TO ranking_ipr5_prospectivo;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS ipr_sensibilidad_pesos (
    escenario TEXT NOT NULL,
    peso_asequibilidad DOUBLE PRECISION NOT NULL,
    peso_turismo DOUBLE PRECISION NOT NULL,
    peso_especulacion DOUBLE PRECISION NOT NULL,
    peso_gentrificacion DOUBLE PRECISION NOT NULL,
    peso_riesgo_futuro DOUBLE PRECISION NOT NULL,
    municipios INTEGER NOT NULL,
    spearman_score_base DOUBLE PRECISION NOT NULL,
    cambio_rango_medio DOUBLE PRECISION NOT NULL,
    cambio_rango_maximo DOUBLE PRECISION NOT NULL,
    solapamiento_top_10_pct DOUBLE PRECISION NOT NULL,
    anio INTEGER NOT NULL,
    PRIMARY KEY (escenario, anio)
);

CREATE INDEX IF NOT EXISTS idx_ipr_anio_ranking
    ON indice_presion_residencial (anio, ranking_ipr5_prospectivo);
