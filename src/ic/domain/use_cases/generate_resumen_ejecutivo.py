from langchain_core.runnables import Runnable

from ic.shared.types import ResumenEjecutivo


class GenerateResumenEjecutivo:
    def __init__(self, chain: Runnable) -> None:
        self._chain = chain

    def execute(
        self,
        nombre_empresa: str,
        descripcion_empresa: str,
        sector_gics: str,
        cap_textos: dict[str, str],
    ) -> ResumenEjecutivo:
        partes = [
            f"## {nombre}\n{texto}"
            for nombre, texto in cap_textos.items()
            if texto and texto.strip()
        ]
        contexto = "\n\n---\n\n".join(partes)

        texto = self._chain.invoke({
            "descripcion_empresa": descripcion_empresa,
            "sector_gics": sector_gics,
            "textos_capitulos": contexto,
        })

        return ResumenEjecutivo(
            texto=texto,
            n_chunks_usados=0,
            retrieval_suficiente=True,
        )
