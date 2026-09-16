"""Comprueba de qué capa oficial salió la geometría municipal del proyecto.

El GeoPackage `municipios_306_con_geometria.gpkg` llegó al repositorio ya
hecho: ningún script lo descarga y no hay registro de su origen. Conserva un
campo `CODNUT2`, que es de las capas de límites administrativos del Instituto
Geográfico Nacional, pero una sospecha no es una atribución.

Esto compara el fichero del proyecto con una capa descargada y mide cuánto se
parecen polígono a polígono. Si encajan, anota la procedencia con la misma
traza que el resto de descargas; si no, lo dice y no escribe nada. La regla es
la de siempre: no se atribuye una fuente que no se ha comprobado.

Uso:
    python -m reproducibilidad.verificar_geometria ruta/al/fichero.shp \\
        --url https://...  --recurso "Líneas límite municipales"
"""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd

from .descargas import record_download

PROYECTO = Path("data/raw/municipios_306_con_geometria.gpkg")
# Dos recintos del mismo municipio nunca coinciden al bit: se comparan áreas.
# Por debajo de este solape ya no se puede hablar del mismo límite.
UMBRAL_COINCIDENCIA = 0.999


def solape(propia: gpd.GeoSeries, candidata: gpd.GeoDataFrame) -> list[float]:
    """Para cada municipio, el mejor solape relativo con la capa candidata.

    Se usa la intersección sobre la unión: vale uno cuando los dos polígonos
    son el mismo y baja en cuanto sobra o falta superficie, de modo que
    distingue un límite idéntico de otro parecido.
    """
    indice = candidata.sindex
    resultados = []
    for geometria in propia:
        posibles = list(indice.intersection(geometria.bounds))
        mejor = 0.0
        for posicion in posibles:
            otra = candidata.geometry.iloc[posicion]
            interseccion = geometria.intersection(otra).area
            if interseccion <= 0:
                continue
            union = geometria.union(otra).area
            if union > 0:
                mejor = max(mejor, interseccion / union)
        resultados.append(mejor)
    return resultados


def comparar(candidato: Path, proyecto: Path = PROYECTO) -> dict:
    propia = gpd.read_file(proyecto).to_crs(4326)
    candidata = gpd.read_file(candidato).to_crs(4326)
    valores = solape(propia.geometry, candidata)
    ordenados = sorted(zip(valores, propia["cod_ine"], propia["nombre"]))
    coincidentes = sum(1 for valor in valores if valor >= UMBRAL_COINCIDENCIA)
    return {
        "municipios": len(valores),
        "coincidentes": coincidentes,
        "solape_minimo": ordenados[0][0] if ordenados else 0.0,
        "solape_mediano": sorted(valores)[len(valores) // 2] if valores else 0.0,
        "peores": [
            {"cod_ine": codigo, "nombre": nombre, "solape": round(valor, 6)}
            for valor, codigo, nombre in ordenados[:5]
        ],
        "es_la_fuente": bool(valores) and coincidentes == len(valores),
        "campos_candidata": list(candidata.columns),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidato", type=Path, help="Capa descargada del organismo")
    parser.add_argument("--url", required=True, help="Dirección exacta de descarga")
    parser.add_argument("--organismo", default="Instituto Geográfico Nacional")
    parser.add_argument("--recurso", required=True, help="Nombre del producto descargado")
    parser.add_argument(
        "--licencia",
        default="https://centrodedescargas.cnig.es/CentroDescargas/politica-datos",
    )
    parser.add_argument("--proyecto", type=Path, default=PROYECTO)
    args = parser.parse_args()

    informe = comparar(args.candidato, args.proyecto)
    print(f"Municipios comparados: {informe['municipios']}")
    print(f"Coinciden por encima de {UMBRAL_COINCIDENCIA}: {informe['coincidentes']}")
    print(f"Solape mediano: {informe['solape_mediano']:.6f} · mínimo: {informe['solape_minimo']:.6f}")
    for peor in informe["peores"]:
        print(f"  {peor['cod_ine']} {peor['nombre']}: {peor['solape']}")

    if not informe["es_la_fuente"]:
        print(
            "\nNo se anota nada: esta capa no reproduce los límites del proyecto.\n"
            "Puede ser otro producto, otra fecha de corte u otra generalización."
        )
        raise SystemExit(1)

    record_download(
        args.proyecto, args.url,
        organism=args.organismo,
        resource=args.recurso,
        license_url=args.licencia,
        verified_against=args.candidato.name,
        verification="solape por municipio >= "
                     f"{UMBRAL_COINCIDENCIA} en los {informe['municipios']}",
    )
    print(f"\nProcedencia anotada en {args.proyecto}.metadata.json")


if __name__ == "__main__":
    main()
