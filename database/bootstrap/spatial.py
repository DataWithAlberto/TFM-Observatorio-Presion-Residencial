"""Carga atómica de resultados ya calculados; el arranque no ejecuta permutaciones."""
import hashlib
import json
from pathlib import Path

from sqlalchemy import text


def load_spatial(engine, root: Path):
    path = root / "data/processed/spatial/spatial_ipr.json"
    payload = json.loads(path.read_text())
    metadata = payload["metadata"]
    for key, source in metadata["sources"].items():
        source_path = root / ("data/raw" if key == "geometry" else "data/processed") / source["file"]
        if hashlib.sha256(source_path.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError("Resultados espaciales obsoletos: ejecute 23_analisis_espacial_ipr.py")
    if not payload["audit"]["passed"]:
        raise ValueError("No se cargan resultados con auditoría fallida")
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM ipr_spatial_local"))
        connection.execute(text("DELETE FROM ipr_spatial_global"))
        for year in payload["years"]:
            scalar_keys = ["anio", "moran_i", "expected_i", "z_score", "p_value", "permutations",
                           "weights_method", "calculation_version"]
            extras = {k: v for k, v in year.items() if k not in {*scalar_keys, "items"}}
            connection.execute(text("""
                INSERT INTO ipr_spatial_global
                    (anio,moran_i,expected_i,z_score,p_value,permutations,weights_method,
                     calculation_version,calculated_at,result,metadata,audit)
                VALUES (:anio,:moran_i,:expected_i,:z_score,:p_value,:permutations,:weights_method,
                     :calculation_version,:calculated_at,CAST(:result AS jsonb),
                     CAST(:metadata AS jsonb),CAST(:audit AS jsonb))
            """), {**{key: year[key] for key in scalar_keys},
                    "calculated_at": metadata["calculated_at"], "result": json.dumps(extras),
                    "metadata": json.dumps(metadata), "audit": json.dumps(payload["audit"])})
            rows = [{**item, "calculation_version": year["calculation_version"],
                     "calculated_at": metadata["calculated_at"]} for item in year["items"]]
            # Keys are an internal schema contract, never supplied by an HTTP request.
            columns = ",".join(rows[0])
            parameters = ",".join(":" + key for key in rows[0])
            connection.execute(text(f"INSERT INTO ipr_spatial_local ({columns}) VALUES ({parameters})"), rows)
    print(f"  spatial: {len(payload['years'])} años, {sum(len(y['items']) for y in payload['years'])} resultados locales")
