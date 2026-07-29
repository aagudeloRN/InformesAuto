"""Tests de contrato APA 7 para format_reference() y funciones auxiliares (T10.3/T10.4)."""

from ic.infrastructure.citation.apa_formatter import (
    CitationMetadata,
    build_references_section,
    find_orphan_citations,
    format_chunks_with_meta,
    format_reference,
    strip_orphan_citations,
)
from ic.shared.types import ChunkResult, Referencia


def _meta(
    titulo="Título de prueba",
    fuente_nombre="Sitio Ejemplo",
    año="2024",
    autor=None,
    url=None,
    fecha_acceso=None,
) -> CitationMetadata:
    return CitationMetadata(
        titulo=titulo,
        fuente_nombre=fuente_nombre,
        año=año,
        autor=autor,
        url=url,
        fecha_acceso=fecha_acceso,
    )


def _chunk(
    texto="Texto de prueba.",
    fuente_tipo="web",
    url=None,
    autor=None,
    año=None,
    titulo=None,
    fuente_nombre=None,
) -> ChunkResult:
    meta: dict = {}
    if autor:
        meta["autor"] = autor
    if año:
        meta["año"] = año
    if titulo:
        meta["titulo"] = titulo
    if fuente_nombre:
        meta["fuente_nombre"] = fuente_nombre
    return ChunkResult(
        chunk_texto=texto,
        fuente_tipo=fuente_tipo,
        fuente_url=url,
        score=0.9,
        metadatos=meta or None,
    )


# ── T10.3: format_reference por tipo de fuente ────────────────────────────


class TestFormatReferenceWeb:
    def test_org_con_url(self):
        meta = _meta(
            autor=None,
            fuente_nombre="Fortune Business Insights",
            año="2026",
            titulo="Global Food Market Report",
            url="https://fortunebusinessinsights.com/report",
        )
        ref = format_reference(meta, fuente_tipo="web")
        assert "Fortune Business Insights" in ref.apa_string
        assert "(2026)" in ref.apa_string
        assert "*Global Food Market Report*" in ref.apa_string
        assert "https://fortunebusinessinsights.com/report" in ref.apa_string

    def test_persona_con_url(self):
        meta = _meta(
            autor="García, J.",
            fuente_nombre="El Espectador",
            año="2025",
            titulo="Industria alimentaria en Colombia",
            url="https://elespectador.com/economia/articulo",
        )
        ref = format_reference(meta, fuente_tipo="web")
        assert ref.autor == "García, J."
        assert "(2025)" in ref.apa_string
        assert "*Industria alimentaria en Colombia*" in ref.apa_string

    def test_sin_url_sin_fecha_acceso(self):
        meta = _meta(año="s.f.", url=None)
        ref = format_reference(meta, fuente_tipo="web")
        assert "(s.f.)" in ref.apa_string
        assert "Recuperado" not in ref.apa_string

    def test_fecha_acceso_solo_cuando_sin_año(self):
        meta = _meta(año="s.f.", url="https://ejemplo.com", fecha_acceso="15 de julio de 2026")
        ref = format_reference(meta, fuente_tipo="web")
        assert "Recuperado el 15 de julio de 2026" in ref.apa_string

    def test_fecha_acceso_omitida_cuando_hay_año(self):
        meta = _meta(año="2024", url="https://ejemplo.com", fecha_acceso="1 de enero de 2025")
        ref = format_reference(meta, fuente_tipo="web")
        assert "Recuperado el" not in ref.apa_string


class TestFormatReferenceOpenAlex:
    def test_articulo_academico(self):
        meta = _meta(
            autor="Martínez, A.",
            fuente_nombre="Journal of Food Science",
            año="2023",
            titulo="Tendencias en procesamiento de alimentos",
            url="https://doi.org/10.1234/jfs.2023.001",
        )
        ref = format_reference(meta, fuente_tipo="openalex")
        assert "Martínez, A." in ref.apa_string
        assert "(2023)" in ref.apa_string
        assert "*Tendencias en procesamiento de alimentos*" in ref.apa_string
        assert "*Journal of Food Science*" in ref.apa_string
        assert "https://doi.org" in ref.apa_string
        assert "[Informe]" not in ref.apa_string

    def test_sin_autor_usa_fuente_nombre(self):
        meta = _meta(autor=None, fuente_nombre="OpenAlex", año="2022", titulo="Artículo sin autor")
        ref = format_reference(meta, fuente_tipo="openalex")
        assert ref.autor == "OpenAlex"
        assert "(2022)" in ref.apa_string


class TestFormatReferencePdf:
    def test_informe_sectorial(self):
        meta = _meta(
            autor="Alcaldía de Medellín",
            fuente_nombre="Alcaldía de Medellín",
            año="2026",
            titulo="Informe de Convergencia Local Medellín 2026",
            url=None,
        )
        ref = format_reference(meta, fuente_tipo="pdf")
        assert "Alcaldía de Medellín" in ref.apa_string
        assert "(2026)" in ref.apa_string
        assert "*Informe de Convergencia Local Medellín 2026*" in ref.apa_string
        assert "[Informe]" in ref.apa_string

    def test_pdf_con_url(self):
        meta = _meta(
            autor="EMIS",
            fuente_nombre="EMIS",
            año="2025",
            titulo="Sector Alimentos Colombia",
            url="https://emis.com/informe.pdf",
        )
        ref = format_reference(meta, fuente_tipo="pdf")
        assert "[Informe]" in ref.apa_string
        assert "https://emis.com/informe.pdf" in ref.apa_string


# ── T10.3: build_references_section ───────────────────────────────────────


class TestBuildReferencesSection:
    def test_deduplicacion_por_url(self):
        chunks = [
            _chunk(texto="A", url="https://ejemplo.com/a", fuente_tipo="web"),
            _chunk(texto="B", url="https://ejemplo.com/a", fuente_tipo="web"),
        ]
        refs = build_references_section(chunks)
        assert len(refs) == 1

    def test_orden_alfabetico(self):
        chunks = [
            _chunk(texto="Z", fuente_nombre="Zebra Corp", año="2024", fuente_tipo="web",
                   url="https://z.com"),
            _chunk(texto="A", fuente_nombre="Alfa Corp", año="2024", fuente_tipo="web",
                   url="https://a.com"),
        ]
        refs = build_references_section(chunks)
        assert refs[0].autor.lower() < refs[1].autor.lower()

    def test_tipo_openalex_pasa_al_formatter(self):
        chunks = [_chunk(fuente_tipo="openalex", url="https://openalex.org/W123")]
        refs = build_references_section(chunks)
        assert len(refs) == 1
        assert "[Informe]" not in refs[0].apa_string

    def test_tipo_pdf_pasa_al_formatter(self):
        chunks = [_chunk(fuente_tipo="pdf", url=None)]
        refs = build_references_section(chunks)
        assert len(refs) == 1
        assert "[Informe]" in refs[0].apa_string


# ── T10.2: find_orphan_citations ──────────────────────────────────────────


class TestFindOrphanCitations:
    def _ref(self, autor: str, año: str = "2024") -> Referencia:
        return Referencia(
            clave=f"{autor}{año}",
            autor=autor,
            año=año,
            titulo="Título",
            fuente="Fuente",
            url=None,
            apa_string=f"{autor}. ({año}).",
        )

    def test_texto_sin_citas(self):
        refs = [self._ref("García, J.")]
        assert find_orphan_citations("Texto sin ninguna cita.", refs) == []

    def test_cita_que_coincide(self):
        refs = [self._ref("Fortune Business Insights", "2026")]
        texto = "Según el análisis (Fortune Business Insights, 2026), el mercado crece."
        assert find_orphan_citations(texto, refs) == []

    def test_cita_huerfana(self):
        refs = [self._ref("García, J.", "2024")]
        texto = "El estudio (Martínez, A., 2023) muestra resultados positivos."
        orphans = find_orphan_citations(texto, refs)
        assert len(orphans) == 1
        assert "Martínez, A." in orphans[0]

    def test_mezcla_validas_y_huerfanas(self):
        refs = [self._ref("García, J.", "2024"), self._ref("López, M.", "2025")]
        texto = (
            "García (García, J., 2024) y una huérfana (Autor Desconocido, 2022) "
            "y López (López, M., 2025)."
        )
        orphans = find_orphan_citations(texto, refs)
        assert len(orphans) == 1
        assert "Autor Desconocido" in orphans[0]

    def test_deduplicacion_de_orphans(self):
        refs = [self._ref("García, J.")]
        texto = "(Desconocido, 2020) y otra vez (Desconocido, 2020)."
        orphans = find_orphan_citations(texto, refs)
        assert len(orphans) == 1

    def test_matcheo_parcial_nombre(self):
        refs = [self._ref("Fortune Business Insights", "2026")]
        texto = "Según (Fortune Business Insights, 2026) crece."
        assert find_orphan_citations(texto, refs) == []


# ── T22.A2 (DT-052): strip_orphan_citations ───────────────────────────────


class TestStripOrphanCitations:
    def _ref(self, autor: str, año: str = "2024") -> Referencia:
        return Referencia(
            clave=f"{autor}{año}", autor=autor, año=año, titulo="Título",
            fuente="Fuente", url=None, apa_string=f"{autor}. ({año}).",
        )

    def test_suprime_huerfana_y_conserva_valida(self):
        refs = [self._ref("Euromonitor", "2024")]
        texto = "El líder (Euromonitor, 2024) domina; una huérfana (Carvajal, 2019) aquí."
        saneado, n = strip_orphan_citations(texto, refs)
        assert n == 1
        assert "(Euromonitor, 2024)" in saneado
        assert "Carvajal" not in saneado
        # Tras suprimir, no quedan huérfanas.
        assert find_orphan_citations(saneado, refs) == []

    def test_cita_multientidad_malformada_se_suprime(self):
        # La huérfana real del A/B: (Alpina, Carvajal Empaques, 2019).
        refs = [self._ref("Euromonitor", "2024")]
        texto = "Dato de mercado (Alpina, Carvajal Empaques, 2019) sin respaldo."
        saneado, n = strip_orphan_citations(texto, refs)
        assert n == 1
        assert "Carvajal Empaques" not in saneado

    def test_sin_huerfanas_no_cambia_conteo(self):
        refs = [self._ref("García, J.", "2024")]
        texto = "Según (García, J., 2024) el sector crece."
        saneado, n = strip_orphan_citations(texto, refs)
        assert n == 0
        assert saneado == texto

    def test_no_deja_espacio_sobrante(self):
        refs = [self._ref("Euromonitor", "2024")]
        texto = "El mercado creció (Fantasma, 2020) según fuentes."
        saneado, _ = strip_orphan_citations(texto, refs)
        assert "  " not in saneado
        assert " ." not in saneado


# ── T22.A2 (DT-052): contrato chunks_usados → Referencias ──────────────────


class TestChunksToRefsContract:
    def _pdf_chunk(self, url: str, titulo: str, autor: str) -> ChunkResult:
        return ChunkResult(
            chunk_texto=f"Contenido de {titulo}.", fuente_tipo="pdf", fuente_url=url,
            score=0.8, metadatos={"titulo": titulo, "autor": autor, "año": "2024"},
        )

    def test_n_docs_distintos_producen_n_referencias(self):
        # 5 documentos EMIS distintos (por URL) → 5 referencias, sin colapsar.
        chunks = [
            self._pdf_chunk(f"/emis/doc_{i}.pdf", f"Informe {i}", f"Publisher {i}")
            for i in range(5)
        ]
        # Añadir chunks repetidos del mismo doc no debe inflar las referencias.
        chunks.append(self._pdf_chunk("/emis/doc_0.pdf", "Informe 0", "Publisher 0"))
        refs = build_references_section(chunks)
        assert len(refs) == 5

    def test_texto_saneado_sin_huerfanas_contra_refs_reales(self):
        chunks = [self._pdf_chunk("/emis/a.pdf", "Capsule", "Euromonitor")]
        refs = build_references_section(chunks)
        texto = "Cita válida (Euromonitor, 2024) y una inventada (Inexistente, 2010)."
        saneado, n = strip_orphan_citations(texto, refs)
        assert n == 1
        assert find_orphan_citations(saneado, refs) == []


# ── T10.2: format_chunks_with_meta ────────────────────────────────────────


class TestFormatChunksWithMeta:
    def test_incluye_autor_y_año(self):
        chunks = [
            _chunk(texto="Texto del chunk.", autor="García, J.", año="2024",
                   url="https://ejemplo.com", fuente_tipo="web"),
        ]
        resultado = format_chunks_with_meta(chunks)
        assert "[1]" in resultado
        assert "García, J., 2024" in resultado
        assert "https://ejemplo.com" in resultado

    def test_sin_autor_usa_fuente_nombre(self):
        chunks = [
            _chunk(texto="Texto.", fuente_nombre="Sitio Web", año="2023",
                   url=None, fuente_tipo="web"),
        ]
        resultado = format_chunks_with_meta(chunks)
        assert "Sitio Web, 2023" in resultado

    def test_multiples_chunks_separados(self):
        chunks = [
            _chunk(texto="Chunk A.", url="https://a.com", fuente_tipo="web"),
            _chunk(texto="Chunk B.", url="https://b.com", fuente_tipo="web"),
        ]
        resultado = format_chunks_with_meta(chunks)
        assert "[1]" in resultado
        assert "[2]" in resultado
        assert "---" in resultado
