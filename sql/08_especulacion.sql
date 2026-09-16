CREATE TABLE IF NOT EXISTS transacciones_vivienda_municipal (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    anio SMALLINT NOT NULL,
    trimestre SMALLINT NOT NULL CHECK (trimestre BETWEEN 1 AND 4),
    compraventas INTEGER NOT NULL CHECK (compraventas >= 0),
    fuente TEXT NOT NULL,
    PRIMARY KEY (cod_ine, anio, trimestre)
);

CREATE TABLE IF NOT EXISTS parque_viviendas_2021 (
    cod_ine CHAR(5) PRIMARY KEY REFERENCES municipios(cod_ine),
    anio_referencia SMALLINT NOT NULL CHECK (anio_referencia = 2021),
    viviendas INTEGER NOT NULL CHECK (viviendas > 0),
    fuente TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS titularidad_corporativa_catastro (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    anio SMALLINT NOT NULL,
    inmuebles_total INTEGER NOT NULL CHECK (inmuebles_total > 0),
    inmuebles_persona_fisica INTEGER NOT NULL CHECK (inmuebles_persona_fisica >= 0),
    inmuebles_sociedades INTEGER NOT NULL CHECK (inmuebles_sociedades >= 0),
    inmuebles_otras_entidades INTEGER NOT NULL CHECK (inmuebles_otras_entidades >= 0),
    fuente TEXT NOT NULL,
    PRIMARY KEY (cod_ine, anio),
    CHECK (
        inmuebles_total =
        inmuebles_persona_fisica + inmuebles_sociedades + inmuebles_otras_entidades
    )
);

COMMENT ON TABLE titularidad_corporativa_catastro IS
'Indicador complementario. Excluye los 17 municipios objetivo de País Vasco y Navarra; no alimenta el score nacional.';

CREATE TABLE IF NOT EXISTS indicadores_especulativos (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    anio SMALLINT NOT NULL,
    compraventas INTEGER NOT NULL CHECK (compraventas >= 0),
    trimestres_tx SMALLINT NOT NULL CHECK (trimestres_tx = 4),
    viviendas INTEGER NOT NULL CHECK (viviendas > 0),
    anio_referencia SMALLINT NOT NULL CHECK (anio_referencia = 2021),
    tasa_rotacion NUMERIC(14,8) NOT NULL CHECK (tasa_rotacion >= 0),
    precio_m2 NUMERIC(14,4) NOT NULL CHECK (precio_m2 > 0),
    trimestres_precio SMALLINT NOT NULL CHECK (trimestres_precio BETWEEN 1 AND 4),
    crecimiento_precio NUMERIC(14,8),
    aceleracion_precio NUMERIC(14,8),
    renta_media NUMERIC(14,2),
    crecimiento_renta NUMERIC(14,8),
    desacoplamiento_precio_renta NUMERIC(14,8),
    pct_propiedad_sociedades NUMERIC(12,8)
        CHECK (pct_propiedad_sociedades BETWEEN 0 AND 100),
    variacion_propiedad_sociedades NUMERIC(12,8),
    elegible_score_principal BOOLEAN NOT NULL,
    PRIMARY KEY (cod_ine, anio)
);

CREATE TABLE IF NOT EXISTS presion_especulativa_score (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    anio SMALLINT NOT NULL,
    tasa_rotacion NUMERIC(14,8) NOT NULL,
    aceleracion_precio NUMERIC(14,8) NOT NULL,
    desacoplamiento_precio_renta NUMERIC(14,8) NOT NULL,
    percentil_tasa_rotacion NUMERIC(8,4) NOT NULL,
    percentil_aceleracion_precio NUMERIC(8,4) NOT NULL,
    percentil_desacoplamiento_precio_renta NUMERIC(8,4) NOT NULL,
    score_presion_especulativa NUMERIC(8,4) NOT NULL
        CHECK (score_presion_especulativa BETWEEN 0 AND 100),
    metodo TEXT NOT NULL,
    version_metodologia TEXT NOT NULL,
    PRIMARY KEY (cod_ine, anio)
);
