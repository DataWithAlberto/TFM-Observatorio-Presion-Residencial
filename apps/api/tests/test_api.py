import csv
import io

from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_health(): assert client.get("/health").json()["status"]=="ok"
def test_municipalities(): assert len(client.get("/api/v1/municipios").json())==306
def test_geometry():
    x=client.get("/api/v1/mapa/geometrias").json()
    assert x["type"]=="FeatureCollection" and len(x["features"])==306

def test_geometry_uses_lon_lat_and_covers_peninsula_and_canaries():
    features=client.get("/api/v1/mapa/geometrias").json()["features"]

    def coordinate_pairs(value):
        if (
            isinstance(value,list)
            and len(value)>=2
            and isinstance(value[0],(int,float))
            and isinstance(value[1],(int,float))
        ):
            yield value[0],value[1]
            return
        if isinstance(value,list):
            for item in value:
                yield from coordinate_pairs(item)

    coordinates=[
        pair
        for feature in features
        for pair in coordinate_pairs(feature["geometry"]["coordinates"])
    ]
    longitudes=[pair[0] for pair in coordinates]
    latitudes=[pair[1] for pair in coordinates]

    assert all(-19<=longitude<=5 for longitude in longitudes)
    assert all(27<=latitude<=45 for latitude in latitudes)
    assert min(longitudes)<-16
    assert min(latitudes)<29
    assert max(longitudes)>3
    assert max(latitudes)>43

def test_observed_detail_uses_four_renormalized_layers():
    response=client.get("/api/v1/municipios/28079?producto=observado")
    assert response.status_code==200
    body=response.json()
    assert len(body["capas"])==4
    assert round(sum(x["peso"] for x in body["capas"]),10)==1
    assert abs(sum(x["contribucion"] for x in body["capas"])-body["score"])<1e-8

def test_ready():
    assert client.get("/ready").json()["status"]=="ready"

def test_catalogo():
    body=client.get("/api/v1/catalogo").json()
    assert set(body)=={"years","regions","historical"}
    assert 2023 in body["years"]
    assert body["regions"] and {"comunidad_autonoma","provincias"}<=set(body["regions"][0])

def test_municipio_not_found_is_404():
    assert client.get("/api/v1/municipios/99999").status_code==404
    assert client.get("/api/v1/municipios/99999/historico").status_code==404
    assert client.get("/api/v1/municipios/99999/capas").status_code==404
    assert client.get("/api/v1/municipios/99999/comparativas").status_code==404

def test_historico_capas_comparativas_contracts():
    historico=client.get("/api/v1/municipios/28079/historico").json()
    assert historico and {"anio","serie","valor","bruto","tipo"}<=set(historico[0])
    # Toda la serie va en la misma escala, índices incluidos: la posición dentro
    # del año. La puntuación con la que se calculó viaja aparte.
    assert all(punto["valor"] is None or 0<=punto["valor"]<=100 for punto in historico)
    indices=[p for p in historico if p["serie"].startswith("ipr_")]
    assert indices and all(p["bruto"] is not None for p in indices)

    capas=client.get("/api/v1/municipios/28079/capas?producto=prospectivo").json()
    assert len(capas)==5
    assert {c["nombre"] for c in capas}=={
        "asequibilidad","turismo","especulacion","gentrificacion","riesgo_futuro",
    }

    comparativas=client.get("/api/v1/municipios/28079/comparativas").json()
    assert {c["nivel"] for c in comparativas}=={"provincia","ccaa","espana"}

def test_capas_validas_is_consistent_between_indice_and_detail():
    # Cádiz (11012) no tiene score prospectivo, así que no aparece en el
    # ranking prospectivo por diseño: solo se contrasta ahí donde ambos
    # endpoints listan al municipio.
    for cod, producto, esperado in (
        ("28079","observado",4),
        ("28079","prospectivo",5),
        ("11012","observado",4),
    ):
        detalle=client.get(
            f"/api/v1/municipios/{cod}?producto={producto}"
        ).json()["capas_validas"]
        items=client.get(f"/api/v1/indice?producto={producto}").json()["items"]
        fila=next(item for item in items if item["cod_ine"]==cod)
        assert detalle==esperado, (cod,producto,"detalle",detalle)
        assert fila["capas_validas"]==esperado, (cod,producto,"indice",fila["capas_validas"])

    assert client.get(
        "/api/v1/municipios/11012?producto=prospectivo"
    ).json()["capas_validas"]==4

def test_ranking_json_and_csv():
    body=client.get("/api/v1/ranking?capa=turismo&min_score=90").json()
    assert body and all(row["score"]>=90 for row in body)

    csv_response=client.get("/api/v1/ranking?formato=csv")
    assert csv_response.status_code==200
    assert csv_response.headers["content-type"].startswith("text/csv")
    rows=list(csv.DictReader(io.StringIO(csv_response.text)))
    assert len(rows)==306

def test_calidad_list_and_filter():
    todos=client.get("/api/v1/calidad").json()
    assert len(todos)==306
    filtrado=client.get("/api/v1/calidad?cod_ine=28079").json()
    assert len(filtrado)==1 and filtrado[0]["cod_ine"]=="28079"

def test_comparacion_requires_distinct_and_between_2_and_4_codes():
    ok=client.get(
        "/api/v1/comparacion",
        params={"cod_ine":["28079","08019"]},
    )
    assert ok.status_code==200 and len(ok.json()["items"])==2

    duplicated=client.get(
        "/api/v1/comparacion",
        params={"cod_ine":["28079","28079"]},
    )
    assert duplicated.status_code==422

    too_few=client.get("/api/v1/comparacion", params={"cod_ine":["28079"]})
    assert too_few.status_code==422

def test_index_and_map_reject_inverted_score_range():
    assert client.get(
        "/api/v1/indice?min_score=90&max_score=10"
    ).status_code==422
    assert client.get(
        "/api/v1/mapa/valores?min_score=90&max_score=10"
    ).status_code==422

def test_prospective_map_and_quality_contracts():
    map_response=client.get("/api/v1/mapa/valores?capa=ipr&producto=prospectivo")
    assert map_response.status_code==200
    assert len(map_response.json())==303
    assert {row["tipo"] for row in map_response.json()}=={"proyectado"}
    quality=client.get("/api/v1/calidad/resumen").json()
    assert quality["municipios_observados"]==306
    assert quality["municipios_prospectivos"]==303

def test_layer_filter_is_ranked_and_invalid_year_is_rejected():
    response=client.get("/api/v1/indice?capa=turismo&min_score=90")
    assert response.status_code==200
    assert all(row["score"]>=90 for row in response.json()["items"])
    assert client.get("/api/v1/indice?anio=2005").status_code==422


def test_prospective_contrast_contract_and_arithmetic():
    response=client.get("/api/v1/prospectiva")
    assert response.status_code==200
    body=response.json()
    assert set(body)=={"items","resumen"}
    assert len(body["items"])==306

    expected_keys={
        "cod_ine","nombre","provincia","comunidad_autonoma","anio",
        "ipr4_observado","ipr5_prospectivo","riesgo_futuro","brecha",
    }
    assert all(set(item)==expected_keys for item in body["items"])

    comparable=[item for item in body["items"] if item["brecha"] is not None]
    missing=[item for item in body["items"] if item["brecha"] is None]
    assert len(comparable)==303
    assert {item["nombre"] for item in missing}=={
        "Cádiz","San Fernando","Getxo",
    }
    for item in comparable:
        assert abs(
            item["brecha"]
            -(item["ipr5_prospectivo"]-item["ipr4_observado"])
        )<1e-10
        assert abs(
            item["brecha"]
            -0.15*(item["riesgo_futuro"]-item["ipr4_observado"])
        )<1e-8

    summary=body["resumen"]
    assert summary["total"]==306
    assert summary["comparables"]==303
    assert summary["sin_contraste"]==3
    assert (
        summary["ipr5_mayor"]+summary["ipr5_menor"]+summary["igual"]
        ==summary["comparables"]
    )
    gaps=[item["brecha"] for item in comparable]
    assert abs(summary["brecha_media"]-sum(gaps)/len(gaps))<1e-10
    assert summary["brecha_min"]==min(gaps)
    assert summary["brecha_max"]==max(gaps)


def test_prospective_contrast_filters_preserve_missing_values():
    response=client.get("/api/v1/prospectiva?min_brecha=10")
    assert response.status_code==200
    body=response.json()
    assert body["resumen"]["sin_contraste"]==3
    assert all(
        item["brecha"] is None or item["brecha"]>=10
        for item in body["items"]
    )

    regional=client.get(
        "/api/v1/prospectiva",
        params={
            "ccaa":"Principado de Asturias",
            "provincia":"ASTURIAS",
        },
    ).json()
    assert regional["resumen"]["total"]==6
    assert all(
        item["comunidad_autonoma"]=="Principado de Asturias"
        and item["provincia"]=="ASTURIAS"
        for item in regional["items"]
    )

    getxo=client.get("/api/v1/prospectiva?search=Getxo").json()
    assert getxo["resumen"]=={
        "total":1,
        "comparables":0,
        "ipr5_mayor":0,
        "ipr5_menor":0,
        "igual":0,
        "sin_contraste":1,
        "brecha_media":None,
        "brecha_min":None,
        "brecha_max":None,
    }
    assert client.get(
        "/api/v1/prospectiva?min_brecha=5&max_brecha=-5"
    ).status_code==422


def test_prospective_contrast_csv_matches_json_contract():
    response=client.get("/api/v1/prospectiva?formato=csv")
    assert response.status_code==200
    assert response.headers["content-type"].startswith("text/csv")
    assert "contraste_prospectivo_2023.csv" in response.headers[
        "content-disposition"
    ]

    rows=list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows)==306
    assert list(rows[0])==[
        "cod_ine","nombre","provincia","comunidad_autonoma","anio",
        "ipr4_observado","ipr5_prospectivo","riesgo_futuro","brecha",
    ]
    missing=[row for row in rows if row["brecha"]==""]
    assert {row["nombre"] for row in missing}=={
        "Cádiz","San Fernando","Getxo",
    }


def test_dqs_detail_quality_and_map_share_persisted_values():
    body = client.get("/api/v1/municipios/28079").json()
    quality = body["data_quality"]
    assert quality["score"] == 99.0625
    assert quality["level"] == "alta"
    assert quality["coverage"] == 100 and quality["recency"] == 97.5
    assert quality["consistency"] is None
    assert quality["scope"] == "ipr4_observado"
    assert len(quality["components"]) == 4
    assert quality["components"][2]["source_year"] == 2021
    assert quality["calculation_version"] == "dqs-ipr4-1.0"
    assert quality["calculated_at"]
    assert any("2021" in issue for issue in quality["issues"])
    quality_rows = client.get("/api/v1/calidad?cod_ine=28079").json()
    assert quality_rows[0]["data_quality"] == quality
    rows = client.get("/api/v1/indice?search=Madrid").json()["items"]
    assert next(row for row in rows if row["cod_ine"] == "28079")["data_quality"] == quality
    layer = client.get("/api/v1/indice?capa=calidad").json()["items"]
    assert len(layer) == 306
    assert all(row["score"] == quality["score"] and row["percentil"] is None for row in layer)
    map_rows = client.get("/api/v1/mapa/valores?capa=calidad").json()
    assert len(map_rows) == 306
    assert all(row["valor"] == quality["score"] and row["categoria"] == "alta" for row in map_rows)
    summary = client.get("/api/v1/calidad/resumen").json()
    assert summary["dqs_media"] == quality["score"]
    assert summary["dqs_niveles"] == {"alta": 306}


def test_dqs_does_not_claim_to_measure_prospective_quality_or_change_ipr():
    observed = client.get("/api/v1/municipios/11012").json()
    projected = client.get("/api/v1/municipios/11012?producto=prospectivo").json()
    assert projected["score"] is None
    assert projected["data_quality"] == observed["data_quality"]
    assert projected["data_quality"]["scope"] == "ipr4_observado"
    assert abs(observed["score"] - sum(layer["contribucion"] for layer in observed["capas"])) < 1e-10
