CREATE TABLE IF NOT EXISTS turismo_fuentes (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    fecha DATE NOT NULL,
    viviendas_turisticas INTEGER NOT NULL CHECK (viviendas_turisticas >= 0),
    plazas INTEGER NOT NULL CHECK (plazas >= 0),
    plazas_por_vivienda NUMERIC(8,3),
    fuente TEXT NOT NULL,
    PRIMARY KEY (cod_ine, fecha)
);

CREATE TABLE IF NOT EXISTS poblacion_municipal (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    anio SMALLINT NOT NULL,
    poblacion INTEGER NOT NULL CHECK (poblacion > 0),
    fuente TEXT NOT NULL,
    PRIMARY KEY (cod_ine, anio)
);

-- Las tablas indicadores_turisticos y presion_turistica_score se crean de
-- forma idempotente desde 06_turismo_indicadores.py y
-- 07_indice_presion_turistica.py con sus restricciones completas.

CREATE TABLE IF NOT EXISTS vut_complementario (
    cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
    fecha DATE NOT NULL,
    fuente TEXT NOT NULL,
    tipo_fuente TEXT NOT NULL CHECK (
        tipo_fuente IN ('registro_autonomico', 'inside_airbnb')
    ),
    vut INTEGER CHECK (vut >= 0),
    plazas INTEGER CHECK (plazas >= 0),
    cobertura_geografica TEXT NOT NULL,
    calidad TEXT NOT NULL CHECK (calidad IN ('alta', 'media', 'baja')),
    PRIMARY KEY (cod_ine, fecha, fuente)
);

COMMENT ON TABLE vut_complementario IS
'Módulo separado de contraste; nunca alimenta ni rellena el score nacional.';
