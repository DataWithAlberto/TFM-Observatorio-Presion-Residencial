"""Traza de las descargas: qué se pidió, a quién, cuándo y qué llegó.

Cada fichero descargado deja al lado un `<nombre>.metadata.json` con la
dirección exacta, el instante de la descarga en UTC y la huella de lo
recibido. La fecha de modificación del fichero no sirve para esto: se pierde
al copiar, al clonar o al restaurar una copia de seguridad, y entonces todas
las fuentes parecen descargadas el mismo día.

El vocabulario es el que ya usaba la validación externa, para que el anexo de
fuentes lea todas las fuentes igual.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SUFFIX = ".metadata.json"


def metadata_path(destination: Path) -> Path:
    """Ruta del acompañante de un fichero descargado."""
    return destination.with_suffix(destination.suffix + SUFFIX)


def sha256(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_download(
    destination: Path,
    url: str,
    *,
    organism: str | None = None,
    resource: str | None = None,
    statistical_period: str | None = None,
    license_url: str | None = None,
    payload: bytes | None = None,
    **extra: object,
) -> dict:
    """Anota la descarga de `destination` y devuelve lo anotado.

    `payload` es lo recibido por la red cuando el fichero guardado no es una
    copia literal, por ejemplo si se comprime o se recorta: entonces se guardan
    las dos huellas, la de lo que envió el servidor y la del archivo local. El
    resto de campos describen la fuente y solo se escriben si se conocen; no se
    inventa un periodo ni una licencia que el llamante no sepa.
    """
    destination = Path(destination)
    if not destination.is_file():
        raise FileNotFoundError(f"No hay nada que anotar en {destination}")
    record: dict[str, object] = {
        "source_url": url,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "archive_sha256": sha256(destination),
    }
    if payload is not None:
        record["download_sha256"] = hashlib.sha256(payload).hexdigest()
    for key, value in (
        ("organism", organism),
        ("resource", resource),
        ("statistical_period", statistical_period),
        ("license_url", license_url),
    ):
        if value:
            record[key] = value
    record.update({key: value for key, value in extra.items() if value is not None})
    path = metadata_path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".part")
    temporary.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)
    return record


def read_download(destination: Path) -> dict | None:
    """Lo anotado para un fichero, o nada si se obtuvo sin dejar traza."""
    path = metadata_path(Path(destination))
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
