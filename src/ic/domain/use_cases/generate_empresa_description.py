from langchain_core.runnables import Runnable

from ic.domain.absent_data import build_absent_paragraph
from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.text_productos import extract_productos_servicios
from ic.shared.text_utils import format_web_results_as_context, has_cjk_characters
from ic.shared.types import DescripcionEmpresa

_MIN_CONTEXT_CHARS = 300
_SEARCH_QUERIES = [
    "{empresa} empresa Colombia descripcion historia",
    "{empresa} productos servicios portafolio sector",
    "{empresa} RUES CIIU actividad economica",
]


class GenerateEmpresaDescription:
    def __init__(self, chain: Runnable, web_connector: WebConnector) -> None:
        self._chain = chain
        self._web_connector = web_connector

    def execute(self, nombre_empresa: str) -> DescripcionEmpresa:
        all_results = []
        for query_tpl in _SEARCH_QUERIES:
            query = query_tpl.format(empresa=nombre_empresa)
            results = self._web_connector.search(query, max_results=3)
            all_results.extend(results)

        ciiu = self._web_connector.extract_ciiu(all_results) or "No disponible"
        web_context = format_web_results_as_context(all_results)

        if len(web_context) < _MIN_CONTEXT_CHARS:
            return DescripcionEmpresa(
                nombre_empresa=nombre_empresa,
                actividad_ciiu=ciiu,
                texto=build_absent_paragraph(
                    "Cap 1 — Descripción de la Empresa",
                    f"No se encontró información web suficiente sobre {nombre_empresa}",
                ),
            )

        texto = self._chain.invoke({
            "nombre_empresa": nombre_empresa,
            "actividad_ciiu": ciiu,
            "web_context": web_context,
        })

        if has_cjk_characters(texto):
            return DescripcionEmpresa(
                nombre_empresa=nombre_empresa,
                actividad_ciiu=ciiu,
                texto=build_absent_paragraph(
                    "Cap 1 — Descripción de la Empresa",
                    "El modelo generó texto en un idioma incorrecto. "
                    "Reintente con un modelo diferente (ver H5B-03: qwen3:8b o gemma3:4b)",
                ),
            )

        return DescripcionEmpresa(
            nombre_empresa=nombre_empresa,
            actividad_ciiu=ciiu,
            texto=texto,
            productos_servicios=extract_productos_servicios(texto),
        )
