#!/usr/bin/env python3
"""Calcula, audita y persiste el DQS después de validar el IPR."""
import argparse
import json
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from database.bootstrap.data_quality import calculate, persist, sensitivity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-db", action="store_true")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", "postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    processed = root / "data/processed"
    # Solo los cortes IPR realmente publicados; no inventar un histórico.
    ipr = pd.concat([pd.read_csv(p, dtype={"cod_ine": str}) for p in sorted(processed.glob("indice_presion_residencial_*.csv"))], ignore_index=True)
    import geopandas as gpd
    codes = set(gpd.read_file(root / "data/raw/municipios_306_con_geometria.gpkg", ignore_geometry=True).cod_ine.astype(str).str.zfill(5))
    rows, components, audit = calculate(processed, ipr, codes)
    (processed / "dqs_municipal.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    pd.DataFrame(components).assign(issues=lambda d: d.issues.map(json.dumps)).to_csv(processed / "dqs_componentes.csv", index=False)
    pd.DataFrame(audit).to_csv(processed / "dqs_auditoria.csv", index=False)
    report = sensitivity(rows)
    (processed / "dqs_sensibilidad.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    if not args.no_db:
        with create_engine(args.db_url).begin() as connection:
            persist(connection, rows, root / "sql/20_data_quality.sql")
    print(json.dumps({"municipios_anio": len(rows), "sensibilidad": report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
