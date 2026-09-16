CREATE TABLE IF NOT EXISTS riesgo_futuro_residencial_score (
    cod_ine CHAR(5) PRIMARY KEY REFERENCES municipios(cod_ine),
    anio_base SMALLINT NOT NULL,
    horizonte_climatico TEXT NOT NULL,
    escenario_climatico TEXT NOT NULL,
    tipo_valor_climatico TEXT NOT NULL CHECK (tipo_valor_climatico = 'ANOMALY'),
    proyeccion_duracion_max_ola_calor_dias DOUBLE PRECISION,
    proyeccion_grados_dia_refrigeracion DOUBLE PRECISION,
    proyeccion_racha_seca_max_dias DOUBLE PRECISION,
    tendencia_asequibilidad DOUBLE PRECISION,
    tendencia_turismo DOUBLE PRECISION,
    tendencia_especulacion DOUBLE PRECISION,
    tendencia_gentrificacion DOUBLE PRECISION,
    percentil_proyeccion_duracion_max_ola_calor_dias DOUBLE PRECISION,
    percentil_proyeccion_grados_dia_refrigeracion DOUBLE PRECISION,
    percentil_proyeccion_racha_seca_max_dias DOUBLE PRECISION,
    percentil_tendencia_asequibilidad DOUBLE PRECISION,
    percentil_tendencia_turismo DOUBLE PRECISION,
    percentil_tendencia_especulacion DOUBLE PRECISION,
    percentil_tendencia_gentrificacion DOUBLE PRECISION,
    score_riesgo_climatico DOUBLE PRECISION CHECK (score_riesgo_climatico BETWEEN 0 AND 100),
    n_tendencias_validas SMALLINT NOT NULL CHECK (n_tendencias_validas BETWEEN 0 AND 4),
    score_tendencia_presion DOUBLE PRECISION,
    elegible_score BOOLEAN NOT NULL,
    score_riesgo_futuro DOUBLE PRECISION CHECK (score_riesgo_futuro BETWEEN 0 AND 100),
    metodo TEXT NOT NULL,
    version_metodologia TEXT NOT NULL
);

ALTER TABLE riesgo_futuro_residencial_score
    ADD COLUMN IF NOT EXISTS tipo_valor_climatico TEXT;

ALTER TABLE riesgo_futuro_residencial_score
    DROP CONSTRAINT IF EXISTS riesgo_futuro_tipo_valor_climatico_check;

ALTER TABLE riesgo_futuro_residencial_score
    ADD CONSTRAINT riesgo_futuro_tipo_valor_climatico_check
    CHECK (tipo_valor_climatico = 'ANOMALY');
