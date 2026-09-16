"""Vista del historial de informes generados."""

from __future__ import annotations

import csv
import io
from pathlib import Path

import streamlit as st

_PAGE_SIZE = 10


def render_historial() -> None:
    """Renderiza el historial paginado de informes generados con descargas."""
    st.subheader("Informes generados")

    filtro = st.text_input("Filtrar por empresa", key="hist_filtro", placeholder="Ej: Noel")

    if "hist_page" not in st.session_state or st.session_state.get("_hist_filtro_prev") != filtro:
        st.session_state["hist_page"] = 1
    st.session_state["_hist_filtro_prev"] = filtro

    page = st.session_state["hist_page"]
    offset = (page - 1) * _PAGE_SIZE

    try:
        from ic.domain.use_cases.ui_query_services import list_informes_recientes

        rows = list_informes_recientes(
            limit=_PAGE_SIZE, offset=offset, empresa_filter=filtro or None
        )
    except Exception as e:
        st.error(f"No se pudo consultar el historial: {e}")
        return

    if not rows and page == 1:
        msg = "A?n no se han generado informes." if not filtro else "Sin resultados para el filtro."
        st.info(msg)
        return

    if rows and page == 1:
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=["empresa", "fecha", "estado", "costo_usd", "tiempo_s", "n_fuentes"],
        )
        writer.writeheader()
        for inf, emp in rows:
            writer.writerow(
                {
                    "empresa": emp,
                    "fecha": inf.created_at.strftime("%Y-%m-%d %H:%M") if inf.created_at else "",
                    "estado": inf.estado,
                    "costo_usd": f"{inf.costo_usd:.4f}" if inf.costo_usd is not None else "",
                    "tiempo_s": f"{inf.tiempo_generacion_s:.0f}" if inf.tiempo_generacion_s else "",
                    "n_fuentes": (inf.metricas_fiabilidad or {}).get("n_fuentes_total", ""),
                }
            )
        st.download_button(
            label="?? Exportar p?gina a CSV",
            data=buf.getvalue().encode(),
            file_name="historial_informes.csv",
            mime="text/csv",
        )

    from ic.shared.constants import EstadoInforme

    for informe, empresa_nombre in rows:
        fecha = informe.created_at.strftime("%Y-%m-%d %H:%M") if informe.created_at else "?"
        with st.expander(f"{empresa_nombre} ? {fecha}"):
            col1, col2, col3 = st.columns(3)
            col1.metric("Estado", informe.estado)
            costo = f"${informe.costo_usd:.4f}" if informe.costo_usd is not None else "?"
            col2.metric("Costo", costo)
            tiempo = (
                f"{informe.tiempo_generacion_s:.0f}s"
                if informe.tiempo_generacion_s is not None
                else "?"
            )
            col3.metric("Tiempo", tiempo)

            if metricas := informe.metricas_fiabilidad:
                n_ok = metricas.get("n_caps_ok", "?")
                n_total = metricas.get("n_caps_total", "?")
                n_fuentes = metricas.get("n_fuentes_total", "?")
                n_huerfanas = metricas.get("n_citas_huerfanas", 0)
                col_f1, col_f2, col_f3 = st.columns(3)
                col_f1.metric("Caps con evidencia", f"{n_ok}/{n_total}")
                col_f2.metric("Fuentes citadas", n_fuentes)
                col_f3.metric("Citas hu?rfanas", n_huerfanas)
                ausencia = metricas.get("caps_ausencia", [])
                if ausencia:
                    st.caption(f"Sin evidencia suficiente: {', '.join(ausencia)}")

            if informe.estado == EstadoInforme.COMPLETADO and informe.ruta_documento_final:
                docx_path = Path(informe.ruta_documento_final)
                if docx_path.exists():
                    with open(docx_path, "rb") as f:
                        st.download_button(
                            label="?? Descargar .docx",
                            data=f,
                            file_name=docx_path.name,
                            mime=(
                                "application/vnd.openxmlformats-"
                                "officedocument.wordprocessingml.document"
                            ),
                            key=str(informe.id),
                        )
                else:
                    st.caption(f"Archivo no encontrado: `{informe.ruta_documento_final}`")

    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("? Anterior", disabled=(page <= 1), key="hist_prev"):
            st.session_state["hist_page"] = page - 1
            st.rerun()
    with col_info:
        st.caption(f"P?gina {page}")
    with col_next:
        if st.button("Siguiente ?", disabled=(len(rows) < _PAGE_SIZE), key="hist_next"):
            st.session_state["hist_page"] = page + 1
            st.rerun()
