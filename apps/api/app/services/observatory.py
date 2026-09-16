from math import isclose

from fastapi import HTTPException

ALL_LAYERS = (
    "asequibilidad",
    "turismo",
    "especulacion",
    "gentrificacion",
    "riesgo_futuro",
)
OBSERVED_LAYERS = ALL_LAYERS[:-1]


class ObservatoryService:
    def __init__(self, repo):
        self.repo = repo

    def prospective_contrast(
        self,
        ccaa: str | None = None,
        provincia: str | None = None,
        search: str | None = None,
        min_brecha: float | None = None,
        max_brecha: float | None = None,
    ) -> dict:
        if (
            min_brecha is not None
            and max_brecha is not None
            and min_brecha > max_brecha
        ):
            raise HTTPException(
                422, "min_brecha no puede superar max_brecha"
            )

        search = search.strip() if search and search.strip() else None
        items = self.repo.prospective_contrast(
            ccaa,
            provincia,
            search,
            min_brecha,
            max_brecha,
        )
        gaps = [item["brecha"] for item in items if item["brecha"] is not None]
        ipr5_mayor = sum(
            gap > 0 and not isclose(gap, 0, abs_tol=1e-9)
            for gap in gaps
        )
        ipr5_menor = sum(
            gap < 0 and not isclose(gap, 0, abs_tol=1e-9)
            for gap in gaps
        )
        igual = sum(isclose(gap, 0, abs_tol=1e-9) for gap in gaps)
        return {
            "items": items,
            "resumen": {
                "total": len(items),
                "comparables": len(gaps),
                "ipr5_mayor": ipr5_mayor,
                "ipr5_menor": ipr5_menor,
                "igual": igual,
                "sin_contraste": len(items) - len(gaps),
                "brecha_media": sum(gaps) / len(gaps) if gaps else None,
                "brecha_min": min(gaps) if gaps else None,
                "brecha_max": max(gaps) if gaps else None,
            },
        }

    def detail(self, cod_ine: str, product: str = "observado") -> dict:
        row = self.repo.detail(cod_ine)
        if not row:
            raise HTTPException(404, "Municipio no encontrado")

        prospective = product == "prospectivo"
        layers = ALL_LAYERS if prospective else OBSERVED_LAYERS
        if prospective:
            weights = {layer: row[f"peso_{layer}"] for layer in layers}
        else:
            observed_total = sum(row[f"peso_{layer}"] for layer in layers)
            weights = {
                layer: row[f"peso_{layer}"] / observed_total for layer in layers
            }

        detail = {
            "data_quality": row.get("data_quality"),
            "cod_ine": row["cod_ine"],
            "nombre": row["nombre"],
            "provincia": row["provincia"],
            "comunidad_autonoma": row["comunidad_autonoma"],
            "anio": row["anio"],
            "score": (
                row["score_prospectivo"]
                if prospective
                else row["score_observado"]
            ),
            "percentil": (
                row["percentil_prospectivo"]
                if prospective
                else row["percentil_observado"]
            ),
            "categoria": (
                row["categoria_prospectiva"]
                if prospective
                else row["categoria_observada"]
            ),
            "ranking": (
                row["ranking_prospectivo"]
                if prospective
                else row["ranking_observado"]
            ),
            "producto": product,
            "capas_validas": (
                row["capas_validas"]
                if prospective
                else sum(row[layer] is not None for layer in layers)
            ),
            "metodo": row["metodo"],
            "version_metodologia": row["version_metodologia"],
            "capas": [],
        }
        for layer in layers:
            score = row[layer]
            weight = weights[layer]
            detail["capas"].append(
                {
                    "nombre": layer,
                    "score": score,
                    "peso": weight,
                    "contribucion": score * weight if score is not None else None,
                    "tipo": (
                        "proyectado"
                        if layer == "riesgo_futuro"
                        else "estimado"
                        if layer == "gentrificacion"
                        else "observado"
                    ),
                }
            )
        return detail

    def spatial_year(self, year: int | None) -> dict:
        years = self.repo.spatial_history()["years"]
        if not years:
            raise HTTPException(503, "No hay análisis espacial precalculado")
        selected = next((row for row in years if row["anio"] == (year if year is not None else years[0]["anio"])), None)
        if selected is None:
            raise HTTPException(422, f"El análisis espacial no está disponible para {year}")
        return selected

    def spatial(self, year: int | None) -> dict:
        result = self.spatial_year(year)
        return {"global_result": result, "items": self.repo.spatial_local(result["anio"])}

    def spatial_municipality(self, code: str, year: int | None) -> dict:
        result = self.spatial_year(year)
        rows = self.repo.spatial_local(result["anio"], code)
        if not rows:
            raise HTTPException(404, "Municipio sin resultado espacial para este año")
        return {**rows[0], "neighbors": self.repo.spatial_neighbors(result["anio"], code)}
