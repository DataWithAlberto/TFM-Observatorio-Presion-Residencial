import csv
import io
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse

from app.dependencies import get_service
from app.schemas import (
    SpatialHistory,
    SpatialYear,
    SpatialMunicipality,
    Benchmark,
    Catalogue,
    Comparison,
    HistoricalPoint,
    HomogeneousHistory,
    LayerValue,
    MapValue,
    Municipality,
    MunicipalityDetail,
    PaginatedIndex,
    ProspectiveContrast,
    QualityRow,
    QualitySummary,
)
from app.services.observatory import ObservatoryService

router = APIRouter()
Product = Literal["observado", "prospectivo"]
Layer = Literal[
    "ipr",
    "calidad",
    "asequibilidad",
    "turismo",
    "especulacion",
    "gentrificacion",
    "riesgo_futuro",
]


@router.get("/catalogo", response_model=Catalogue)
def catalogo(service: ObservatoryService = Depends(get_service)):
    return service.repo.catalogue()


@router.get("/municipios", response_model=list[Municipality])
def municipios(service: ObservatoryService = Depends(get_service)):
    return service.repo.municipalities()


@router.get("/municipios/{cod_ine}", response_model=MunicipalityDetail)
def municipio(
    cod_ine: str,
    producto: Product = "observado",
    service: ObservatoryService = Depends(get_service),
):
    return service.detail(cod_ine, producto)


@router.get(
    "/municipios/{cod_ine}/historico", response_model=list[HistoricalPoint] | HomogeneousHistory
)
def historico(cod_ine: str, serie: Literal["disponible", "homogenea"] = "disponible",
              service: ObservatoryService = Depends(get_service)):
    service.detail(cod_ine)
    if serie == "homogenea":
        return service.repo.homogeneous_history(cod_ine)
    return service.repo.history(cod_ine)


@router.get("/municipios/{cod_ine}/capas", response_model=list[LayerValue])
def capas(
    cod_ine: str,
    producto: Product = "observado",
    service: ObservatoryService = Depends(get_service),
):
    return service.detail(cod_ine, producto)["capas"]


@router.get(
    "/municipios/{cod_ine}/comparativas", response_model=list[Benchmark]
)
def comparativas(
    cod_ine: str,
    producto: Product = "observado",
    service: ObservatoryService = Depends(get_service),
):
    service.detail(cod_ine, producto)
    return service.repo.benchmarks(cod_ine, producto)


def query_index(
    service: ObservatoryService,
    anio: int | None,
    producto: Product,
    capa: Layer,
    ccaa: str | None,
    provincia: str | None,
    min_score: float = 0,
    max_score: float = 100,
    search: str | None = None,
):
    years = service.repo.catalogue()["years"]
    if not years:
        raise HTTPException(503, "No hay resultados del índice disponibles")
    year = anio or years[0]
    if year not in years:
        raise HTTPException(422, f"El IPR no está disponible para {year}")
    if min_score > max_score:
        raise HTTPException(422, "min_score no puede superar max_score")
    return (
        service.repo.index_rows(
            year,
            producto,
            capa,
            ccaa,
            provincia,
            min_score,
            max_score,
            search,
        ),
        years,
    )


@router.get("/indice", response_model=PaginatedIndex)
def indice(
    anio: int | None = None,
    producto: Product = "observado",
    capa: Layer = "ipr",
    ccaa: str | None = None,
    provincia: str | None = None,
    search: str | None = Query(None, max_length=80),
    min_score: float = Query(0, ge=0, le=100),
    max_score: float = Query(100, ge=0, le=100),
    service: ObservatoryService = Depends(get_service),
):
    items, years = query_index(
        service,
        anio,
        producto,
        capa,
        ccaa,
        provincia,
        min_score,
        max_score,
        search,
    )
    return {"items": items, "total": len(items), "year_options": years}


@router.get("/ranking")
def ranking(
    anio: int | None = None,
    producto: Literal["observado", "prospectivo", "historico"] = "observado",
    capa: Layer = "ipr",
    ccaa: str | None = None,
    provincia: str | None = None,
    search: str | None = Query(None, max_length=80),
    min_score: float = Query(0, ge=0, le=100),
    max_score: float = Query(100, ge=0, le=100),
    formato: Literal["json", "csv"] = "json",
    orden: Literal["ranking", "incremento", "descenso", "subida_ranking", "bajada_ranking"] = "ranking",
    service: ObservatoryService = Depends(get_service),
):
    if producto == "historico":
        years = service.repo.historical_metadata().get("years", [])
        year = anio if anio is not None else max(years, default=None)
        if year not in years:
            raise HTTPException(422, "Año sin IPR histórico homogéneo")
        if capa != "ipr" or min_score > max_score:
            raise HTTPException(422, "El ranking histórico requiere capa=ipr y un rango válido")
        items = service.repo.historical_ranking(year, ccaa, provincia, search, min_score, max_score)
        if orden != "ranking":
            field = "delta_ipr" if orden in ("incremento", "descenso") else "rank_change"
            positive = orden in ("incremento", "bajada_ranking")
            items = [r for r in items if r[field] is not None and (r[field] > 0 if positive else r[field] < 0)]
            items.sort(key=lambda r: ((-1 if positive else 1) * r[field], r["cod_ine"]))
    else:
        if orden != "ranking":
            raise HTTPException(422, "Los cambios temporales requieren producto=historico")
        items, _ = query_index(service, anio, producto, capa, ccaa, provincia, min_score, max_score, search)
    if formato == "json":
        return items
    output = io.StringIO()
    fields = [
        "ranking",
        "cod_ine",
        "nombre",
        "provincia",
        "comunidad_autonoma",
        "anio",
        "score",
        "percentil",
        "categoria",
        "producto",
    ]
    if producto == "historico":
        fields += ["delta_ipr", "delta_since_start", "rank_change", "calculation_version"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(items)
    return Response(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=ranking_ipr.csv"
        },
    )


@router.get("/comparacion", response_model=Comparison)
def comparacion(
    cod_ine: list[str] = Query(min_length=2, max_length=4),
    producto: Product = "observado",
    service: ObservatoryService = Depends(get_service),
):
    if len(set(cod_ine)) != len(cod_ine):
        raise HTTPException(422, "Los municipios comparados deben ser distintos")
    return {
        "items": [service.detail(code, producto) for code in cod_ine]
    }


@router.get("/prospectiva", response_model=ProspectiveContrast)
def prospectiva(
    ccaa: str | None = None,
    provincia: str | None = None,
    search: str | None = Query(None, max_length=80),
    min_brecha: float | None = Query(None, ge=-15, le=15),
    max_brecha: float | None = Query(None, ge=-15, le=15),
    formato: Literal["json", "csv"] = "json",
    service: ObservatoryService = Depends(get_service),
):
    contrast = service.prospective_contrast(
        ccaa,
        provincia,
        search,
        min_brecha,
        max_brecha,
    )
    if formato == "json":
        return contrast

    output = io.StringIO()
    fields = [
        "cod_ine",
        "nombre",
        "provincia",
        "comunidad_autonoma",
        "anio",
        "ipr4_observado",
        "ipr5_prospectivo",
        "riesgo_futuro",
        "brecha",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(contrast["items"])
    return Response(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                "attachment; filename=contraste_prospectivo_2023.csv"
            )
        },
    )


@router.get("/calidad", response_model=list[QualityRow])
def calidad(
    cod_ine: str | None = None,
    service: ObservatoryService = Depends(get_service),
):
    return service.repo.quality(cod_ine)


@router.get("/calidad/resumen", response_model=QualitySummary)
def calidad_resumen(service: ObservatoryService = Depends(get_service)):
    return service.repo.quality_summary()


@router.get("/mapa/valores", response_model=list[MapValue])
def valores(
    anio: int | None = None,
    capa: Layer = "ipr",
    producto: Product = "observado",
    ccaa: str | None = None,
    provincia: str | None = None,
    min_score: float = Query(0, ge=0, le=100),
    max_score: float = Query(100, ge=0, le=100),
    service: ObservatoryService = Depends(get_service),
):
    years = service.repo.catalogue()["years"]
    year = anio or years[0]
    if min_score > max_score:
        raise HTTPException(422, "min_score no puede superar max_score")
    rows = service.repo.map_values(
        year, capa, producto, ccaa, provincia, min_score, max_score
    )
    projected = capa == "riesgo_futuro" or (
        capa == "ipr" and producto == "prospectivo"
    )
    return [
        {
            **row,
            "tipo": "proyectado" if projected else "observado",
        }
        for row in rows
    ]


@router.get("/mapa/geometrias")
def geometrias(service: ObservatoryService = Depends(get_service)):
    return JSONResponse(
        service.repo.geometry(),
        headers={"Cache-Control": "public,max-age=86400"},
    )


@router.get("/espacial/historico", response_model=SpatialHistory)
def espacial_historico(service: ObservatoryService = Depends(get_service)):
    return service.repo.spatial_history()


@router.get("/espacial", response_model=SpatialYear)
def espacial(anio: int | None = None, service: ObservatoryService = Depends(get_service)):
    # One year response keeps the global statistic, scatterplot and map consistent.
    return service.spatial(anio)


@router.get("/municipios/{cod_ine}/espacial", response_model=SpatialMunicipality)
def municipio_espacial(
    cod_ine: str, anio: int | None = None,
    service: ObservatoryService = Depends(get_service),
):
    return service.spatial_municipality(cod_ine, anio)
