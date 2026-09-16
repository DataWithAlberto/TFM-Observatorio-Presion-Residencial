CREATE TABLE IF NOT EXISTS indicadores_asequibilidad (
    cod_ine CHAR(5) NOT NULL,
    anio SMALLINT NOT NULL,
    precio_m2 NUMERIC(12,2) NOT NULL CHECK (precio_m2 > 0),
    num_tasaciones INTEGER,
    trimestres_disponibles SMALLINT NOT NULL,
    renta_media NUMERIC(12,2) NOT NULL CHECK (renta_media > 0),
    superficie_ref_m2 NUMERIC(7,2) NOT NULL CHECK (superficie_ref_m2 > 0),
    precio_vivienda NUMERIC(14,2) NOT NULL CHECK (precio_vivienda > 0),
    ratio_asequibilidad NUMERIC(12,6) NOT NULL CHECK (ratio_asequibilidad > 0),
    puntuacion_asequibilidad NUMERIC(7,4) NOT NULL
        CHECK (puntuacion_asequibilidad BETWEEN 0 AND 100),
    metodo_normalizacion TEXT NOT NULL,
    fuente_precio TEXT NOT NULL,
    fuente_renta TEXT NOT NULL,
    PRIMARY KEY (cod_ine, anio)
);

CREATE TABLE IF NOT EXISTS presion_turistica_score (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    fecha DATE NOT NULL,
    vut_por_1000_hab NUMERIC(14,6) NOT NULL,
    vut_por_km2 NUMERIC(14,6) NOT NULL,
    percentil_vut_por_1000_hab NUMERIC(8,4) NOT NULL,
    percentil_vut_por_km2 NUMERIC(8,4) NOT NULL,
    score_presion_turistica NUMERIC(8,4) NOT NULL
        CHECK (score_presion_turistica BETWEEN 0 AND 100),
    metodo TEXT NOT NULL,
    version_metodologia TEXT NOT NULL,
    PRIMARY KEY (cod_ine, fecha)
);

CREATE TABLE IF NOT EXISTS bootstrap_metadata (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
