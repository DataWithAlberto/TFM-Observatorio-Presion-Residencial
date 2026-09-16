"""Pruebas de regresión para las correcciones metodológicas de riesgo futuro."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def cargar_modulo(nombre: str, archivo: str):
    spec = importlib.util.spec_from_file_location(nombre, ROOT / archivo)
    modulo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modulo)
    return modulo


indicadores = cargar_modulo("indicadores_riesgo_futuro", "16_indicadores_riesgo_futuro.py")
indice = cargar_modulo("indice_riesgo_futuro", "17_indice_riesgo_futuro.py")


class TendenciasTest(unittest.TestCase):
    def test_asequibilidad_se_invierte_antes_de_la_pendiente(self):
        df = pd.DataFrame(
            {
                "anio": [2021, 2022, 2023],
                "puntuacion_asequibilidad": [20.0, 30.0, 40.0],
            }
        )
        preparada, score = indicadores.preparar_serie_tendencia(
            df, "asequibilidad", "anio", "puntuacion_asequibilidad"
        )
        pendiente, *_ = indicadores.pendiente_robusta(preparada, score)
        self.assertAlmostEqual(pendiente, -10.0)

    def test_turismo_ignora_otros_meses_y_datos_posteriores(self):
        df = pd.DataFrame(
            {
                "fecha": pd.to_datetime(
                    [
                        "2020-08-01",
                        "2021-02-01",
                        "2021-08-01",
                        "2022-08-01",
                        "2023-08-01",
                        "2024-08-01",
                        "2026-08-01",
                    ]
                ),
                "score": [10, 99, 20, 30, 40, 1000, -1000],
            }
        )
        preparada, score = indicadores.preparar_serie_tendencia(
            df, "turismo", "fecha", "score"
        )
        self.assertEqual(preparada["anio"].tolist(), [2020, 2021, 2022, 2023])
        pendiente, n, inicio, fin = indicadores.pendiente_robusta(preparada, score)
        self.assertAlmostEqual(pendiente, 10.0)
        self.assertEqual((n, inicio, fin), (4, 2020, 2023))


class PercentilesTest(unittest.TestCase):
    def test_serie_completamente_nula_permanece_nula(self):
        resultado = indice.percentil(pd.Series([np.nan, np.nan]))
        self.assertTrue(resultado.isna().all())

    def test_constante_parcial_preserva_ausencia(self):
        resultado = indice.percentil(pd.Series([5.0, np.nan]))
        self.assertEqual(resultado.iloc[0], 50.0)
        self.assertTrue(np.isnan(resultado.iloc[1]))

    def test_dos_valores_y_una_ausencia(self):
        resultado = indice.percentil(pd.Series([1.0, 2.0, np.nan]))
        self.assertEqual(resultado.iloc[0], 0.0)
        self.assertEqual(resultado.iloc[1], 100.0)
        self.assertTrue(np.isnan(resultado.iloc[2]))


if __name__ == "__main__":
    unittest.main()
