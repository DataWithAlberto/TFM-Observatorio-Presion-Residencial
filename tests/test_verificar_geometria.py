"""Qué puede afirmar el verificador de la geometría municipal y qué no."""
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import box

from reproducibilidad.descargas import read_download
from reproducibilidad.verificar_geometria import comparar


def capa(tmp_path: Path, nombre: str, desplazamiento: float = 0.0) -> Path:
    marco = gpd.GeoDataFrame(
        {"cod_ine": [f"{i:05}" for i in range(4)], "nombre": [f"M{i}" for i in range(4)]},
        geometry=[box(i + desplazamiento, 0, i + 1 + desplazamiento, 1) for i in range(4)],
        crs=4326,
    )
    destino = tmp_path / f"{nombre}.gpkg"
    marco.to_file(destino, driver="GPKG")
    return destino


def test_reconoce_la_capa_de_la_que_salio(tmp_path):
    proyecto = capa(tmp_path, "proyecto")
    # La capa oficial llega en otra proyección, como la publican los organismos.
    oficial = gpd.read_file(proyecto).to_crs(25830)
    ruta_oficial = tmp_path / "oficial.gpkg"
    oficial.to_file(ruta_oficial, driver="GPKG")

    informe = comparar(ruta_oficial, proyecto)
    assert informe["es_la_fuente"]
    assert informe["coincidentes"] == informe["municipios"] == 4


def test_una_capa_parecida_no_cuenta_como_fuente(tmp_path):
    proyecto = capa(tmp_path, "proyecto")
    informe = comparar(capa(tmp_path, "vecina", desplazamiento=0.2), proyecto)
    assert not informe["es_la_fuente"]
    # Se parece mucho y aun así no basta: son límites distintos.
    assert 0.5 < informe["solape_mediano"] < 1.0
    assert informe["peores"][0]["cod_ine"]


def test_sin_coincidencia_no_se_anota_procedencia(tmp_path, monkeypatch):
    proyecto = capa(tmp_path, "proyecto")
    distinta = capa(tmp_path, "otra", desplazamiento=50.0)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        from reproducibilidad.verificar_geometria import main
        import sys
        monkeypatch.setattr(sys, "argv", [
            "verificar", str(distinta), "--url", "https://ejemplo/capa.zip",
            "--recurso", "Capa que no es", "--proyecto", str(proyecto),
        ])
        main()
    assert read_download(proyecto) is None
