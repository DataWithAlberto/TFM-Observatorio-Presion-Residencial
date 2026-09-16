"""Pruebas de regresión para el cálculo del índice de presión residencial (18)."""

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


ipr = cargar_modulo("indice_presion_residencial", "18_indice_presion_residencial.py")


class PercentilTest(unittest.TestCase):
    def test_serie_completamente_nula_permanece_nula(self):
        resultado = ipr.percentil(pd.Series([np.nan, np.nan]))
        self.assertTrue(resultado.isna().all())

    def test_valor_unico_no_nulo_es_neutro(self):
        resultado = ipr.percentil(pd.Series([42.0]))
        self.assertTrue(resultado.isna().all())

    def test_dos_valores_ocupan_los_extremos(self):
        resultado = ipr.percentil(pd.Series([10.0, 20.0]))
        self.assertEqual(resultado.iloc[0], 0.0)
        self.assertEqual(resultado.iloc[1], 100.0)


class SumaPonderadaTest(unittest.TestCase):
    def test_pesos_que_no_suman_uno_lanzan_error(self):
        df = pd.DataFrame({f"score_normalizado_{c}": [50.0] for c in ipr.CAPAS})
        pesos = dict(ipr.PESOS_BASE)
        pesos["asequibilidad"] += 0.1
        with self.assertRaises(ValueError):
            ipr.suma_ponderada(df, pesos)

    def test_suma_ponderada_coincide_con_calculo_manual(self):
        valores = {"asequibilidad": 80, "turismo": 60, "especulacion": 40,
                   "gentrificacion": 20, "riesgo_futuro": 100}
        df = pd.DataFrame({f"score_normalizado_{c}": [v] for c, v in valores.items()})
        esperado = sum(valores[c] * ipr.PESOS_BASE[c] for c in ipr.CAPAS)
        resultado = ipr.suma_ponderada(df, ipr.PESOS_BASE)
        self.assertAlmostEqual(resultado.iloc[0], esperado)


class CategoriaRelativaTest(unittest.TestCase):
    def test_limites_de_bandas(self):
        percentiles = pd.Series([0, 20, 40, 60, 80, 100])
        categorias = ipr.categoria_relativa(percentiles).astype(str).tolist()
        self.assertEqual(
            categorias,
            ["muy_baja", "muy_baja", "baja", "media", "alta", "muy_alta"],
        )


class ConstruirResultadosTest(unittest.TestCase):
    def _matriz(self) -> pd.DataFrame:
        # Tres municipios: uno completo, y dos sin riesgo_futuro (como
        # Cádiz/San Fernando/Getxo en el corte real).
        filas = {
            "cod_ine": ["00001", "00002", "00003"],
            "nombre": ["Completo", "Sin riesgo A", "Sin riesgo B"],
        }
        capas_valores = {
            "asequibilidad": [10.0, 90.0, 50.0],
            "turismo": [20.0, 80.0, 50.0],
            "especulacion": [30.0, 70.0, 50.0],
            "gentrificacion": [40.0, 60.0, 50.0],
            "riesgo_futuro": [50.0, np.nan, np.nan],
        }
        df = pd.DataFrame(filas)
        for capa, valores in capas_valores.items():
            df[f"score_normalizado_{capa}"] = valores
        return df

    def test_municipios_incompletos_no_reciben_ipr5_cero(self):
        principal, _ = ipr.construir_resultados(self._matriz())
        incompletos = principal[~principal["elegible_ipr5_prospectivo"]]
        self.assertEqual(len(incompletos), 2)
        self.assertTrue(incompletos["ipr5_prospectivo"].isna().all())
        self.assertTrue((incompletos["capas_validas"] == 4).all())

    def test_municipio_completo_es_elegible_y_tiene_score(self):
        principal, _ = ipr.construir_resultados(self._matriz())
        fila = principal.loc[principal["cod_ine"] == "00001"].iloc[0]
        self.assertTrue(fila["elegible_ipr5_prospectivo"])
        self.assertEqual(fila["capas_validas"], 5)
        self.assertFalse(pd.isna(fila["ipr5_prospectivo"]))

    def test_ipr4_nacional_esta_disponible_incluso_sin_riesgo_futuro(self):
        principal, _ = ipr.construir_resultados(self._matriz())
        self.assertTrue(principal["ipr4_nacional_observado"].notna().all())

    def test_contribuciones_suman_el_score_prospectivo(self):
        principal, _ = ipr.construir_resultados(self._matriz())
        elegibles = principal[principal["elegible_ipr5_prospectivo"]]
        contribuciones = elegibles[[f"contribucion_{c}" for c in ipr.CAPAS]].sum(axis=1)
        diferencia = (contribuciones - elegibles["ipr5_prospectivo"]).abs().max()
        self.assertLess(diferencia, 1e-9)


if __name__ == "__main__":
    unittest.main()
