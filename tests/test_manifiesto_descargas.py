"""La traza de descarga y lo que el manifiesto puede afirmar con ella."""
import json
from pathlib import Path

import pytest

from reproducibilidad.descargas import metadata_path, read_download, record_download
from reproducibilidad.manifest import build_manifest, source_metadata

ROOT = Path(__file__).resolve().parents[1]


def datos(tmp_path: Path, nombre: str = "tabla.csv", contenido: bytes = b"a;b\n1;2\n") -> Path:
    destino = tmp_path / "data" / "raw" / nombre
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return destino


def test_la_traza_guarda_origen_instante_y_huella(tmp_path):
    destino = datos(tmp_path)
    anotado = record_download(
        destino, "https://www.ine.es/tabla.csv",
        organism="Instituto Nacional de Estadística",
        resource="Tabla de prueba",
        license_url="https://www.ine.es/dyngs/AYU/index.htm?cid=125",
        payload=b"a;b\n1;2\n",
    )
    assert metadata_path(destino).name == "tabla.csv.metadata.json"
    assert anotado["source_url"].endswith("tabla.csv")
    assert anotado["downloaded_at"].endswith("+00:00")
    # Con copia literal las dos huellas coinciden; con archivo comprimido no.
    assert anotado["archive_sha256"] == anotado["download_sha256"]
    assert read_download(destino) == anotado


def test_no_se_anota_lo_que_no_existe(tmp_path):
    with pytest.raises(FileNotFoundError):
        record_download(tmp_path / "ausente.csv", "https://ejemplo/x.csv")


def test_los_campos_desconocidos_no_se_inventan(tmp_path):
    destino = datos(tmp_path)
    anotado = record_download(destino, "https://ejemplo/x.csv")
    assert set(anotado) == {"source_url", "downloaded_at", "archive_sha256"}


def test_el_manifiesto_usa_la_traza_y_separa_la_fecha_del_fichero(tmp_path):
    con_traza = datos(tmp_path, "con_traza.csv")
    sin_traza = datos(tmp_path, "sin_traza.csv")
    record_download(
        con_traza, "https://www.ine.es/jaxiT3/files/t/csv_bdsc/39363.csv",
        organism="Instituto Nacional de Estadística",
        resource="Viviendas turísticas y plazas, tabla 39363",
        statistical_period="2023",
        license_url="https://www.ine.es/dyngs/AYU/index.htm?cid=125",
    )
    ficheros = {f["dataset"]: f for f in build_manifest(tmp_path)["files"]}

    # El acompañante describe a otro fichero; no es un dato del proyecto.
    assert not any(nombre.endswith(".metadata.json") for nombre in ficheros)

    anotado = ficheros["data/raw/con_traza.csv"]
    assert anotado["url"].endswith("39363.csv")
    assert anotado["organism"] == "Instituto Nacional de Estadística"
    assert anotado["reference_period"] == "2023"
    assert anotado["license"].startswith("https://www.ine.es/")
    assert anotado["download_date"]

    # Sin traza no hay fecha de descarga que dar. La del fichero se publica
    # aparte y con su nombre, porque no dice cuándo se obtuvo el dato.
    huerfano = ficheros["data/raw/sin_traza.csv"]
    assert huerfano["download_date"] is None
    assert huerfano["url"] is None
    assert huerfano["file_modified"]


def test_una_fuente_sin_origen_no_se_confunde_con_un_producto(tmp_path):
    fuente = datos(tmp_path, "geometria.gpkg")
    derivado = tmp_path / "data" / "processed" / "indice.csv"
    derivado.parent.mkdir(parents=True, exist_ok=True)
    derivado.write_text("cod_ine,score\n01059,50\n")
    descargado = datos(tmp_path, "tabla_bajada.csv")
    record_download(descargado, "https://www.ine.es/tabla.csv")

    manifiesto = build_manifest(tmp_path)
    tipos = {f["dataset"]: f["kind"] for f in manifiesto["files"]}
    assert tipos["data/raw/tabla_bajada.csv"] == "descarga"
    assert tipos["data/raw/geometria.gpkg"] == "fuente_sin_origen"
    assert tipos["data/processed/indice.csv"] == "derivado"

    resumen = manifiesto["summary"]
    assert resumen["by_kind"] == {"derivado": 1, "descarga": 1, "fuente_sin_origen": 1}
    # Lo que hay que mirar en una auditoría queda nombrado, no solo contado.
    assert resumen["sources_without_origin"] == ["data/raw/geometria.gpkg"]


def test_se_acepta_la_traza_de_la_validacion_externa(tmp_path):
    # Ese script nombra su acompañante sustituyendo la extensión del archivo
    # comprimido, y sus artefactos ya publicados no se reescriben.
    destino = datos(tmp_path, "VDP001_01.csv.gz", b"contenido")
    destino.with_suffix(".metadata.json").write_text(
        json.dumps({"source_url": "https://cdn.mivau.gob.es/VDP001_01.csv",
                    "downloaded_at": "2026-09-11T16:20:56.722014+00:00"})
    )
    assert source_metadata(destino)["source_url"].endswith("VDP001_01.csv")


def test_todas_las_descargas_del_pipeline_dejan_traza():
    """Ningún descargador puede guardar un fichero sin decir de dónde salió."""
    descargadores = [
        "01_municipios.py", "02_precios_vivienda.py", "03_renta_ine.py",
        "05_turismo_ingesta.py", "08_fuentes_especulacion.py",
        "11_fuentes_gentrificacion.py", "15_fuentes_riesgo_futuro.py",
    ]
    sin_traza = [
        nombre for nombre in descargadores
        if "record_download" not in (ROOT / nombre).read_text()
    ]
    assert not sin_traza, f"Descargan sin anotar la fuente: {sin_traza}"
    # La validación externa mantiene su propio registro, anterior y equivalente.
    assert "downloaded_at" in (ROOT / "24_validacion_externa_ipr.py").read_text()


def test_un_residuo_local_no_es_una_fuente_pendiente(tmp_path):
    """Lo que el repositorio ignora solo entra si tiene traza de descarga."""
    import subprocess
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text(
        "data/raw/residuo.csv\ndata/raw/grande.csv\n"
    )
    datos(tmp_path, "residuo.csv")           # descarga vieja de alguien
    grande = datos(tmp_path, "grande.csv")   # fuente real, fuera por tamaño
    record_download(grande, "https://www.ine.es/atlas.csv")
    datos(tmp_path, "normal.csv")

    ficheros = {f["dataset"]: f for f in build_manifest(tmp_path)["files"]}
    assert "data/raw/residuo.csv" not in ficheros
    assert ficheros["data/raw/grande.csv"]["kind"] == "descarga"
    # Quien clone no tendrá ese fichero: lo tiene que volver a descargar.
    assert ficheros["data/raw/grande.csv"]["in_repository"] is False
    assert ficheros["data/raw/normal.csv"]["in_repository"] is True
