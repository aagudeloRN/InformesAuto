"""UI Streamlit — Generador de Informes de Inteligencia Competitiva.

Inicio:
    uv run streamlit run src/ic/presentation/app.py --server.port 8503

Esta capa no contiene lógica de negocio: solo llama a GenerateInforme (domain)
y renderiza el resultado. (PRIME DIRECTIVE §1.1 — SoC)
"""

import sys
from pathlib import Path

# Asegurar que src/ está en el path al ejecutar con `streamlit run`
_src = Path(__file__).parent.parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

import logging  # noqa: E402

import streamlit as st  # noqa: E402

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# ── Configuración de página ────────────────────────────────────────────────
st.set_page_config(
    page_title="Informes IC — Ruta N",
    page_icon="📊",
    layout="centered",
)

st.title("📊 Informes de Inteligencia Competitiva")
st.caption("Sistema automatizado de generación de informes — Ruta N")

tab_gen, tab_hist, tab_repo = st.tabs(["Generar Informe", "Historial", "Repositorio"])


_PAGE_SIZE = 10


def _render_repositorio() -> None:
    st.subheader("Repositorio de documentos sectoriales")
    st.caption(
        "Corpus permanente por sector GICS. Los documentos activos alimentan el retrieval "
        "de los informes; desactivar excluye sus chunks sin borrarlos."
    )

    from ic.shared.constants import TipoDocumento
    from ic.shared.constants.gics_groups import gics_options

    opciones = gics_options()  # [(código, nombre)]
    etiqueta_por_codigo = {c: f"{c} — {n}" for c, n in opciones}

    # ── Subida ──────────────────────────────────────────────────────────────
    with st.expander("➕ Subir documento", expanded=False):
        with st.form("repo_upload_form"):
            archivo = st.file_uploader("Archivo PDF", type=["pdf"])
            sector_code = st.selectbox(
                "Sector GICS *",
                options=[c for c, _ in opciones],
                format_func=lambda c: etiqueta_por_codigo.get(c, c),
            )
            col_a, col_b = st.columns(2)
            tipo_doc = col_a.selectbox(
                "Tipo",
                options=[TipoDocumento.PDF_SECTORIAL.value, TipoDocumento.PAPER_ACADEMICO.value],
            )
            año_doc = col_b.number_input("Año", min_value=1990, max_value=2100, value=2026)
            autor_doc = st.text_input("Autor", value="Ruta N")
            titulo_doc = st.text_input(
                "Título", placeholder="Ej: Informe sectorial: Servicios al consumidor"
            )
            subir = st.form_submit_button("📥 Ingerir documento", use_container_width=True)

        if subir:
            if archivo is None:
                st.error("Debes seleccionar un archivo PDF.")
            else:
                import tempfile

                from ic.shared.config import get_settings

                settings = get_settings()
                tmp_dir = Path(tempfile.mkdtemp())
                tmp_path = tmp_dir / archivo.name
                tmp_path.write_bytes(archivo.getbuffer())
                with st.spinner(f"Ingiriendo '{archivo.name}'…"):
                    try:
                        from ic.infrastructure.sources.pdf_ingestor import PdfIngestor

                        n = PdfIngestor(settings).ingest_batched(
                            pdf_path=str(tmp_path),
                            titulo=titulo_doc.strip() or None,
                            autor=autor_doc.strip() or None,
                            año=int(año_doc),
                            sector_gics=sector_code,
                            tipo=tipo_doc,
                        )
                        st.success(
                            f"✅ '{archivo.name}': {n} chunks ingestados (sector {sector_code})."
                        )
                    except Exception as exc:
                        st.error(f"Error al ingerir: {exc}")

    # ── Listado ─────────────────────────────────────────────────────────────
    st.markdown("### Documentos indexados")
    try:
        from ic.data.database import SessionLocal
        from ic.data.repositories.documento_repo import DocumentoRepository

        with SessionLocal() as db:
            docs = DocumentoRepository(db).list_all()
            filas = [
                {
                    "id": str(d.id),
                    "nombre": d.nombre_archivo,
                    "tipo": d.tipo,
                    "sector": d.sector_gics or "—",
                    "activo": bool(d.activo),
                    "año": (d.metadatos or {}).get("año", "—"),
                    "n_chunks": (d.metadatos or {}).get("n_chunks", "—"),
                    "fecha": d.created_at.strftime("%Y-%m-%d %H:%M") if d.created_at else "—",
                }
                for d in docs
            ]
    except Exception as e:
        st.error(f"No se pudo consultar el repositorio: {e}")
        return

    if not filas:
        st.info("Aún no hay documentos en el repositorio.")
        return

    for fila in filas:
        estado = "🟢" if fila["activo"] else "⚪"
        with st.expander(f"{estado} {fila['nombre']} — sector {fila['sector']}"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tipo", fila["tipo"])
            c2.metric("Año", str(fila["año"]))
            c3.metric("Chunks", str(fila["n_chunks"]))
            c4.metric("Ingesta", fila["fecha"])

            col_t, col_d = st.columns(2)
            nuevo_estado = not fila["activo"]
            if col_t.button(
                "Desactivar" if fila["activo"] else "Activar",
                key=f"toggle_{fila['id']}",
                use_container_width=True,
            ):
                import uuid as _uuid

                with SessionLocal() as db:
                    DocumentoRepository(db).set_activo(_uuid.UUID(fila["id"]), nuevo_estado)
                st.rerun()

            confirm_key = f"confirm_del_{fila['id']}"
            if col_d.button("🗑️ Borrar", key=f"del_{fila['id']}", use_container_width=True):
                st.session_state[confirm_key] = True
            if st.session_state.get(confirm_key):
                st.warning("Esto borrará el documento y todos sus chunks. ¿Confirmas?")
                cc1, cc2 = st.columns(2)
                if cc1.button("Sí, borrar", key=f"yes_{fila['id']}"):
                    import uuid as _uuid

                    with SessionLocal() as db:
                        n = DocumentoRepository(db).delete_with_chunks(_uuid.UUID(fila["id"]))
                    st.session_state.pop(confirm_key, None)
                    st.success(f"Borrado: {n} chunks eliminados.")
                    st.rerun()
                if cc2.button("Cancelar", key=f"no_{fila['id']}"):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()


def _render_historial() -> None:
    st.subheader("Informes generados")

    filtro = st.text_input("Filtrar por empresa", key="hist_filtro", placeholder="Ej: Noel")

    if "hist_page" not in st.session_state or st.session_state.get("_hist_filtro_prev") != filtro:
        st.session_state["hist_page"] = 1
    st.session_state["_hist_filtro_prev"] = filtro

    page = st.session_state["hist_page"]
    offset = (page - 1) * _PAGE_SIZE

    try:
        from ic.data.database import SessionLocal
        from ic.data.repositories.informe_repo import InformeRepository

        with SessionLocal() as db:
            rows = InformeRepository(db).list_recientes(
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
        import csv
        import io

        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=["empresa", "fecha", "estado", "costo_usd", "tiempo_s", "n_fuentes"],
        )
        writer.writeheader()
        for inf, emp in rows:
            writer.writerow({
                "empresa": emp,
                "fecha": inf.created_at.strftime("%Y-%m-%d %H:%M") if inf.created_at else "",
                "estado": inf.estado,
                "costo_usd": f"{inf.costo_usd:.4f}" if inf.costo_usd is not None else "",
                "tiempo_s": f"{inf.tiempo_generacion_s:.0f}" if inf.tiempo_generacion_s else "",
                "n_fuentes": (inf.metricas_fiabilidad or {}).get("n_fuentes_total", ""),
            })
        st.download_button(
            label="⬇️ Exportar página a CSV",
            data=buf.getvalue().encode(),
            file_name="historial_informes.csv",
            mime="text/csv",
        )

    from ic.shared.constants import EstadoInforme

    for informe, empresa_nombre in rows:
        fecha = informe.created_at.strftime("%Y-%m-%d %H:%M") if informe.created_at else "—"
        with st.expander(f"{empresa_nombre} — {fecha}"):
            col1, col2, col3 = st.columns(3)
            col1.metric("Estado", informe.estado)
            costo = f"${informe.costo_usd:.4f}" if informe.costo_usd is not None else "—"
            col2.metric("Costo", costo)
            tiempo = (
                f"{informe.tiempo_generacion_s:.0f}s"
                if informe.tiempo_generacion_s is not None
                else "—"
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
                col_f3.metric("Citas huérfanas", n_huerfanas)
                ausencia = metricas.get("caps_ausencia", [])
                if ausencia:
                    st.caption(f"Sin evidencia suficiente: {', '.join(ausencia)}")

            if (
                informe.estado == EstadoInforme.COMPLETADO
                and informe.ruta_documento_final
            ):
                docx_path = Path(informe.ruta_documento_final)
                if docx_path.exists():
                    with open(docx_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Descargar .docx",
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
        if st.button("← Anterior", disabled=(page <= 1), key="hist_prev"):
            st.session_state["hist_page"] = page - 1
            st.rerun()
    with col_info:
        st.caption(f"Página {page}")
    with col_next:
        if st.button("Siguiente →", disabled=(len(rows) < _PAGE_SIZE), key="hist_next"):
            st.session_state["hist_page"] = page + 1
            st.rerun()


def _check_services(settings) -> tuple[bool, bool]:
    import httpx
    import sqlalchemy

    ollama_ok = False
    try:
        resp = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        ollama_ok = resp.status_code == 200
    except Exception:
        pass

    pg_ok = False
    try:
        engine = sqlalchemy.create_engine(settings.database_url)
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        engine.dispose()
        pg_ok = True
    except Exception:
        pass

    return ollama_ok, pg_ok


with tab_hist:
    _render_historial()

with tab_repo:
    _render_repositorio()

# ── Formulario ─────────────────────────────────────────────────────────────
with tab_gen:
    with st.form("informe_form"):
        empresa = st.text_input(
            "Nombre de la empresa *",
            placeholder='Ej: "Noel S.A.S."',
            help="Nombre oficial de la empresa a analizar",
        )
        ciiu = st.text_input(
            "Código CIIU (opcional)",
            placeholder="Ej: 1081",
            help="Si se omite, se intenta extraer automáticamente",
        )
        output_path = st.text_input(
            "Ruta de salida (opcional)",
            placeholder="./output/noel_informe.docx",
            help="Ruta donde se guardará el .docx. Se crea el directorio si no existe.",
        )
        submitted = st.form_submit_button("🚀 Generar informe", use_container_width=True)

    # ── Ejecución ──────────────────────────────────────────────────────────
    if submitted:
        if not empresa.strip():
            st.error("El nombre de la empresa es obligatorio.")
            st.stop()

        from ic.shared.config import get_settings

        try:
            settings = get_settings()
        except Exception as e:
            st.error(
                f"Error cargando configuración: {e}\n"
                "Verifica que el archivo `.env` esté presente."
            )
            st.stop()

        # Verificación de servicios
        with st.spinner("Verificando servicios..."):
            ollama_ok, pg_ok = _check_services(settings)

        col1, col2 = st.columns(2)
        with col1:
            if ollama_ok:
                st.success("Ollama ✅")
            else:
                st.error(f"Ollama ❌ — no disponible en {settings.ollama_base_url}")
        with col2:
            if pg_ok:
                st.success("PostgreSQL ✅")
            else:
                st.error("PostgreSQL ❌ — no disponible")

        if not ollama_ok or not pg_ok:
            st.error(
                "Uno o más servicios no están disponibles. "
                "Verifica que Ollama esté corriendo (`curl http://127.0.0.1:11434/api/tags`) "
                "y que el contenedor `repositorio_postgres` esté activo (`docker ps`)."
            )
            st.stop()

        # Barra de progreso y label de paso
        progress_bar = st.progress(0.0, text="Iniciando pipeline...")
        step_label = st.empty()

        TOTAL_PASOS = 10

        def on_step(n: int, total: int, label: str) -> None:
            progress_bar.progress(n / total, text=f"[{n}/{total}] {label}")
            step_label.markdown(f"**Paso {n}/{total}:** {label}…")

        try:
            from ic.domain.use_cases.generate_informe import GenerateInforme, InformeParams

            uc = GenerateInforme(settings)
            params = InformeParams(
                empresa=empresa.strip(),
                ciiu=ciiu.strip() or None,
                output_path=output_path.strip() or None,
            )
            result = uc.run(params, on_step=on_step)

        except Exception as exc:
            progress_bar.empty()
            step_label.empty()
            st.error(
                f"Error durante la generación: {exc}\n\n"
                "Revisa los logs de la terminal para más detalles."
            )
            st.stop()

        # ── Resultado ──────────────────────────────────────────────────────
        progress_bar.progress(1.0, text="✅ Informe completado")
        step_label.empty()

        st.success(f"✅ Informe generado: `{result.ruta_docx}`")

        docx_path = Path(result.ruta_docx)
        col_docx, col_pdf = st.columns(2)
        if docx_path.exists():
            with open(docx_path, "rb") as f:
                col_docx.download_button(
                    label="⬇️ Descargar informe .docx",
                    data=f,
                    file_name=docx_path.name,
                    mime=(
                        "application/vnd.openxmlformats-"
                        "officedocument.wordprocessingml.document"
                    ),
                    use_container_width=True,
                )
        else:
            col_docx.warning(f"El archivo no se encontró en `{result.ruta_docx}`.")

        if result.ruta_pdf and Path(result.ruta_pdf).exists():
            with open(result.ruta_pdf, "rb") as f:
                col_pdf.download_button(
                    label="⬇️ Descargar informe .pdf",
                    data=f,
                    file_name=Path(result.ruta_pdf).name,
                    mime="application/pdf",
                    use_container_width=True,
                )

        with st.expander("📊 Resumen de ejecución"):
            col_t, col_c, col_r = st.columns(3)
            col_t.metric("Tiempo total", f"{result.tiempo_total_s:.0f}s")
            col_c.metric("Costo API", f"${result.costo_usd:.4f} USD")
            col_r.metric("Referencias", str(result.n_referencias))

            if result.tokens_in or result.tokens_out:
                st.caption(
                    f"Tokens: {result.tokens_in:,} entrada / {result.tokens_out:,} salida"
                )

            if result.cost_records:
                st.markdown("**Desglose por llamada:**")
                for rec in result.cost_records:
                    st.text(
                        f"  {rec.modelo[:50]:<50}  "
                        f"in={rec.tokens_in:>7,}  out={rec.tokens_out:>6,}  ${rec.costo_usd:.4f}"
                    )
