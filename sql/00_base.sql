CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS municipios (
    cod_ine CHAR(5) PRIMARY KEY,
    nombre TEXT NOT NULL,
    provincia TEXT NOT NULL,
    comunidad_autonoma TEXT,
    geometry geometry(MULTIPOLYGON, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS precios_vivienda (
    cod_ine CHAR(5) NOT NULL,
    anio INTEGER NOT NULL,
    trimestre INTEGER NOT NULL,
    precio_m2 DOUBLE PRECISION,
    valor_5menos DOUBLE PRECISION,
    valor_5mas DOUBLE PRECISION,
    num_tasaciones BIGINT,
    PRIMARY KEY (cod_ine, anio, trimestre),
    FOREIGN KEY (cod_ine) REFERENCES municipios(cod_ine),
    CHECK (trimestre BETWEEN 1 AND 4),
    CHECK (precio_m2 IS NULL OR precio_m2 > 0),
    CHECK (num_tasaciones IS NULL OR num_tasaciones >= 0)
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'precios_vivienda'::regclass AND contype = 'p'
    ) THEN
        ALTER TABLE precios_vivienda
            ADD CONSTRAINT precios_vivienda_pkey
            PRIMARY KEY (cod_ine, anio, trimestre);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'precios_vivienda'::regclass
          AND conname = 'precios_vivienda_cod_ine_fkey'
    ) THEN
        ALTER TABLE precios_vivienda
            ADD CONSTRAINT precios_vivienda_cod_ine_fkey
            FOREIGN KEY (cod_ine) REFERENCES municipios(cod_ine);
    END IF;
END $$;

ALTER TABLE precios_vivienda
    DROP CONSTRAINT IF EXISTS precios_vivienda_trimestre_check,
    DROP CONSTRAINT IF EXISTS precios_vivienda_precio_m2_check,
    DROP CONSTRAINT IF EXISTS precios_vivienda_num_tasaciones_check;

ALTER TABLE precios_vivienda
    ADD CONSTRAINT precios_vivienda_trimestre_check
        CHECK (trimestre BETWEEN 1 AND 4),
    ADD CONSTRAINT precios_vivienda_precio_m2_check
        CHECK (precio_m2 IS NULL OR precio_m2 > 0),
    ADD CONSTRAINT precios_vivienda_num_tasaciones_check
        CHECK (num_tasaciones IS NULL OR num_tasaciones >= 0);
