from langchain_core.runnables import Runnable

from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.types import DescripcionEmpresa


class GenerateEmpresaDescription:
    def __init__(self, chain: Runnable, web_connector: WebConnector) -> None:
        self._chain = chain
        self._web_connector = web_connector

    def execute(self, nombre_empresa: str) -> DescripcionEmpresa:
        results = self._web_connector.search(f"{nombre_empresa} RUES CIIU")
        ciiu = self._web_connector.extract_ciiu(results) or "No disponible"
        texto = self._chain.invoke({"nombre_empresa": nombre_empresa, "actividad_ciiu": ciiu})
        return DescripcionEmpresa(nombre_empresa=nombre_empresa, actividad_ciiu=ciiu, texto=texto)
