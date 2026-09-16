"""Integración contra la misma base local que las pruebas de API; rollback final."""
import copy
import json
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import get_engine
from database.bootstrap.data_quality import persist

ROOT = Path(__file__).resolve().parents[3]


def test_dqs_upsert_preserves_years_and_ipr():
    row = json.loads((ROOT / "data/processed/dqs_municipal.json").read_text())[0]
    with get_engine().connect() as conn:
        transaction = conn.begin()
        try:
            initial = conn.scalar(text("SELECT COUNT(*) FROM data_quality_municipal"))
            ipr_before = conn.execute(text("SELECT * FROM indice_presion_residencial ORDER BY cod_ine,anio")).all()
            persist(conn, [row, row], ROOT / "sql/20_data_quality.sql")
            assert conn.scalar(text("SELECT COUNT(*) FROM data_quality_municipal")) == initial
            older = copy.deepcopy(row)
            older["anio"] = 2022
            persist(conn, [older], ROOT / "sql/20_data_quality.sql")
            assert conn.scalar(text("SELECT COUNT(*) FROM data_quality_municipal")) == initial + 1
            assert conn.execute(text("SELECT * FROM indice_presion_residencial ORDER BY cod_ine,anio")).all() == ipr_before
        finally:
            transaction.rollback()


@pytest.mark.parametrize("assignment", [
    "dqs_score=101", "coverage_score=-1", "recency_score=101", "consistency_score=101",
    "quality_level='baja'", "quality_level=NULL", "recency_score=NULL", "coverage_score=0",
    "anio=1800", "cod_ine='99999'",
])
def test_database_rejects_invalid_quality(assignment):
    with get_engine().connect() as conn:
        transaction = conn.begin()
        try:
            with pytest.raises(IntegrityError):
                # Assignment is a fixed test parameter, never user input.
                conn.execute(text(f"UPDATE data_quality_municipal SET {assignment} WHERE cod_ine='28079'"))
        finally:
            transaction.rollback()
