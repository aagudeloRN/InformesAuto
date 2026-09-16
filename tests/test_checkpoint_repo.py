"""Tests fast del checkpoint --resume (T22.3, DT-030) — sin BD ni Ollama.

Cubren: round-trip de serialización, repositorio (upsert/load/clear) mockeado,
migración idempotente (IF NOT EXISTS) y el gancho de resume (persistir → leer → el
capítulo persistido se salta, el ausente se recomputa).
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from ic.domain.checkpoint_serde import (
    deserialize_cap,
    make_run_key,
    serialize_cap,
)
from ic.domain.use_cases import checkpoint_hooks
from ic.shared.types import CapBenchmarking, ChunkResult, DescripcionEmpresa


def _cap_benchmarking():
    ch = ChunkResult(
        chunk_texto="frag",
        fuente_tipo="web",
        fuente_url="http://x",
        score=0.91,
        metadatos={"sector": "3020"},
        chunk_id="c1",
    )
    return CapBenchmarking(
        texto="Cap 2 texto",
        n_chunks_usados=1,
        retrieval_suficiente=True,
        chunks_usados=[ch],
        radar_data={"dimensions": ["a"], "competidores": {"X": [1, 2, 3, 4, 5]}},
    )


class TestSerde:
    def test_roundtrip_cap_via_json(self):
        cap = _cap_benchmarking()
        payload = json.loads(json.dumps(serialize_cap(cap)))  # simula ida/vuelta JSONB
        back = deserialize_cap(payload)
        assert isinstance(back, CapBenchmarking)
        assert back.texto == cap.texto
        assert back.chunks_usados[0].chunk_id == "c1"
        assert back.chunks_usados[0].metadatos == {"sector": "3020"}
        assert back.radar_data["competidores"]["X"] == [1, 2, 3, 4, 5]

    def test_roundtrip_empresa_sin_chunks(self):
        emp = DescripcionEmpresa(nombre_empresa="Alpina", actividad_ciiu="1040", texto="desc")
        back = deserialize_cap(json.loads(json.dumps(serialize_cap(emp))))
        assert isinstance(back, DescripcionEmpresa)
        assert back.nombre_empresa == "Alpina"

    def test_make_run_key_determinista(self):
        # Mismo input → misma clave (permite reanudar); slug case-insensitive + espacios→_.
        assert make_run_key("Alpina S.A.S.", None) == make_run_key("  Alpina S.A.S.  ", None)
        assert make_run_key("Alpina S.A.S.", None) == "alpina_sas:auto"
        assert make_run_key("Sofasa S.A.", "2510") == "sofasa_sa:2510"
        assert make_run_key("X", None).endswith(":auto")


class TestCheckpointRepository:
    def test_save_capitulo_upsert_y_commit(self):
        from ic.data.repositories.checkpoint_repo import CheckpointRepository

        db = MagicMock()
        CheckpointRepository(db).save_capitulo("rk", "cap2", {"a": 1})
        db.execute.assert_called_once()
        db.commit.assert_called_once()
        # El statement es un INSERT ... ON CONFLICT (upsert idempotente).
        sql = str(db.execute.call_args[0][0]).upper()
        assert "INSERT" in sql and "CONFLICT" in sql

    def test_load_capitulos_devuelve_dict(self):
        from ic.data.repositories.checkpoint_repo import CheckpointRepository

        row = SimpleNamespace(cap_nombre="cap2", payload={"a": 1})
        db = MagicMock()
        db.execute.return_value.scalars.return_value.all.return_value = [row]
        result = CheckpointRepository(db).load_capitulos("rk")
        assert result == {"cap2": {"a": 1}}

    def test_clear_borra_y_commit(self):
        from ic.data.repositories.checkpoint_repo import CheckpointRepository

        db = MagicMock()
        CheckpointRepository(db).clear("rk")
        assert "DELETE" in str(db.execute.call_args[0][0]).upper()
        db.commit.assert_called_once()


class TestMigracionIdempotente:
    def test_ensure_checkpoint_table_usa_if_not_exists(self):
        from ic.data.models.checkpoint import ensure_checkpoint_table

        conn = MagicMock()
        engine = MagicMock()
        engine.begin.return_value.__enter__.return_value = conn
        ensure_checkpoint_table(engine)
        sql = str(conn.execute.call_args[0][0]).upper()
        assert "CREATE TABLE IF NOT EXISTS" in sql
        assert "CHECKPOINT_CAPITULOS" in sql
        assert "PRIMARY KEY" in sql


class TestResumeHook:
    def test_restore_salta_lo_persistido_y_recomputa_lo_ausente(self):
        # "persistir cap → leer → resume salta lo hecho": cap2 está en el checkpoint
        # (se restaura, la generación se salta), cap3 no (restore=None → se recomputa).
        cap = _cap_benchmarking()
        payload = json.loads(json.dumps(serialize_cap(cap)))
        ctx = SimpleNamespace(checkpoint={"cap2": payload})

        restaurado = checkpoint_hooks.restore(ctx, "cap2")
        assert isinstance(restaurado, CapBenchmarking)
        assert restaurado.texto == cap.texto

        assert checkpoint_hooks.restore(ctx, "cap3") is None

    def test_restore_payload_corrupto_devuelve_none(self):
        ctx = SimpleNamespace(checkpoint={"cap2": {"__type__": "NoExiste", "x": 1}})
        assert checkpoint_hooks.restore(ctx, "cap2") is None

    def test_save_ignora_objeto_none(self):
        # obj None no debe tocar la BD (retorno temprano, sin SessionLocal).
        ctx = SimpleNamespace(checkpoint={}, run_key="rk")
        checkpoint_hooks.save(ctx, "cap2", None)  # no lanza ni abre sesión
