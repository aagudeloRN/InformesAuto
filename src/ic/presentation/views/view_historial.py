"""Vista del historial de informes generados con desglose de competidores y feedback (US3)."""

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
        msg = "Aún no se han generado informes." if not filtro else "Sin resultados para el filtro."
        st.info(msg)
        return

    if rows and page == 1:
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=["empresa", "fecha", "estado", "costo_usd", "tiempo_s", "n_fuentes"],
        )
        writer.writeheader()
        for r in rows:
            emp = r["empresa_nombre"]
            fecha = r["fecha"]
            writer.writerow(
                {
                    "empresa": emp,
                    "fecha": fecha,
                    "estado": r["estado"],
                    "costo_usd": f"{r['costo_usd']:.4f}" if r.get("costo_usd") is not None else "",
                    "tiempo_s": f"{r['tiempo_generacion_s']:.0f}"
                    if r.get("tiempo_generacion_s")
                    else "",
                    "n_fuentes": (r.get("metricas_fiabilidad") or {}).get("n_fuentes_total", ""),
                }
            )
        st.download_button(
            label="📊 Exportar página a CSV",
            data=buf.getvalue().encode(),
            file_name="historial_informes.csv",
            mime="text/csv",
        )

    for r in rows:
        inf_id = r["id"]
        empresa_nombre = r["empresa_nombre"]
        fecha = r["fecha"]
        estado_str = str(r["estado"])

        with st.expander(f"{empresa_nombre} — {fecha}"):
            col1, col2, col3 = st.columns(3)
            col1.metric("Estado", estado_str)
            costo = f"${r['costo_usd']:.4f}" if r.get("costo_usd") is not None else "?"
            col2.metric("Costo", costo)
            tiempo = (
                f"{r['tiempo_generacion_s']:.0f}s"
                if r.get("tiempo_generacion_s") is not None
                else "?"
            )
            col3.metric("Tiempo", tiempo)

            metricas = r.get("metricas_fiabilidad") or {}
            if metricas:
                n_ok = metricas.get("n_caps_ok", "?")
                n_total = metricas.get("n_caps_total", "?")
                n_fuentes = metricas.get("n_fuentes_total", "?")
                n_huerfanas = metricas.get("n_citas_huerfanas", 0)
                col_f1, col_f2, col_f3 = st.columns(3)
                col_f1.metric("Caps con evidencia", f"{n_ok}/{n_total}")
                col_f2.metric("Fuentes citadas", n_fuentes)
                col_f3.metric("Citas huérfanas", n_huerfanas)

                if comp_used := metricas.get("competidores_utilizados"):
                    st.markdown("**Competidores anclados en Cap 2.1:**")
                    if isinstance(comp_used, dict):
                        for tier_name, lst in comp_used.items():
                            st.caption(f"• **{tier_name.capitalize()}**: {', '.join(lst)}")
                    elif isinstance(comp_used, list):
                        st.caption(f"• {', '.join(comp_used)}")

            if r.get("ruta_documento_final"):
                docx_path = Path(r["ruta_documento_final"])
                if docx_path.exists():
                    with open(docx_path, "rb") as f:
                        st.download_button(
                            label="📄 Descargar .docx",
                            data=f,
                            file_name=docx_path.name,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=inf_id,
                        )
                else:
                    st.caption(f"Archivo no encontrado: `{r['ruta_documento_final']}`")

            # Feedback de calidad / relevancia (US3 / T019)
            st.markdown("---")
            user_fb = metricas.get("user_feedback") or {}
            if current_rating := user_fb.get("rating"):
                comm = f" — {user_fb.get('comentario')}" if user_fb.get("comentario") else ""
                st.info(f"Feedback guardado: **{current_rating}**{comm}")
            else:
                st.caption("Calificación de calidad:")
                fb_col1, fb_col2 = st.columns(2)
                with fb_col1:
                    if st.button("👍 Relevante", key=f"fb_rel_{inf_id}"):
                        from ic.domain.use_cases.ui_query_services import save_informe_feedback

                        save_informe_feedback(inf_id, "Relevante")
                        st.success("Feedback guardado: Relevante")
                        st.rerun()
                with fb_col2:
                    if st.button("⚠️ Con observaciones", key=f"fb_obs_{inf_id}"):
                        st.session_state[f"show_obs_form_{inf_id}"] = True

                if st.session_state.get(f"show_obs_form_{inf_id}"):
                    with st.form(key=f"form_obs_{inf_id}"):
                        comentario = st.text_area("Observaciones sobre el informe")
                        if st.form_submit_button("Guardar observaciones"):
                            from ic.domain.use_cases.ui_query_services import (
                                save_informe_feedback,
                            )

                            save_informe_feedback(inf_id, "Con observaciones", comentario)
                            st.success("Observaciones guardadas exitosamente.")
                            st.rerun()

    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("⬅️ Anterior", disabled=(page <= 1), key="hist_prev"):
            st.session_state["hist_page"] = page - 1
            st.rerun()
    with col_info:
        st.caption(f"Página {page}")
    with col_next:
        if st.button("Siguiente ➡️", disabled=(len(rows) < _PAGE_SIZE), key="hist_next"):
            st.session_state["hist_page"] = page + 1
            st.rerun()
