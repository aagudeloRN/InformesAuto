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

tab_gen, tab_hist = st.tabs(["Generar Informe", "Historial"])


def _render_historial() -> None:
    st.subheader("Informes generados")
    try:
        from ic.data.database import SessionLocal
        from ic.data.repositories.informe_repo import InformeRepository

        with SessionLocal() as db:
            rows = InformeRepository(db).list_recientes(limit=20)
    except Exception as e:
        st.error(f"No se pudo consultar el historial: {e}")
        return

    if not rows:
        st.info("Aún no se han generado informes.")
        return

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
