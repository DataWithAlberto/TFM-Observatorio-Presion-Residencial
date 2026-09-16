#!/usr/bin/env python3
"""Audita primero y calcula el IPR-4 histórico con universo fijo."""

import argparse
import json
import os
from pathlib import Path

from analytics.historical import ROOT, audit, calculate, persist, sha256, write_audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--no-db", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/ipr_historical")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL"))
    args = parser.parse_args()
    _, layers, coverage, panel_coverage, universe, metadata = audit()
    # Una auditoría aislada no invalida el manifiesto de resultados ya publicados.
    audit_output = args.output / "audit" if args.audit_only else args.output
    write_audit(coverage, panel_coverage, universe, metadata, audit_output)
    print(json.dumps({k: metadata[k] for k in ("status", "years", "municipality_count")}, indent=2))
    if args.audit_only:
        return
    if not args.no_db and not args.db_url:
        parser.error("Indicar DATABASE_URL/--db-url o --no-db")
    scores, components = calculate(layers, universe, metadata)
    scores.to_csv(args.output / "scores.csv", index=False)
    components.to_csv(args.output / "components.csv", index=False)
    metadata["output_sha256"] = {name: sha256(args.output / name) for name in (
        "scores.csv", "components.csv", "historical_municipality_universe.csv"
    )}
    (args.output / "manifest.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    if not args.no_db:
        persist(scores, components, universe, metadata, args.db_url)


if __name__ == "__main__":
    main()
