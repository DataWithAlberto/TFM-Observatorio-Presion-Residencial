CREATE TABLE IF NOT EXISTS variables_socioeconomicas_municipales (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    anio SMALLINT NOT NULL,
    mediana_renta_unidad_consumo NUMERIC(14,2),
    renta_neta_media_hogar NUMERIC(14,2),
    renta_neta_media_persona NUMERIC(14,2),
    pct_renta_alta_200 DOUBLE PRECISION,
    pct_renta_baja_60 DOUBLE PRECISION,
    indice_gini DOUBLE PRECISION,
    ratio_p80_p20 DOUBLE PRECISION,
    edad_media DOUBLE PRECISION,
    pct_hogares_unipersonales DOUBLE PRECISION,
    pct_mayor_65 DOUBLE PRECISION,
    pct_menor_18 DOUBLE PRECISION,
    pct_poblacion_espanola DOUBLE PRECISION,
    tamano_medio_hogar DOUBLE PRECISION,
    fuente TEXT NOT NULL,
    PRIMARY KEY (cod_ine, anio)
);

CREATE TABLE IF NOT EXISTS saldos_migratorios_municipales (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    anio SMALLINT NOT NULL,
    saldo_exterior INTEGER NOT NULL,
    saldo_interior INTEGER NOT NULL,
    saldo_total INTEGER NOT NULL,
    fuente TEXT NOT NULL,
    PRIMARY KEY (cod_ine, anio)
);

CREATE TABLE IF NOT EXISTS indicadores_gentrificacion (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    anio SMALLINT NOT NULL,
    poblacion INTEGER NOT NULL CHECK (poblacion > 0),
    log_cambio_poblacion_3a DOUBLE PRECISION,
    precio_m2 DOUBLE PRECISION,
    log_cambio_precio_m2_3a DOUBLE PRECISION,
    renta_neta_media_persona DOUBLE PRECISION,
    renta_neta_media_hogar DOUBLE PRECISION,
    mediana_renta_unidad_consumo DOUBLE PRECISION,
    log_cambio_renta_neta_media_persona_3a DOUBLE PRECISION,
    log_cambio_mediana_renta_unidad_consumo_3a DOUBLE PRECISION,
    brecha_precio_renta_3a DOUBLE PRECISION,
    pct_renta_alta_200 DOUBLE PRECISION,
    pct_renta_baja_60 DOUBLE PRECISION,
    cambio_pct_renta_alta_200_3a DOUBLE PRECISION,
    cambio_pct_renta_baja_60_3a DOUBLE PRECISION,
    sustitucion_composicion_renta_3a DOUBLE PRECISION,
    indice_gini DOUBLE PRECISION,
    ratio_p80_p20 DOUBLE PRECISION,
    cambio_indice_gini_3a DOUBLE PRECISION,
    cambio_ratio_p80_p20_3a DOUBLE PRECISION,
    edad_media DOUBLE PRECISION,
    pct_hogares_unipersonales DOUBLE PRECISION,
    pct_mayor_65 DOUBLE PRECISION,
    pct_menor_18 DOUBLE PRECISION,
    pct_poblacion_espanola DOUBLE PRECISION,
    tamano_medio_hogar DOUBLE PRECISION,
    cambio_edad_media_3a DOUBLE PRECISION,
    cambio_pct_hogares_unipersonales_3a DOUBLE PRECISION,
    cambio_pct_mayor_65_3a DOUBLE PRECISION,
    cambio_pct_menor_18_3a DOUBLE PRECISION,
    cambio_pct_poblacion_espanola_3a DOUBLE PRECISION,
    cambio_tamano_medio_hogar_3a DOUBLE PRECISION,
    transformacion_hogares_ajustada_3a DOUBLE PRECISION,
    saldo_total_acum_3a DOUBLE PRECISION,
    saldo_exterior_acum_3a DOUBLE PRECISION,
    saldo_interior_acum_3a DOUBLE PRECISION,
    salida_interior_por_1000_3a DOUBLE PRECISION,
    saldo_exterior_por_1000_3a DOUBLE PRECISION,
    ratio_asequibilidad DOUBLE PRECISION,
    puntuacion_asequibilidad DOUBLE PRECISION,
    score_presion_turistica DOUBLE PRECISION,
    score_presion_especulativa DOUBLE PRECISION,
    elegible_score BOOLEAN NOT NULL,
    PRIMARY KEY (cod_ine, anio)
);

CREATE TABLE IF NOT EXISTS riesgo_gentrificacion_score (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    anio SMALLINT NOT NULL,
    log_cambio_renta_neta_media_persona_3a DOUBLE PRECISION NOT NULL,
    brecha_precio_renta_3a DOUBLE PRECISION NOT NULL,
    transformacion_hogares_ajustada_3a DOUBLE PRECISION NOT NULL,
    winsor_log_cambio_renta_neta_media_persona_3a DOUBLE PRECISION NOT NULL,
    percentil_log_cambio_renta_neta_media_persona_3a DOUBLE PRECISION NOT NULL,
    winsor_brecha_precio_renta_3a DOUBLE PRECISION NOT NULL,
    percentil_brecha_precio_renta_3a DOUBLE PRECISION NOT NULL,
    winsor_transformacion_hogares_ajustada_3a DOUBLE PRECISION NOT NULL,
    percentil_transformacion_hogares_ajustada_3a DOUBLE PRECISION NOT NULL,
    score_riesgo_gentrificacion DOUBLE PRECISION NOT NULL
        CHECK (score_riesgo_gentrificacion BETWEEN 0 AND 100),
    municipios_cobertura_anio SMALLINT NOT NULL,
    pct_cobertura_anio DOUBLE PRECISION NOT NULL,
    panel_completo_306 BOOLEAN NOT NULL,
    universo_normalizacion TEXT NOT NULL,
    metodo TEXT NOT NULL,
    version_metodologia TEXT NOT NULL,
    PRIMARY KEY (cod_ine, anio)
);

COMMENT ON TABLE riesgo_gentrificacion_score IS
'Riesgo relativo de transformación compatible con gentrificación; no acredita gentrificación observada ni causalidad.';

-- Migración compatible con instalaciones previas de la versión 1.0.
ALTER TABLE variables_socioeconomicas_municipales
    ADD COLUMN IF NOT EXISTS pct_renta_alta_200 DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS pct_renta_baja_60 DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS indice_gini DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS ratio_p80_p20 DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS edad_media DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS pct_hogares_unipersonales DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS pct_mayor_65 DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS pct_menor_18 DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS pct_poblacion_espanola DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS tamano_medio_hogar DOUBLE PRECISION;

ALTER TABLE indicadores_gentrificacion
    ADD COLUMN IF NOT EXISTS pct_renta_alta_200 DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS pct_renta_baja_60 DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS cambio_pct_renta_alta_200_3a DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS cambio_pct_renta_baja_60_3a DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS sustitucion_composicion_renta_3a DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS indice_gini DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS ratio_p80_p20 DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS cambio_indice_gini_3a DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS cambio_ratio_p80_p20_3a DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS edad_media DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS pct_hogares_unipersonales DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS pct_mayor_65 DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS pct_menor_18 DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS pct_poblacion_espanola DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS tamano_medio_hogar DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS cambio_edad_media_3a DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS cambio_pct_hogares_unipersonales_3a DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS cambio_pct_mayor_65_3a DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS cambio_pct_menor_18_3a DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS cambio_pct_poblacion_espanola_3a DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS cambio_tamano_medio_hogar_3a DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS transformacion_hogares_ajustada_3a DOUBLE PRECISION;

ALTER TABLE riesgo_gentrificacion_score
    ADD COLUMN IF NOT EXISTS transformacion_hogares_ajustada_3a DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS winsor_transformacion_hogares_ajustada_3a DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS percentil_transformacion_hogares_ajustada_3a DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS municipios_cobertura_anio SMALLINT,
    ADD COLUMN IF NOT EXISTS pct_cobertura_anio DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS panel_completo_306 BOOLEAN,
    ADD COLUMN IF NOT EXISTS universo_normalizacion TEXT;

-- Columnas de la versión 1.0: estaban vacías y ya no forman parte del score.
ALTER TABLE riesgo_gentrificacion_score
    DROP COLUMN IF EXISTS salida_interior_por_1000_3a,
    DROP COLUMN IF EXISTS winsor_salida_interior_por_1000_3a,
    DROP COLUMN IF EXISTS percentil_salida_interior_por_1000_3a;
