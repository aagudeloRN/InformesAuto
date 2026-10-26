"""DT-057/T1 — `tipo_fuente` en EMIS individuales: estampado en ingesta + backfill idempotente.

Dos frentes, ambos fast (sin BD ni Ollama reales):
  1. `PdfIngestor.ingest_batched` estampa `tipo_fuente='informe_emis'` para `tipo=INFORME_EMIS`
     (PDFs nuevos entran etiquetados), y NO estampa para tipos que no aplican.
  2. `EmbeddingBackfillRepository.backfill_tipo_fuente_emis` etiqueta los chunks EMIS ya
     indexados con una Session falsa que modela la idempotencia (segunda corrida → 0 filas).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ic.data.repositories.embedding_backfill_repo import EmbeddingBackfillRepository
from ic.shared.constants import TipoDocumento, TipoFuente


def _make_fake_reader(pages_text):
    reader = MagicMock()
    reader.metadata = {"/Title": "T", "/Author": "EMIS"}
    pages = [MagicMock() for _ in pages_text]
    for p, t in zip(pages, pages_text):
        p.extract_text.return_value = t
    reader.pages = pages
    return reader


def _run_ingest(tipo, sector_gics="3020"):
    """Corre ingest_batched capturando el metadatos del EmbeddingVectorial insertado."""
    from ic.infrastructure.sources import pdf_ingestor as mod

    settings = MagicMock()
    settings.ollama_base_url = "http://127.0.0.1:11434"
    settings.llm_local_embed_model = "nomic-embed-text"
    settings.llm_local_analytic_model = "qwen3:8b"
    settings.pdf_batch_size_pages = 2
    settings.db_schema = "informes_ic"

    capturado = {}

    def _fake_embed_vectorial(**kwargs):
        capturado.update(kwargs)
        return MagicMock()

    reader = _make_fake_reader(["Contenido EMIS con datos de sector"])
    with (
        patch.object(mod, "_ensure_metadatos_column"),
        patch.object(mod, "PdfReader", return_value=reader),
        patch.object(mod, "SessionLocal") as mock_session,
        patch.object(mod, "_document_already_ingested", return_value=False),
        patch.object(mod, "Embedder") as mock_embedder_cls,
        patch.object(mod, "_chunk_exists", return_value=False),
        patch.object(mod, "_release_vram"),
        patch.object(mod, "EmbeddingRepository"),
        patch.object(mod, "DocumentoLocal"),
        patch.object(mod, "EmbeddingVectorial", side_effect=_fake_embed_vectorial),
    ):
        mock_embedder_cls.return_value.embed_many.return_value = [[0.1] * 768]
        db = MagicMock()
        mock_session.return_value.__enter__.return_value = db
        mock_session.return_value.__exit__.return_value = False

        mod.PdfIngestor(settings).ingest_batched(
            pdf_path="/fake/emis.pdf",
            sector_gics=sector_gics,
            tipo=tipo,
        )
    return capturado


def test_ingest_estampa_tipo_fuente_emis():
    cap = _run_ingest(TipoDocumento.INFORME_EMIS)
    assert cap["metadatos"]["sector_gics"] == "3020"
    assert cap["metadatos"]["tipo_fuente"] == TipoFuente.INFORME_EMIS.value


def test_ingest_no_emis_no_sectorial_sin_tipo_fuente():
    # Un tipo que no es PDF_SECTORIAL/global ni EMIS no debe llevar tipo_fuente.
    cap = _run_ingest(TipoDocumento.OTRO)
    assert "tipo_fuente" not in cap["metadatos"]


# --- Backfill idempotente (Session falsa que modela el estado) ---


class _FakeResult:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class _StatefulSession:
    """Session falsa: mantiene chunks EMIS (algunos con tipo_fuente NULL) y aplica el UPDATE."""

    def __init__(self, tipos_fuente: list) -> None:
        # cada elemento es el valor actual de tipo_fuente del chunk (None = sin etiquetar)
        self.rows = list(tipos_fuente)
        self.sqls: list[str] = []
        self.commits = 0

    def execute(self, sql, params=None):  # noqa: ANN001
        s = str(sql)
        self.sqls.append(s)
        if s.strip().upper().startswith("UPDATE"):
            tf = params["tf"]
            n = 0
            for i, val in enumerate(self.rows):
                if val is None:  # solo los NULL (idempotencia)
                    self.rows[i] = tf
                    n += 1
            return _FakeResult(n)
        return _FakeResult(0)

    def commit(self):
        self.commits += 1


def test_backfill_tipo_fuente_emis_idempotente():
    # 3 chunks EMIS sin etiquetar + 1 ya etiquetado en corridas previas.
    sess = _StatefulSession([None, None, None, TipoFuente.INFORME_EMIS.value])
    repo = EmbeddingBackfillRepository(sess)

    n1 = repo.backfill_tipo_fuente_emis()
    n2 = repo.backfill_tipo_fuente_emis()  # segunda corrida: nada pendiente

    assert n1 == 3
    assert n2 == 0  # idempotente
    assert all(v == TipoFuente.INFORME_EMIS.value for v in sess.rows)


def test_backfill_sql_tiene_guarda_de_idempotencia_y_scope_emis():
    sess = _StatefulSession([None])
    EmbeddingBackfillRepository(sess).backfill_tipo_fuente_emis()
    sql = sess.sqls[-1]
    # Guarda de idempotencia: solo toca chunks aún sin etiquetar.
    assert "(metadatos->>'tipo_fuente') IS NULL" in sql
    # Acotado a documentos EMIS (no toca web/académicas/compilados).
    assert "documentos_locales" in sql
    assert "tipo = :tipo_emis" in sql
