#!/usr/bin/env python3
"""Auditoría, Moran/LISA y artefactos del IPR observado. No requiere base de datos."""
import argparse
from pathlib import Path

from spatial_ipr.analysis import run
from spatial_ipr.reporting import create_report

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geometry", type=Path, default=ROOT / "data/raw/municipios_306_con_geometria.gpkg")
    parser.add_argument("--ipr", type=Path, default=ROOT / "data/processed/indice_presion_residencial_2023.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/spatial")
    parser.add_argument("--report", type=Path, default=ROOT / "output/analisis_espacial")
    parser.add_argument("--permutations", type=int, default=999)
    parser.add_argument("--seed", type=int, default=2023)
    args = parser.parse_args()
    payload = run(args.geometry, args.ipr, args.output, args.permutations, args.seed)
    create_report(payload, args.geometry, args.report)
    for result in payload["years"]:
        print(f'{result["anio"]}: I={result["moran_i"]:.6f}; p={result["p_value"]:.4f}; '
              f'n={result["n_observations"]}/{result["n_municipalities"]}; {result["interpretation"]}')


if __name__ == "__main__":
    main()
