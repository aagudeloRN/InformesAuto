"""DT-062 T2 — gate de corroboración web + caso de uso DiscoverGlobales.

Cubre el gate puro (``contar_corroboracion``/``es_corroborado``, fold de acentos/substring/umbral)
y la orquestación con mocks (sin Ollama/Tavily): candidato corroborado → verificado/global +
ingesta; no corroborado → candidato/fuente=llm sin ingesta (RN-001).
"""

from __future__ import annotations

from unittest.mock import MagicMock

from ic.domain.kb.corroboracion import contar_corroboracion, es_corroborado
from ic.domain.use_cases.discover_globales import DiscoverGlobales
from ic.shared.types import WebResult


class TestGateCorroboracion:
    def test_cuenta_menciones_fold_acentos(self):
        textos = ["Nestle es líder mundial", "Perfil de NESTLÉ SA", "otra cosa"]
        assert contar_corroboracion("Nestlé", textos) == 2

    def test_nombre_vacio_no_corrobora(self):
        assert contar_corroboracion("", ["cualquier texto"]) == 0

    def test_sin_menciones(self):
        assert contar_corroboracion("Fonterra", ["Danone y Nestlé"]) == 0

    def test_sufijos_societarios_no_dan_falso_negativo(self):
        # Regresión (E2E 3020): el LLM emite "JBS S.A." / "Tyson Foods, Inc."; la web dice "JBS" /
        # "Tyson Foods". Se matchea el núcleo, no la forma legal literal.
        assert contar_corroboracion("JBS S.A.", [
            "JBS is the world's largest meat company", "Report on JBS 2025",
        ]) == 2
        assert contar_corroboracion("Tyson Foods, Inc.", [
            "Tyson Foods reported revenue", "perfil de tyson foods",
        ]) == 2

    def test_match_por_limite_de_palabra(self):
        # "jbs" no debe casar dentro de otra palabra ("jbservice").
        assert contar_corroboracion("JBS S.A.", ["jbservice unrelated"]) == 0

    def test_umbral(self):
        assert es_corroborado(2, 2) is True
        assert es_corroborado(3, 2) is True
        assert es_corroborado(1, 2) is False


def _web(content: str, url: str = "https://e.com/x") -> WebResult:
    return WebResult(
        url=url, title="Perfil", content=content, snippet="s",
        metadatos={"titulo": "Perfil", "año": "2025", "autor": None},
    )


class TestDiscoverGlobales:
    def _run(self, *, llm_json: str, web_content_por_query, min_corrob: int = 2):
        chain = MagicMock()
        chain.invoke.return_value = llm_json
        web = MagicMock()
        web.search.side_effect = lambda q, **_: [
            _web(c, f"https://e.com/{i}")
            for i, c in enumerate(web_content_por_query(q))
        ]
        store = MagicMock()
        seed = MagicMock()
        conteos = DiscoverGlobales(
            chain=chain, web_connector=web, store=store, min_corrob=min_corrob,
        ).discover(
            sector_gics="Alimentos", productos="lácteos, leche, yogurt", seed_repo_fn=seed
        )
        return conteos, store, seed

    def test_corroborado_siembra_verificado_e_ingiere(self):
        # 2 resultados mencionan "Nestlé" → ≥ min_corrob (2) → corroborado.
        conteos, store, seed = self._run(
            llm_json='["Nestlé"]',
            web_content_por_query=lambda q: ["Perfil de Nestlé", "Nestlé revenue 2025"],
        )
        assert conteos == {"recomendados": 1, "corroborados": 1, "no_corroborados": 0}
        store.ingest.assert_called_once()
        seed.assert_called_once()
        nombre, corroborado, hits = seed.call_args.args
        assert nombre == "Nestlé" and corroborado is True and hits == 2

    def test_no_corroborado_siembra_candidato_sin_ingesta(self):
        # Solo 1 mención (< min_corrob) → no corroborado: candidato, sin ingesta (RN-001).
        conteos, store, seed = self._run(
            llm_json='["Marca Inventada"]',
            web_content_por_query=lambda q: ["Marca Inventada aparece una vez", "ruido"],
        )
        assert conteos == {"recomendados": 1, "corroborados": 0, "no_corroborados": 1}
        store.ingest.assert_not_called()
        nombre, corroborado, hits = seed.call_args.args
        assert nombre == "Marca Inventada" and corroborado is False and hits == 1

    def test_sin_candidatos_no_busca_ni_siembra(self):
        conteos, store, seed = self._run(
            llm_json="[]", web_content_por_query=lambda q: [],
        )
        assert conteos == {"recomendados": 0, "corroborados": 0, "no_corroborados": 0}
        store.ingest.assert_not_called()
        seed.assert_not_called()


class TestInvarianteFlag:
    """El descubrimiento debe llegar apagado por defecto: flag OFF = anclaje DT-061b (solo semilla
    curada). generate_n1._fn_cap2 solo lo ejecuta bajo `if s.discover_globales_enabled`; que el
    default sea False es la garantía de la invariante (evita shippear el motor encendido)."""

    def test_flag_off_por_defecto(self):
        # Se comprueba el default declarado (sin instanciar Settings, que exige campos del .env).
        from ic.shared.config import Settings

        campos = Settings.model_fields
        assert campos["discover_globales_enabled"].default is False
        assert campos["discover_globales_min_corrob"].default == 2
