"""Build an auditable manifest for files used by the project."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .descargas import SUFFIX as DOWNLOAD_SUFFIX, read_download


def pipeline_version(root: Path) -> str:
    """Return an immutable version when possible, without manual duplication."""
    configured = os.getenv("PIPELINE_VERSION")
    if configured:
        return configured
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ignored_by_git(root: Path, paths: list[str]) -> set[str]:
    """Rutas que el repositorio ignora.

    Sirve para dos cosas distintas. Un fichero ignorado y sin traza es un
    residuo local, una descarga vieja que quedó en el disco de alguien, y
    contarlo como fuente sin origen manda a buscar la procedencia de algo que
    no forma parte del proyecto. Un fichero ignorado pero con traza sí es una
    fuente: se ignora por tamaño y el pipeline lo vuelve a descargar, así que
    se inventaría y se marca como ausente del repositorio.
    """
    if not paths:
        return set()
    try:
        salida = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "--stdin"],
            input="\n".join(paths), capture_output=True, text=True,
        ).stdout
    except OSError:
        return set()
    return {linea.strip() for linea in salida.splitlines() if linea.strip()}


def first_seen(root: Path, relative: str) -> str | None:
    """Fecha del commit que incorporó el fichero al repositorio.

    Es una cota superior verificable de cuándo se obtuvo: el dato no puede
    haberse descargado después de entrar aquí. No sustituye a la fecha real de
    descarga, que la anota quien descarga, pero se puede comprobar.
    """
    try:
        salida = subprocess.check_output(
            ["git", "-C", str(root), "log", "--diff-filter=A", "--format=%aI",
             "-1", "--", relative],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return salida or None


def source_metadata(path: Path) -> dict | None:
    """Traza de descarga de un fichero, en cualquiera de sus dos ubicaciones.

    La validación externa nombra su acompañante sustituyendo la extensión
    (`.csv.gz` -> `.csv.metadata.json`) y el resto la añade al final; se aceptan
    las dos para no reescribir artefactos ya publicados.
    """
    directo = read_download(path)
    if directo:
        return directo
    alternativo = path.with_suffix(DOWNLOAD_SUFFIX)
    if alternativo.is_file():
        try:
            return json.loads(alternativo.read_text())
        except json.JSONDecodeError:
            return None
    return None


def build_manifest(
    root: Path = Path("."),
    directories: Iterable[str] = ("data/raw", "data/processed"),
) -> dict:
    """Describe current data files; hashes and dates are always computed here."""
    root = root.resolve()
    generated_at = datetime.now(timezone.utc).isoformat()
    version = pipeline_version(root)
    files = []
    candidates: list[tuple[Path, str]] = []
    for directory in directories:
        folder = root / directory
        if not folder.exists():
            continue
        for path in sorted(p for p in folder.rglob("*") if p.is_file()):
            if path.name.endswith(DOWNLOAD_SUFFIX):
                continue
            candidates.append((path, path.relative_to(root).as_posix()))

    ignored = ignored_by_git(root, [relative for _, relative in candidates])
    for path, relative in candidates:
        trace = source_metadata(path) or {}
        if relative in ignored and not trace:
            continue
        stat = path.stat()
        # Un CSV calculado por el pipeline no tiene origen que citar; una
        # fuente sin traza sí, y hay que verla. Sin esta distinción ambos
        # se confunden en el mismo recuento de «sin fecha de descarga».
        kind = ("descarga" if trace
                else "fuente_sin_origen" if path.is_relative_to(root / "data" / "raw")
                else "derivado")
        files.append({
            "kind": kind,
            "source": path.parts[len(root.parts)],
            "dataset": relative,
            # Los ficheros muy grandes no viajan en el repositorio; quien
            # clone tendrá que descargarlos con el pipeline.
            "in_repository": relative not in ignored,
            "url": trace.get("source_url"),
            # Sale de quien descargó. Sin traza queda vacío: la fecha del
            # fichero en disco no es la de la descarga, y rellenarla con
            # ella hacía que todas las fuentes pareciesen del mismo día.
            "download_date": trace.get("downloaded_at"),
            "file_modified": datetime.fromtimestamp(
                stat.st_mtime, timezone.utc
            ).isoformat(),
            "first_seen_in_repo": first_seen(root, relative),
            "organism": trace.get("organism"),
            "resource": trace.get("resource"),
            "reference_period": trace.get("statistical_period"),
            "file_size": stat.st_size,
            "sha256": sha256(path),
            "license": trace.get("license_url"),
            "pipeline_version": version,
            "status": "present",
        })
    kinds: dict[str, int] = {}
    for entry in files:
        kinds[entry["kind"]] = kinds.get(entry["kind"], 0) + 1
    return {
        "manifest_version": "1.1",
        "generated_at": generated_at,
        "pipeline_version": version,
        "summary": {
            "files": len(files),
            "by_kind": dict(sorted(kinds.items())),
            "sources_without_origin": sorted(
                entry["dataset"] for entry in files
                if entry["kind"] == "fuente_sin_origen"
            ),
        },
        "files": files,
    }


def write_manifest(root: Path = Path("."), output: Path | None = None) -> Path:
    root = root.resolve()
    output = output or root / "data" / "data_manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_manifest(root), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output

