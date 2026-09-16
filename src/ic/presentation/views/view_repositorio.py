"""Vista del repositorio de documentos sectoriales."""

from __future__ import annotations

from pathlib import Path

import streamlit as st


def render_repositorio() -> None:
    """Renderiza el panel de gestion e ingesta de documentos sectoriales."""
    st.subheader("Repositorio de documentos sectoriales")
    st.caption(
        "Corpus permanente por sector GICS. Los documentos activos alimentan el retrieval "
        "de los informes; desactivar excluye sus chunks sin borrarlos."
    )

    from ic.shared.constants import TipoDocumento
    from ic.shared.constants.gics_groups import gics_options

    opciones = gics_options()
    etiqueta_por_codigo = {c: f"{c} ? {n}" for c, n in opciones}

    with st.expander("? Subir documento", expanded=False):
        from ic.domain.use_cases.ui_query_services import list_empresas_conocidas

        empresas_conocidas = list_empresas_conocidas()

        with st.form("repo_upload_form"):
            archivo = st.file_uploader("Archivo PDF", type=["pdf"])
            sector_code = st.selectbox(
                "Sector GICS *",
                options=[c for c, _ in opciones],
                format_func=lambda c: etiqueta_por_codigo.get(c, c),
            )
            empresa_sel = st.selectbox(
                "Empresa (opcional)",
                options=[eid for eid, _ in empresas_conocidas],
                format_func=lambda eid: dict(empresas_conocidas).get(eid, eid),
                help="Asociar a una empresa hace que sus docs se prioricen en sus informes.",
            )
            col_a, col_b = st.columns(2)
            tipo_opts = [
                TipoDocumento.PDF_SECTORIAL.value,
                TipoDocumento.INFORME_EMIS.value,
                TipoDocumento.PAPER_ACADEMICO.value,
            ]
            tipo_doc = col_a.selectbox("Tipo", options=tipo_opts)
            anio_doc = col_b.number_input("A?o", min_value=1990, max_value=2100, value=2026)
            autor_doc = st.text_input("Autor", value="Ruta N Medell?n")
            titulo_doc = st.text_input(
                "T?tulo", placeholder="Ej: Informe sectorial: Servicios al consumidor"
            )
            subir = st.form_submit_button("?? Ingerir documento", use_container_width=True)

        if subir:
            if archivo is None:
                st.error("Debes seleccionar un archivo PDF.")
            else:
                import tempfile
                import uuid as _uuid

                from ic.shared.config import get_settings

                settings = get_settings()
                tmp_dir = Path(tempfile.mkdtemp())
                tmp_path = tmp_dir / archivo.name
                tmp_path.write_bytes(archivo.getbuffer())
                empresa_id = _uuid.UUID(empresa_sel) if empresa_sel else None
                with st.spinner(f"Ingiriendo '{archivo.name}'?"):
                    try:
                        from ic.infrastructure.sources.pdf_ingestor import PdfIngestor

                        n = PdfIngestor(settings).ingest_batched(
                            pdf_path=str(tmp_path),
                            titulo=titulo_doc.strip() or None,
                            autor=autor_doc.strip() or None,
                            **{'a\u00f1o': int(anio_doc)},
                            sector_gics=sector_code,
                            tipo=tipo_doc,
                            empresa_id=empresa_id,
                        )
                        msg = f"? '{archivo.name}': {n} chunks ingestados (sector {sector_code})"
                        if empresa_id:
                            msg += " ? asociado a empresa."
                        st.success(msg)
                    except Exception as exc:
                        st.error(f"Error al ingerir: {exc}")

    st.markdown("### Documentos indexados")
    try:
        from ic.domain.use_cases.ui_query_services import list_documentos_indexados

        filas = list_documentos_indexados()
    except Exception as e:
        st.error(f"No se pudo consultar el repositorio: {e}")
        return

    if not filas:
        st.info("A?n no hay documentos en el repositorio.")
        return

    for fila in filas:
        estado = "??" if fila["activo"] else "?"
        with st.expander(f"{estado} {fila['nombre']} ? sector {fila['sector']}"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tipo", fila["tipo"])
            c2.metric("A?o", str(fila["a?o"]))
            c3.metric("Chunks", str(fila["n_chunks"]))
            c4.metric("Ingesta", fila["fecha"])

            col_t, col_d = st.columns(2)
            nuevo_estado = not fila["activo"]
            if col_t.button(
                "Desactivar" if fila["activo"] else "Activar",
                key=f"toggle_{fila['id']}",
                use_container_width=True,
            ):
                from ic.domain.use_cases.ui_query_services import set_documento_activo

                set_documento_activo(fila["id"], nuevo_estado)
                st.rerun()

            confirm_key = f"confirm_del_{fila['id']}"
            if col_d.button("??? Borrar", key=f"del_{fila['id']}", use_container_width=True):
                st.session_state[confirm_key] = True
            if st.session_state.get(confirm_key):
                st.warning("Esto borrar? el documento y todos sus chunks. ?Confirmas?")
                cc1, cc2 = st.columns(2)
                if cc1.button("S?, borrar", key=f"yes_{fila['id']}"):
                    from ic.domain.use_cases.ui_query_services import delete_documento_con_chunks

                    n = delete_documento_con_chunks(fila["id"])
                    st.session_state.pop(confirm_key, None)
                    st.success(f"Borrado: {n} chunks eliminados.")
                    st.rerun()
                if cc2.button("Cancelar", key=f"no_{fila['id']}"):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()
