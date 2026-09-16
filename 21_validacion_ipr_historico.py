#!/usr/bin/env python3
"""Contrasta Madrid, Barcelona y Gijón con fuentes conservadas, sin modificarlas."""

import argparse
import importlib.util
import json
import re
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from analytics.historical import ROOT, audit, calculate

REFERENCES = {"28079": "MADRID", "08019": "BARCELONA", "33024": "GIJON"}


def module(filename):
    spec = importlib.util.spec_from_file_location(filename[:-3], ROOT / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def verify(output: Path):
    frames, layers, _, _, universe, metadata = audit()
    scores, components = calculate(layers, universe, metadata)
    first, last = min(metadata["years"]), max(metadata["years"])
    prices_module = module("02_precios_vivienda.py")
    xls = pd.ExcelFile(ROOT / "data/raw/ministerio_vivienda/valor_tasado_municipios_25000hab.xls")
    parts = []
    for sheet in xls.sheet_names:
        match = re.match(r"T\dA(\d{4})", sheet.strip())
        if match and first - 3 <= int(match.group(1)) <= last:
            part = prices_module.parsea_hoja(xls, sheet)
            parts.append(part[part.municipio_norm.isin(REFERENCES.values())])
    raw_prices = pd.concat(parts)
    raw_prices["cod_ine"] = raw_prices.municipio_norm.map({v: k for k, v in REFERENCES.items()})
    raw_prices["anio"] = raw_prices.fecha.dt.year
    # Reutiliza los parsers existentes, desviando sus salidas a un directorio temporal.
    with tempfile.TemporaryDirectory(prefix="ipr-reference-") as temporary:
        tourism = module("05_turismo_ingesta.py")
        tourism.OUT_VUT = Path(temporary) / "vut.csv"
        raw_vut = tourism.procesar_vut()
        speculation = module("08_fuentes_especulacion.py")
        speculation.TRANSACCIONES_OUT = Path(temporary) / "transacciones.csv"
        speculation.PARQUE_OUT = Path(temporary) / "parque.csv"
        raw_tx = speculation.procesar_transacciones()
        raw_stock = speculation.procesar_parque().set_index("cod_ine")
    demographics = pd.read_csv(ROOT / "data/raw/ine_gentrificacion/demografia_hogares_30832_selectivo.csv", dtype={"cod_ine": str}).set_index(["cod_ine", "anio"])
    annual_prices = raw_prices.groupby(["cod_ine", "anio"]).apply(
        lambda g: np.average(g.valor_total, weights=g.num_tasaciones), include_groups=False
    )
    price_source = frames["precios"].set_index(["cod_ine", "fecha"])
    for row in raw_prices.itertuples():
        processed = price_source.loc[(row.cod_ine, row.fecha)]
        np.testing.assert_allclose([row.valor_total, row.num_tasaciones], [processed.valor_total, processed.num_tasaciones])
    income = frames["renta"].set_index(["cod_ine", "anio"])
    socio = frames["socio"].set_index(["cod_ine", "anio"])
    records = []
    for code, name in REFERENCES.items():
        for year in metadata["years"]:
            a = frames["asequibilidad"].set_index(["cod_ine", "anio"]).loc[(code, year)]
            t = frames["turismo"].set_index(["cod_ine", "fecha"]).loc[(code, pd.Timestamp(year, 8, 1))]
            e = frames["especulacion"].set_index(["cod_ine", "anio"]).loc[(code, year)]
            g = frames["gentrificacion"].set_index(["cod_ine", "anio"]).loc[(code, year)]
            price = annual_prices.loc[(code, year)]
            rent = income.loc[(code, year), "renta_media"]
            ratio = price * 90 / rent
            np.testing.assert_allclose([price, rent, ratio], [a.precio_m2, a.renta_media, a.ratio_asequibilidad])
            assert rent == socio.loc[(code, year), "renta_neta_media_hogar"]
            vut = raw_vut[(raw_vut.cod_ine == code) & (raw_vut.fecha == pd.Timestamp(year, 8, 1))].viviendas_turisticas.item()
            assert vut == t.viviendas_turisticas
            np.testing.assert_allclose([1000 * vut / t.poblacion, vut / t.superficie_km2], [t.vut_por_1000_hab, t.vut_por_km2])
            tx = raw_tx[(raw_tx.cod_ine == code) & (raw_tx.anio == year)]
            assert tx.trimestre.nunique() == 4
            rotation = 100 * tx.compraventas.sum() / raw_stock.loc[code, "viviendas"]
            growth = price / annual_prices.loc[(code, year - 1)] - 1
            previous_growth = annual_prices.loc[(code, year - 1)] / annual_prices.loc[(code, year - 2)] - 1
            rent_growth = rent / income.loc[(code, year - 1), "renta_media"] - 1
            np.testing.assert_allclose([rotation, growth - previous_growth, growth - rent_growth],
                                       [e.tasa_rotacion, e.aceleracion_precio, e.desacoplamiento_precio_renta], atol=1e-12)
            income_growth = np.log(socio.loc[(code, year), "renta_neta_media_persona"] / socio.loc[(code, year - 3), "renta_neta_media_persona"])
            gap = np.log(price / annual_prices.loc[(code, year - 3)]) - income_growth
            np.testing.assert_allclose([income_growth, gap], [g.log_cambio_renta_neta_media_persona_3a, g.brecha_precio_renta_3a], atol=1e-12)
            for variable in ("pct_hogares_unipersonales", "pct_mayor_65", "pct_menor_18"):
                expected = demographics.loc[(code, year), variable] - demographics.loc[(code, year - 3), variable]
                np.testing.assert_allclose(expected, g[f"cambio_{variable}_3a"], atol=1e-12)
            result = scores.set_index(["cod_ine", "anio"]).loc[(code, year)]
            contribution = components[(components.cod_ine == code) & (components.anio == year)]
            records.append({"cod_ine": code, "municipio": name, "anio": year, "precio_m2": price,
                            "renta_hogar": rent, "ratio_acceso": ratio, "vut_agosto": vut,
                            "tasa_rotacion": rotation, "crecimiento_renta_persona_3a": income_growth,
                            "brecha_precio_renta_3a": gap, "ipr": result.ipr_score,
                            "delta_ipr": result.delta_ipr, "rank": result["rank"],
                            "contribuciones": json.dumps(dict(zip(contribution.component, contribution.contribution)), sort_keys=True),
                            "validacion": "OK", "limite_trazabilidad_renta": "CSV procesados Atlas; bruto 30824 no incluido en git"})
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(output, index=False)
    print(pd.DataFrame(records)[["municipio", "anio", "ipr", "delta_ipr", "rank", "validacion"]].to_string(index=False))
    return pd.DataFrame(records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/ipr_historical/reference_checks.csv")
    verify(parser.parse_args().output)
