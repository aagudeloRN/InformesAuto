"""Tests Fase 13 — Repositorio Sectorial RAG (fast, mocked)."""

from unittest.mock import MagicMock, patch

from ic.infrastructure.citation.apa_formatter import CitationMetadata, format_reference
from ic.shared.constants import TipoDocumento
from ic.shared.constants.gics_groups import GICS_GROUPS, extract_gics_code, gics_options

# --- extract_gics_code ---


def test_extract_gics_code_basico():
    assert extract_gics_code("Grupo 8 — Servicios al consumidor (GICS 2530): ...") == "2530"


def test_extract_gics_code_solo_codigo():
    assert extract_gics_code("(GICS 4510)") == "4510"


def test_extract_gics_code_sin_match():
    assert extract_gics_code("Sector sin código") is None
    assert extract_gics_code(None) is None
    assert extract_gics_code("") is None


def test_extract_gics_code_no_confunde_tres_digitos():
    assert extract_gics_code("algo (GICS 253)") is None


def test_extract_gics_code_fallback_por_nombre():
    # El clasificador a veces devuelve solo el nombre del grupo, sin "(GICS XXXX)"
    assert extract_gics_code("Servicios al consumidor") == "2530"
    assert extract_gics_code("Grupo Industrial: Software y servicios") == "4510"
    assert extract_gics_code("Materiales") == "1510"


def test_extract_gics_code_prioriza_regex_sobre_nombre():
    # Si hay código explícito, gana sobre el nombre
    assert extract_gics_code("Bancos (GICS 4010)") == "4010"


# --- gics_options ---


def test_gics_options_cubre_los_25():
    opciones = gics_options()
    assert len(opciones) == len(GICS_GROUPS) == 25
    codigos = {c for c, _ in opciones}
    assert "2530" in codigos and "1510" in codigos and "4510" in codigos
    # nombre limpio, sin "(GICS" ni "Grupo N —"
    nombre_2530 = dict(opciones)["2530"]
    assert nombre_2530 == "Servicios al consumidor"


# --- APA informe compilado ---


def test_apa_report_informe_compilado():
    meta = CitationMetadata(
        titulo="Informe sectorial: Servicios al consumidor",
        fuente_nombre="Ruta N",
        año="2026",
        autor="Ruta N",
        url=None,
        fecha_acceso=None,
        tipo_fuente="informe_compilado",
    )
    ref = format_reference(meta, fuente_tipo="pdf")
    assert "Ruta N. (2026)." in ref.apa_string
    assert "Informe compilado de múltiples fuentes" in ref.apa_string


def test_apa_report_pdf_normal_sin_compilado():
    meta = CitationMetadata(
        titulo="Estudio X",
        fuente_nombre="Autoridad",
        año="2025",
        autor="Autoridad",
        url=None,
        fecha_acceso=None,
        tipo_fuente=None,
    )
    ref = format_reference(meta, fuente_tipo="pdf")
    assert "[Informe]." in ref.apa_string
    assert "compilado" not in ref.apa_string


# --- Migración idempotente ---


def test_ensure_documento_columns_emite_alters():
    from ic.data.models.documento_local import ensure_documento_columns

    conn = MagicMock()
    engine = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    engine.begin.return_value.__exit__.return_value = False

    with patch("ic.shared.config.get_settings") as mock_settings:
        mock_settings.return_value.db_schema = "informes_ic"
        ensure_documento_columns(engine)

    ejecutado = " ".join(str(c.args[0]) for c in conn.execute.call_args_list)
    assert "ADD COLUMN IF NOT EXISTS sector_gics" in ejecutado
    assert "ADD COLUMN IF NOT EXISTS activo" in ejecutado
    assert "ck_doc_tipo" in ejecutado
    assert "paper_academico" in ejecutado  # el CHECK incluye el valor nuevo


# --- PGVectorStore propaga filtros al repo ---


def test_search_propaga_filtros_sector_y_activos():
    from ic.infrastructure.retrieval.pgvector_store import PGVectorStore

    settings = MagicMock()
    settings.rag_top_k = 10
    settings.rag_similarity_threshold = 0.7
    settings.rag_max_chunks_per_doc = 4
    settings.rag_sector_reserve = 3
    settings.rag_sector_reserve_threshold = 0.5

    embedder = MagicMock()
    embedder.embed.return_value = [0.1] * 768
    repo = MagicMock()
    repo.search_similar.return_value = []

    store = PGVectorStore(embedder, repo, settings)
    store.search("consulta", sector_gics="2530", solo_activos=True)

    # Con match de sector se hacen 2 llamadas: general (con cap) + reserva sectorial estricta
    llamadas = repo.search_similar.call_args_list
    assert len(llamadas) == 2
    general = llamadas[0].kwargs
    assert general["sector_gics"] == "2530"
    assert general["solo_activos"] is True
    assert general["max_chunks_per_doc"] == 4
    reserva = llamadas[1].kwargs
    assert reserva["sector_estricto"] is True
    # la reserva usa el umbral relajado (0.5 < 0.7)
    assert llamadas[1].args[2] == 0.5


def test_search_reserva_garantiza_chunks_sectoriales():
    """La reserva antepone chunks sectoriales aunque puntúen menos que los web."""
    from ic.infrastructure.retrieval.pgvector_store import PGVectorStore

    settings = MagicMock()
    settings.rag_top_k = 3
    settings.rag_similarity_threshold = 0.7
    settings.rag_max_chunks_per_doc = 4
    settings.rag_sector_reserve = 2
    settings.rag_sector_reserve_threshold = 0.5

    def _chunk(cid, sector, tf):
        obj = MagicMock()
        obj.id = cid
        obj.chunk_texto = f"c{cid}"
        obj.fuente_tipo = "pdf" if sector else "web"
        obj.fuente_url = None
        obj.metadatos = {"sector_gics": sector, "tipo_fuente": tf} if sector else None
        return obj

    web = [
        (_chunk(1, None, None), 0.83),
        (_chunk(2, None, None), 0.82),
        (_chunk(3, None, None), 0.81),
    ]
    sect = [(_chunk(10, "2530", "informe_compilado"), 0.68)]

    embedder = MagicMock()
    embedder.embed.return_value = [0.1] * 768
    repo = MagicMock()
    repo.search_similar.side_effect = [web, sect]  # 1ª general, 2ª reserva

    store = PGVectorStore(embedder, repo, settings)
    res = store.search("q", sector_gics="2530")

    # El chunk sectorial (score 0.68) queda incluido pese a puntuar menos que los web
    ids = [r.chunk_texto for r in res]
    assert "c10" in ids
    assert len(res) == 3


# --- ingest_batched estampa sector_gics y documento_id ---


def _make_fake_reader(pages_text):
    reader = MagicMock()
    reader.metadata = {"/Title": "T", "/Author": "Ruta N"}
    pages = [MagicMock() for _ in pages_text]
    for p, t in zip(pages, pages_text):
        p.extract_text.return_value = t
    reader.pages = pages
    return reader


def test_ingest_batched_estampa_sector_y_fuente_pdf():
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

    reader = _make_fake_reader(["Contenido sectorial rico"])
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

        ingestor = mod.PdfIngestor(settings)
        ingestor.ingest_batched(
            pdf_path="/fake/pulso.pdf", sector_gics="2530",
            tipo=TipoDocumento.PDF_SECTORIAL,
        )

    assert capturado["fuente_tipo"] == "pdf"
    assert capturado["documento_id"] is not None
    assert capturado["metadatos"]["sector_gics"] == "2530"
    assert capturado["metadatos"]["tipo_fuente"] == "informe_compilado"
