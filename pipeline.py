#!/usr/bin/env python3
"""Run the scientific pipeline with auditable structured execution logs.

The default commands intentionally mirror README.md. External downloads are the
only retried operations; database and analytical stages fail fast.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from reproducibilidad.manifest import pipeline_version, write_manifest

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "data" / "runs"
STAGES = [
    ("ingesta_municipios", ["01_municipios.py"], True),
    ("ingesta_precios", ["02_precios_vivienda.py"], True),
    ("carga_postgis_base", ["00_carga_postgis_base.py"], False),
    ("ingesta_renta", ["03_renta_ine.py"], True),
    ("transformacion_asequibilidad", ["04_indice_asequibilidad.py"], False),
    ("ingesta_turismo", ["05_turismo_ingesta.py"], True),
    ("transformacion_turismo", ["06_turismo_indicadores.py"], False),
    ("calculo_turismo", ["07_indice_presion_turistica.py"], False),
    ("ingesta_especulacion", ["08_fuentes_especulacion.py"], True),
    ("transformacion_especulacion", ["09_indicadores_especulativos.py"], False),
    ("calculo_especulacion", ["10_indice_presion_especulativa.py"], False),
    ("ingesta_gentrificacion", ["11_fuentes_gentrificacion.py"], True),
    ("transformacion_gentrificacion", ["12_indicadores_gentrificacion.py"], False),
    ("calculo_gentrificacion", ["13_indice_riesgo_gentrificacion.py"], False),
    ("auditoria_integracion", ["14_auditoria_integracion.py", "--check-db", "--load-db"], False),
    ("ingesta_riesgo_futuro", ["15_fuentes_riesgo_futuro.py"], True),
    ("transformacion_riesgo_futuro", ["16_indicadores_riesgo_futuro.py"], False),
    ("calculo_riesgo_futuro", ["17_indice_riesgo_futuro.py"], False),
    ("calculo_ipr", ["18_indice_presion_residencial.py"], False),
    ("validacion_publicacion", ["19_validacion_indice_presion_residencial.py", "--strict"], False),
    ("ipr_historico", ["20_ipr_historico.py"], False),
    ("validacion_ipr_historico", ["21_validacion_ipr_historico.py"], False),
    ("data_quality_score", ["22_data_quality_score.py"], False),
    ("analisis_espacial", ["23_analisis_espacial_ipr.py"], False),
    ("validacion_externa", ["24_validacion_externa_ipr.py"], False),
    ("analisis_ml_exploratorio", ["25_analisis_ml_exploratorio.py"], False),
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def records_from_stdout(stdout: str) -> int | None:
    """Extract a conventional row count without imposing an output contract."""
    for line in reversed(stdout.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        for key in ("filas", "rows", "registros", "records"):
            if isinstance(value, dict) and isinstance(value.get(key), int):
                return value[key]
    return None


def run_stage(run_id: str, name: str, command: list[str], retryable: bool, log) -> None:
    started = time.monotonic()
    record = {"run_id": run_id, "stage": name, "started_at": now(), "status": "running"}
    log.write(json.dumps(record, ensure_ascii=False) + "\n")
    log.flush()
    attempts = 2 if retryable else 1
    error = None
    for attempt in range(1, attempts + 1):
        completed = subprocess.run([sys.executable, *command], cwd=ROOT, text=True, capture_output=True)
        if completed.returncode == 0:
            record.update({"status": "success", "attempt": attempt, "stdout": completed.stdout[-4000:]})
            count = records_from_stdout(completed.stdout)
            if count is not None:
                record["records_processed"] = count
            break
        error = completed.stderr[-4000:] or completed.stdout[-4000:]
        record.update({"attempt": attempt, "return_code": completed.returncode})
    else:
        record.update({"status": "failed", "error": error})
    record.update({"finished_at": now(), "duration_seconds": round(time.monotonic() - started, 3)})
    log.write(json.dumps(record, ensure_ascii=False) + "\n")
    log.flush()
    if record["status"] == "failed":
        raise RuntimeError(f"Etapa {name} fallida: {error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-stage", choices=[s[0] for s in STAGES])
    parser.add_argument("--max-stage", choices=[s[0] for s in STAGES])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    selected = STAGES[:]
    if args.from_stage:
        selected = selected[next(i for i, s in enumerate(selected) if s[0] == args.from_stage):]
    if args.max_stage:
        selected = selected[: next(i for i, s in enumerate(selected) if s[0] == args.max_stage) + 1]
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    started = time.monotonic()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{run_id}.jsonl"
    with log_path.open("w", encoding="utf-8") as log:
        log.write(json.dumps({"run_id": run_id, "pipeline_version": pipeline_version(ROOT), "started_at": now(), "status": "started"}) + "\n")
        try:
            for name, command, retryable in selected:
                if args.dry_run:
                    log.write(json.dumps({"run_id": run_id, "stage": name, "command": command, "status": "planned"}) + "\n")
                else:
                    run_stage(run_id, name, command, retryable, log)
            if not args.dry_run:
                write_manifest(ROOT)
            log.write(json.dumps({"run_id": run_id, "finished_at": now(), "duration_seconds": round(time.monotonic() - started, 3), "status": "success", "manifest": "data/data_manifest.json"}) + "\n")
        except Exception as exc:
            log.write(json.dumps({"run_id": run_id, "finished_at": now(), "duration_seconds": round(time.monotonic() - started, 3), "status": "failed", "error": str(exc)}) + "\n")
            print(f"Pipeline fallido. RUN_ID={run_id}. Log: {log_path}", file=sys.stderr)
            return 1
    print(json.dumps({"run_id": run_id, "status": "success", "log": str(log_path.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
