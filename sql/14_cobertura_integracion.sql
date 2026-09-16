CREATE TABLE IF NOT EXISTS cobertura_temporal_integracion (
    capa TEXT NOT NULL,
    anio SMALLINT NOT NULL,
    filas_fuente INTEGER NOT NULL CHECK (filas_fuente >= 0),
    municipios_con_fila SMALLINT NOT NULL CHECK (municipios_con_fila BETWEEN 0 AND 306),
    pct_municipios_con_fila DOUBLE PRECISION NOT NULL CHECK (pct_municipios_con_fila BETWEEN 0 AND 100),
    municipios_valor_valido SMALLINT NOT NULL CHECK (municipios_valor_valido BETWEEN 0 AND 306),
    pct_municipios_valor_valido DOUBLE PRECISION NOT NULL CHECK (pct_municipios_valor_valido BETWEEN 0 AND 100),
    municipios_elegibles_score SMALLINT NOT NULL CHECK (municipios_elegibles_score BETWEEN 0 AND 306),
    pct_municipios_elegibles_score DOUBLE PRECISION NOT NULL CHECK (pct_municipios_elegibles_score BETWEEN 0 AND 100),
    observaciones_temporales SMALLINT NOT NULL CHECK (observaciones_temporales >= 0),
    cobertura_completa_306 BOOLEAN NOT NULL,
    PRIMARY KEY (capa, anio)
);

CREATE TABLE IF NOT EXISTS cobertura_municipio_anio_integracion (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    nombre TEXT NOT NULL,
    anio SMALLINT NOT NULL,
    asequibilidad_disponible BOOLEAN NOT NULL,
    asequibilidad_observaciones SMALLINT NOT NULL,
    turismo_disponible BOOLEAN NOT NULL,
    turismo_observaciones SMALLINT NOT NULL,
    especulacion_disponible BOOLEAN NOT NULL,
    especulacion_observaciones SMALLINT NOT NULL,
    gentrificacion_disponible BOOLEAN NOT NULL,
    gentrificacion_observaciones SMALLINT NOT NULL,
    capas_disponibles SMALLINT NOT NULL CHECK (capas_disponibles BETWEEN 0 AND 4),
    elegible_indice_completo BOOLEAN NOT NULL,
    estado_integracion TEXT NOT NULL CHECK (
        estado_integracion IN (
            'sin_cobertura',
            'historico_parcial_observado',
            'observado_completo'
        )
    ),
    PRIMARY KEY (cod_ine, anio)
);

COMMENT ON TABLE cobertura_temporal_integracion IS
'Metadatos reproducibles de filas, valores válidos y elegibilidad de las capas 1–4; no contiene un índice compuesto.';
COMMENT ON TABLE cobertura_municipio_anio_integracion IS
'Disponibilidad observada por municipio-año. FALSE significa ausencia, nunca presión cero.';

CREATE TABLE IF NOT EXISTS cobertura_corte_ipr5_integracion (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    nombre TEXT NOT NULL,
    score_asequibilidad DOUBLE PRECISION,
    asequibilidad_disponible BOOLEAN NOT NULL,
    score_turismo DOUBLE PRECISION,
    turismo_disponible BOOLEAN NOT NULL,
    score_especulacion DOUBLE PRECISION,
    especulacion_disponible BOOLEAN NOT NULL,
    score_gentrificacion DOUBLE PRECISION,
    gentrificacion_disponible BOOLEAN NOT NULL,
    anio_base SMALLINT NOT NULL CHECK (anio_base = 2023),
    horizonte_climatico TEXT NOT NULL,
    escenario_climatico TEXT NOT NULL,
    tipo_valor_climatico TEXT NOT NULL CHECK (tipo_valor_climatico = 'ANOMALY'),
    score_riesgo_futuro DOUBLE PRECISION,
    riesgo_futuro_elegible_origen BOOLEAN NOT NULL,
    version_riesgo_futuro TEXT NOT NULL,
    riesgo_futuro_disponible BOOLEAN NOT NULL,
    capas_actuales_disponibles SMALLINT NOT NULL
        CHECK (capas_actuales_disponibles BETWEEN 0 AND 4),
    capas_ipr5_disponibles SMALLINT NOT NULL
        CHECK (capas_ipr5_disponibles BETWEEN 0 AND 5),
    elegible_ipr4_observado BOOLEAN NOT NULL,
    elegible_ipr5_prospectivo BOOLEAN NOT NULL,
    motivo_no_elegible_ipr5 TEXT NOT NULL,
    anio_corte SMALLINT NOT NULL CHECK (anio_corte = 2023),
    fecha_turismo DATE NOT NULL CHECK (fecha_turismo = DATE '2023-08-01'),
    tipo_producto TEXT NOT NULL CHECK (tipo_producto = 'corte_ipr5_prospectivo'),
    PRIMARY KEY (cod_ine, anio_corte)
);

COMMENT ON TABLE cobertura_corte_ipr5_integracion IS
'Corte transversal separado: cuatro capas actuales observadas e incorporación prospectiva del riesgo futuro.';
