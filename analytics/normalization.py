"""Transformaciones compartidas; la referencia temporal la decide el llamador."""

import numpy as np
import pandas as pd


def percentil(serie: pd.Series) -> pd.Series:
    """Rango medio, extremos 0–100, sin convertir ausencias en ceros."""
    n = serie.notna().sum()
    if n < 2:
        return pd.Series(np.nan, index=serie.index)
    return 100 * (serie.rank(method="average") - 1) / (n - 1)


def ajustar_hogares(grupo: pd.DataFrame) -> pd.Series:
    """Residuo OLS de hogares unipersonales frente a estructura de edades."""
    cols = ["cambio_pct_hogares_unipersonales_3a",
            "cambio_pct_mayor_65_3a", "cambio_pct_menor_18_3a"]
    validos = np.isfinite(grupo[cols]).all(axis=1)
    resultado = pd.Series(np.nan, index=grupo.index)
    if validos.sum() >= 10:
        y = grupo.loc[validos, cols[0]].to_numpy()
        x = np.column_stack([np.ones(validos.sum()), grupo.loc[validos, cols[1:]]])
        resultado.loc[validos] = y - x @ np.linalg.lstsq(x, y, rcond=None)[0]
    return resultado
