# Ejecución — capa de presión turística

Requisitos: servicio `db` de Docker Compose operativo y el entorno virtual del
proyecto activo. Ejecute los comandos desde la raíz del repositorio.

```bash
Requisitos: contenedor `tfm-postgis` operativo en el puerto 5433 y entorno
virtual del proyecto creado en `venv`.

```bash
cd /ruta/al/repositorio/TFM
export PROJ_NETWORK=OFF
python 05_turismo_ingesta.py
python 06_turismo_indicadores.py
python 07_indice_presion_turistica.py
```

Para validar los CSV sin escribir en PostgreSQL:

```bash
python 05_turismo_ingesta.py --no-db
python 06_turismo_indicadores.py --no-db
python 07_indice_presion_turistica.py --no-db
```

Para reutilizar descargas existentes:

```bash
python 05_turismo_ingesta.py --skip-download
```

La conexión puede sobrescribirse con `DATABASE_URL` o `--db-url`. Las cargas
son idempotentes mediante claves `(cod_ine, fecha)` y `ON CONFLICT`.

Validaciones automáticas:

- exactamente 306 municipios en cada fecha;
- ausencia de duplicados municipio-fecha;
- claves foráneas hacia `municipios`;
- población y superficie positivas;
- indicadores no negativos;
- score dentro de 0–100;
- control de correlación entre variables del score;
- impresión de Barcelona, Palma, Málaga, Donostia/San Sebastián, Gijón,
  Oviedo y Santander.
