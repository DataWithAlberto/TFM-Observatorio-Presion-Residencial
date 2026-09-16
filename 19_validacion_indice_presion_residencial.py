#!/usr/bin/env python3
"""Valida cobertura, integridad, rangos, estabilidad y casos de referencia del IPR."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("data/processed")
RESULTADOS = OUT / "indice_presion_residencial_2023.csv"
VALIDACIONES = OUT / "ipr_validaciones.csv"
REFERENCIAS = OUT / "ipr_municipios_referencia.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Falla también ante avisos")
    args = parser.parse_args()
    df = pd.read_csv(RESULTADOS, dtype={"cod_ine": str})
    sensibilidad = pd.read_csv(OUT / "ipr_sensibilidad_pesos.csv")
    vif = pd.read_csv(OUT / "ipr_vif.csv")
    pruebas: list[dict[str, str]] = []

    def registrar(prueba: str, condicion: bool, detalle: str, aviso: bool = False) -> None:
        estado = "OK" if condicion else ("AVISO" if aviso else "ERROR")
        pruebas.append({"prueba": prueba, "estado": estado, "detalle": detalle})

    registrar("universo_306", len(df) == 306 and df["cod_ine"].nunique() == 306, f"{len(df)} filas")
    registrar("clave_unica", not df["cod_ine"].duplicated().any(), f"{df['cod_ine'].duplicated().sum()} duplicados")
    registrar(
        "ipr5_prospectivo_cobertura",
        int(df["elegible_ipr5_prospectivo"].sum()) == 303,
        f"{int(df['elegible_ipr5_prospectivo'].sum())}/306",
    )
    registrar("ipr4_cobertura_nacional", df["ipr4_nacional_observado"].notna().sum() == 306, f"{df['ipr4_nacional_observado'].notna().sum()}/306")
    registrar(
        "ipr5_prospectivo_rango",
        df.loc[
            df["elegible_ipr5_prospectivo"], "ipr5_prospectivo"
        ].between(0, 100).all(),
        "0–100",
    )
    registrar("ipr4_rango", df["ipr4_nacional_observado"].between(0, 100).all(), "0–100")
    contribuciones = [c for c in df if c.startswith("contribucion_")]
    diferencia = (
        df[contribuciones].sum(axis=1, min_count=5)
        - df["ipr5_prospectivo"]
    ).abs().max()
    registrar("trazabilidad_contribuciones", diferencia < 1e-9, f"diferencia máxima {diferencia:.3g}")
    pesos = df[[c for c in df if c.startswith("peso_")]].iloc[0].sum()
    registrar("pesos_suman_uno", np.isclose(pesos, 1), f"{pesos:.6f}")
    registrar("vif_sin_redundancia_severa", vif["vif"].max() < 5, f"máximo {vif['vif'].max():.3f}")
    registrar(
        "sensibilidad_correlacion",
        sensibilidad["spearman_score_base"].min() >= 0.90,
        f"Spearman mínimo {sensibilidad['spearman_score_base'].min():.3f}",
        aviso=True,
    )
    registrar(
        "sensibilidad_top10",
        sensibilidad["solapamiento_top_10_pct"].min() >= 0.70,
        f"solapamiento mínimo {sensibilidad['solapamiento_top_10_pct'].min():.3f}",
        aviso=True,
    )
    faltantes = set(df.loc[~df["elegible_ipr5_prospectivo"], "cod_ine"])
    registrar("faltantes_riesgo_documentados", faltantes == {"11012", "11031", "48044"}, ",".join(sorted(faltantes)))
    registrar(
        "sin_ceros_por_ausencia",
        df.loc[
            ~df["elegible_ipr5_prospectivo"], "ipr5_prospectivo"
        ].isna().all(),
        "Los tres IPR-5 no elegibles permanecen nulos",
    )

    codigos = {"08019", "28079", "29067", "07040", "20069", "33024", "46250"}
    referencias = df[df["cod_ine"].isin(codigos)].copy()
    referencias = referencias.sort_values("ranking_ipr4")
    referencias.to_csv(REFERENCIAS, index=False)
    registrar("municipios_referencia", referencias["cod_ine"].nunique() == len(codigos), f"{len(referencias)}/{len(codigos)}")

    validaciones = pd.DataFrame(pruebas)
    validaciones.to_csv(VALIDACIONES, index=False)
    errores = validaciones["estado"].eq("ERROR").sum()
    avisos = validaciones["estado"].eq("AVISO").sum()
    print(json.dumps({"pruebas": len(validaciones), "errores": int(errores), "avisos": int(avisos)}, indent=2))
    if errores or (args.strict and avisos):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
