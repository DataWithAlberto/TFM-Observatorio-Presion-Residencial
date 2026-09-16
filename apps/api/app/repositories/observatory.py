from __future__ import annotations

from typing import Any

from sqlalchemy import text

LAYERS = {
    "calidad": "dqs_score",
    "asequibilidad": "asequibilidad",
    "turismo": "turismo",
    "especulacion": "especulacion",
    "gentrificacion": "gentrificacion",
    "riesgo_futuro": "riesgo_futuro",
}


class ObservatoryRepository:
    def __init__(self, engine):
        self.engine = engine

    def rows(self, sql: str, params: dict[str, Any] | None = None) -> list[dict]:
        with self.engine.connect() as connection:
            result = connection.execute(text(sql), params or {}).mappings()
            return [dict(row) for row in result]

    def municipalities(self) -> list[dict]:
        return self.rows(
            """SELECT cod_ine,nombre,provincia,comunidad_autonoma
               FROM municipios ORDER BY nombre"""
        )

    def catalogue(self) -> dict:
        years = [
            row["anio"]
            for row in self.rows(
                "SELECT DISTINCT anio FROM api_ipr_municipal ORDER BY anio DESC"
            )
        ]
        regions = self.rows(
            """SELECT comunidad_autonoma,
                      ARRAY_AGG(DISTINCT provincia ORDER BY provincia) provincias
               FROM municipios
               GROUP BY comunidad_autonoma
               ORDER BY comunidad_autonoma"""
        )
        return {"years": years, "regions": regions, "historical": self.historical_metadata()}

    def historical_metadata(self) -> dict:
        rows = self.rows("""SELECT metadata,calculated_at FROM ipr_historical_runs
                            ORDER BY calculated_at DESC,calculation_version DESC LIMIT 1""")
        return {**rows[0]["metadata"], "calculated_at": rows[0]["calculated_at"]} if rows else {}

    def homogeneous_history(self, cod_ine: str) -> dict:
        metadata = self.historical_metadata()
        params = {"cod": cod_ine, "v": metadata.get("calculation_version")}
        universe = self.rows("""SELECT included,reason FROM historical_municipality_universe
                                WHERE cod_ine=:cod AND calculation_version=:v""", params)
        items = self.rows("""SELECT s.*,
                (SELECT json_agg(c ORDER BY c.component) FROM ipr_historical_components c
                 WHERE c.cod_ine=s.cod_ine AND c.anio=s.anio
                   AND c.calculation_version=s.calculation_version) components
                FROM ipr_historical_scores s
                WHERE cod_ine=:cod AND calculation_version=:v ORDER BY anio""", params)
        return {"metadata": metadata, "items": items,
                **(universe[0] if universe else {"included": False, "reason": "Sin histórico calculado"})}

    def historical_ranking(self, year, ccaa=None, provincia=None, search=None,
                           min_score=0, max_score=100) -> list[dict]:
        version = self.historical_metadata().get("calculation_version")
        return self.rows("""SELECT m.cod_ine,m.nombre,m.provincia,m.comunidad_autonoma,
                      s.anio,s.ipr_score score,s.ipr_percentile percentil,s.rank ranking,
                      s.delta_ipr,s.delta_since_start,s.rank_change,s.calculation_version,
                      'historico'::text producto,4 capas_validas,NULL categoria
               FROM ipr_historical_scores s JOIN municipios m USING (cod_ine)
               WHERE s.anio=:year AND s.calculation_version=:v
                 AND (:ccaa IS NULL OR m.comunidad_autonoma=:ccaa)
                 AND (:provincia IS NULL OR m.provincia=:provincia)
                 AND (:search IS NULL OR lower(m.nombre) LIKE lower(:pattern))
                 AND s.ipr_score BETWEEN :min_score AND :max_score
               ORDER BY s.rank,m.cod_ine""",
            {"year": year, "v": version, "ccaa": ccaa, "provincia": provincia,
             "search": search, "pattern": f"%{search}%" if search else None,
             "min_score": min_score, "max_score": max_score})

    @staticmethod
    def product_columns(product: str) -> tuple[str, str, str, str]:
        if product == "prospectivo":
            return (
                "score_prospectivo",
                "percentil_prospectivo",
                "categoria_prospectiva",
                "ranking_prospectivo",
            )
        return (
            "score_observado",
            "percentil_observado",
            "categoria_observada",
            "ranking_observado",
        )

    def index_rows(
        self,
        anio: int,
        product: str,
        layer: str,
        ccaa: str | None,
        provincia: str | None,
        min_score: float,
        max_score: float,
        search: str | None = None,
    ) -> list[dict]:
        if layer == "ipr":
            score, percentile, category, ranking = self.product_columns(product)
        elif layer == "calidad":
            score, percentile, category = "dqs_score", "NULL", "quality_level"
            ranking = "RANK() OVER (PARTITION BY anio ORDER BY dqs_score DESC NULLS LAST)"
        else:
            score = LAYERS[layer]
            percentile = LAYERS[layer]
            category = f"""CASE
                WHEN {score} < 20 THEN 'muy_baja'
                WHEN {score} < 40 THEN 'baja'
                WHEN {score} < 60 THEN 'media'
                WHEN {score} < 80 THEN 'alta'
                ELSE 'muy_alta' END"""
            ranking = f"RANK() OVER (PARTITION BY anio ORDER BY {score} DESC)"
        return self.rows(
            f"""WITH scored AS (
                  SELECT cod_ine,nombre,provincia,comunidad_autonoma,anio,
                         {score} score,{percentile} percentil,
                         {category} categoria,{ranking} ranking,
                         CASE WHEN :product='prospectivo' THEN capas_validas
                              ELSE num_nonnulls(
                                asequibilidad,turismo,especulacion,gentrificacion
                              )
                         END capas_validas,data_quality
                  FROM api_ipr_municipal
                )
                SELECT *, :product producto FROM scored
                WHERE anio=:anio
                  AND (:ccaa IS NULL OR comunidad_autonoma=:ccaa)
                  AND (:provincia IS NULL OR provincia=:provincia)
                  AND (:search IS NULL OR lower(nombre) LIKE lower(:search_pattern))
                  AND score BETWEEN :min_score AND :max_score
                ORDER BY ranking NULLS LAST""",
            {
                "anio": anio,
                "product": product,
                "ccaa": ccaa,
                "provincia": provincia,
                "search": search,
                "search_pattern": f"%{search}%" if search else None,
                "min_score": min_score,
                "max_score": max_score,
            },
        )

    def detail(self, cod_ine: str) -> dict | None:
        rows = self.rows(
            """SELECT * FROM api_ipr_municipal
               WHERE cod_ine=:cod ORDER BY anio DESC LIMIT 1""",
            {"cod": cod_ine},
        )
        return rows[0] if rows else None

    def prospective_contrast(
        self,
        ccaa: str | None,
        provincia: str | None,
        search: str | None,
        min_brecha: float | None,
        max_brecha: float | None,
    ) -> list[dict]:
        return self.rows(
            """SELECT cod_ine,nombre,provincia,comunidad_autonoma,anio,
                      ipr4_observado,ipr5_prospectivo,riesgo_futuro,brecha
               FROM api_contraste_prospectivo
               WHERE (:ccaa IS NULL OR comunidad_autonoma=:ccaa)
                 AND (:provincia IS NULL OR provincia=:provincia)
                 AND (
                   :search IS NULL
                   OR lower(nombre) LIKE lower(:search_pattern)
                 )
                 AND (
                   brecha IS NULL
                   OR :min_brecha IS NULL
                   OR brecha>=:min_brecha
                 )
                 AND (
                   brecha IS NULL
                   OR :max_brecha IS NULL
                   OR brecha<=:max_brecha
                 )
               ORDER BY brecha DESC NULLS LAST,nombre""",
            {
                "ccaa": ccaa,
                "provincia": provincia,
                "search": search,
                "search_pattern": f"%{search}%" if search else None,
                "min_brecha": min_brecha,
                "max_brecha": max_brecha,
            },
        )

    def quality(self, cod_ine: str | None = None) -> list[dict]:
        return self.rows(
            """SELECT * FROM api_calidad_municipal
               WHERE (:cod IS NULL OR cod_ine=:cod)
               ORDER BY cod_ine,anio""",
            {"cod": cod_ine},
        )

    def quality_summary(self) -> dict:
        row = self.rows(
            """SELECT COUNT(*) municipios,
                      COALESCE(ROUND(AVG(cobertura_observada_pct),1),0)::float
                        cobertura_observada_media,
                      COALESCE(ROUND(AVG(cobertura_prospectiva_pct),1),0)::float
                        cobertura_prospectiva_media,
                      COALESCE(SUM(nulos_prospectivos),0)::int nulos_prospectivos,
                      COUNT(*) FILTER (WHERE elegible_observado)::int
                        municipios_observados,
                      COUNT(*) FILTER (WHERE elegible_prospectivo)::int
                        municipios_prospectivos
               FROM api_calidad_municipal"""
        )[0]
        row["dqs_media"] = self.rows(
            "SELECT AVG(dqs_score)::float media FROM api_ipr_municipal"
        )[0]["media"]
        row["dqs_niveles"] = {
            item["nivel"]: item["n"] for item in self.rows(
                "SELECT COALESCE(quality_level,'sin_dato') nivel,COUNT(*) n "
                "FROM api_ipr_municipal GROUP BY quality_level"
            )
        }
        row["sources"] = [
            {"name": "Ministerio de Vivienda / INE Atlas de Renta", "layer": "asequibilidad"},
            {"name": "INE, viviendas de uso turístico y población municipal", "layer": "turismo"},
            {"name": "MIVAU / INE Censo y Atlas de Renta", "layer": "especulacion"},
            {"name": "INE Atlas / padrón / migraciones", "layer": "gentrificacion"},
            {"name": "Copernicus Climate Data Store", "layer": "riesgo_futuro"},
        ]
        return row

    def geometry(self) -> dict:
        rows = self.rows(
            """SELECT cod_ine,nombre,provincia,comunidad_autonoma,
                      ST_AsGeoJSON(
                        ST_SimplifyPreserveTopology(geometry,0.001),6
                      )::json geometry
               FROM municipios ORDER BY cod_ine"""
        )
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": row["cod_ine"],
                    "properties": {
                        "cod_ine": row["cod_ine"],
                        "nombre": row["nombre"],
                        "provincia": row["provincia"],
                        "comunidad_autonoma": row["comunidad_autonoma"],
                    },
                    "geometry": row["geometry"],
                }
                for row in rows
            ],
        }

    def map_values(
        self,
        anio: int,
        layer: str,
        product: str,
        ccaa: str | None,
        provincia: str | None,
        min_score: float,
        max_score: float,
    ) -> list[dict]:
        if layer == "ipr":
            score, _, category, _ = self.product_columns(product)
            value = score
        else:
            value = LAYERS[layer]
            category = "quality_level" if layer == "calidad" else "NULL"
        return self.rows(
            f"""SELECT cod_ine,{value}::float valor,{category} categoria
                FROM api_ipr_municipal
                WHERE anio=:anio
                  AND (:ccaa IS NULL OR comunidad_autonoma=:ccaa)
                  AND (:provincia IS NULL OR provincia=:provincia)
                  AND {value} BETWEEN :min_score AND :max_score
                ORDER BY cod_ine""",
            {
                "anio": anio,
                "ccaa": ccaa,
                "provincia": provincia,
                "min_score": min_score,
                "max_score": max_score,
            },
        )

    def history(self, cod_ine: str) -> list[dict]:
        return self.rows(
            """WITH turismo_anual AS (
               SELECT DISTINCT ON (cod_ine,EXTRACT(YEAR FROM fecha))
                        cod_ine,EXTRACT(YEAR FROM fecha)::int anio,
                        score_presion_turistica::float bruto,
                        'observado'::text tipo
                 FROM presion_turistica_score
                 ORDER BY cod_ine,EXTRACT(YEAR FROM fecha),fecha DESC
               ), raw AS (
                 SELECT cod_ine,anio,'asequibilidad'::text serie,
                        (100-puntuacion_asequibilidad)::float bruto,
                        'observado'::text tipo
                 FROM indicadores_asequibilidad
                 UNION ALL
                 SELECT cod_ine,anio,'turismo',bruto,tipo FROM turismo_anual
                 UNION ALL
                 SELECT cod_ine,anio,'especulacion',
                        score_presion_especulativa::float,'observado'
                 FROM presion_especulativa_score
                 UNION ALL
                 SELECT cod_ine,anio,'gentrificacion',
                        score_riesgo_gentrificacion::float,'estimado'
                 FROM riesgo_gentrificacion_score
                 -- Los dos índices entran en el mismo cálculo que los factores:
                 -- la serie publica la posición del municipio dentro del año, de
                 -- modo que una puntuación sin convertir se leería en una escala
                 -- que no es la suya.
                 UNION ALL
                 SELECT cod_ine,anio,'ipr_observado',score_observado::float,'observado'
                 FROM api_ipr_municipal
                 UNION ALL
                 SELECT cod_ine,anio,'ipr_prospectivo',score_prospectivo::float,'proyectado'
                 FROM api_ipr_municipal WHERE score_prospectivo IS NOT NULL
               ), ranked AS (
                 SELECT *,
                   COUNT(*) OVER (PARTITION BY serie,anio) n,
                   RANK() OVER (PARTITION BY serie,anio ORDER BY bruto) rango,
                   COUNT(*) OVER (PARTITION BY serie,anio,bruto) empates
                 FROM raw WHERE bruto IS NOT NULL
               )
               SELECT anio,serie,
                 CASE WHEN n<2 THEN NULL ELSE
                   100.0*(rango-1+(empates-1)/2.0)/(n-1) END::float valor,
                 bruto,tipo
               FROM ranked WHERE cod_ine=:cod
               ORDER BY anio,serie""",
            {"cod": cod_ine},
        )

    def benchmarks(self, cod_ine: str, product: str) -> list[dict]:
        score, _, _, _ = self.product_columns(product)
        row = self.detail(cod_ine)
        if not row:
            return []
        params = {
            "anio": row["anio"],
            "provincia": row["provincia"],
            "ccaa": row["comunidad_autonoma"],
        }
        return self.rows(
            f"""SELECT 'provincia' nivel,:provincia territorio,
                       AVG({score})::float score,
                       AVG(asequibilidad)::float asequibilidad,
                       AVG(turismo)::float turismo,
                       AVG(especulacion)::float especulacion,
                       AVG(gentrificacion)::float gentrificacion,
                       AVG(riesgo_futuro)::float riesgo_futuro
                FROM api_ipr_municipal
                WHERE anio=:anio AND provincia=:provincia
                UNION ALL
                SELECT 'ccaa',:ccaa,AVG({score})::float,
                       AVG(asequibilidad)::float,AVG(turismo)::float,
                       AVG(especulacion)::float,AVG(gentrificacion)::float,
                       AVG(riesgo_futuro)::float
                FROM api_ipr_municipal
                WHERE anio=:anio AND comunidad_autonoma=:ccaa
                UNION ALL
                SELECT 'espana','España (306 municipios)',AVG({score})::float,
                       AVG(asequibilidad)::float,AVG(turismo)::float,
                       AVG(especulacion)::float,AVG(gentrificacion)::float,
                       AVG(riesgo_futuro)::float
                FROM api_ipr_municipal WHERE anio=:anio""",
            params,
        )

    def spatial_history(self) -> dict:
        rows = self.rows("SELECT * FROM ipr_spatial_global ORDER BY anio DESC")
        return {
            "years": [self.spatial_global_row(row) for row in rows],
            "history_comparable": bool(rows and rows[0]["metadata"]["history_comparable"]),
            "dqs_available": bool(rows and rows[0]["metadata"]["dqs_available"]),
        }

    @staticmethod
    def spatial_global_row(row: dict) -> dict:
        return {**{key: value for key, value in row.items() if key not in {"result", "audit", "metadata"}},
                **row["result"], "calculated_at": row["calculated_at"].isoformat()}

    def spatial_local(self, year: int, code: str | None = None) -> list[dict]:
        rows = self.rows(
            """SELECT l.*, m.nombre FROM ipr_spatial_local l JOIN municipios m USING(cod_ine)
               WHERE l.anio=:year AND (:code IS NULL OR l.cod_ine=:code) ORDER BY l.cod_ine""",
            {"year": year, "code": code},
        )
        for row in rows:
            row["calculated_at"] = row["calculated_at"].isoformat()
        return rows

    def spatial_neighbors(self, year: int, code: str) -> list[dict]:
        return self.rows(
            """SELECT n.cod_ine,m.nombre,n.ipr,1.0/l.neighbor_count AS weight
               FROM ipr_spatial_local l
               JOIN ipr_spatial_local n ON n.cod_ine=ANY(l.neighbors) AND n.anio=l.anio
               JOIN municipios m ON m.cod_ine=n.cod_ine
               WHERE l.anio=:year AND l.cod_ine=:code ORDER BY n.cod_ine""",
            {"year": year, "code": code},
        )
