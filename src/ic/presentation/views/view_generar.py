"""Vista Streamlit para la generacion de informes con soporte HITL (Spec 007)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ic.presentation.views.view_hitl import render_hitl_curation_panel
from ic.presentation.views.view_services import check_services


def render_generar() -> None:
    """Renderiza el formulario y flujo de generacion de informes."""
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

        st.divider()
        st.markdown("**Módulos del análisis**")
        st.caption("Cap 1 (Descripción) y GICS siempre se generan.")

        col_m1, col_m2 = st.columns(2)

        with col_m1:
            st.markdown("**Cap 2 — Competidores**")
            mod_hitl = st.checkbox(
                "Validación humana previa de competidores (HITL)",
                value=False,
                help="Muestra el panel interactivo para curar competidores antes de redactar.",
            )
            mod_globales = st.checkbox(
                "Descubrir globales (LLM + web)",
                value=True,
                help="Identifica líderes mundiales del sector.",
            )
            mod_local = st.checkbox(
                "Jugadores colombianos (reg. + startups)",
                value=True,
                help="Inyecta empresas locales del directorio.",
            )
            mod_det = st.checkbox(
                "Tabla 2.1 determinista desde KB",
                value=True,
                help="Ensambla la tabla de jugadores clave desde hechos del KB.",
            )

        with col_m2:
            st.markdown("**Caps 3–6**")
            mod_tend = st.checkbox("Cap 3 — Tendencias sectoriales", value=True)
            mod_eco = st.checkbox("Cap 4 — Ecosistema empresarial", value=True)
            mod_conv = st.checkbox("Cap 5 — Convergencia empresarial", value=True)
            mod_acc = st.checkbox("Cap 6 — Accionables estratégicos", value=True)

        _auto_activados: list[str] = []
        if mod_acc and not mod_conv:
            mod_conv = True
            _auto_activados.append("Cap 5 — Convergencia")
        if mod_conv and not mod_tend:
            mod_tend = True
            _auto_activados.append("Cap 3 — Tendencias")
        if mod_conv and not mod_eco:
            mod_eco = True
            _auto_activados.append("Cap 4 — Ecosistema")
        if _auto_activados:
            st.info("Auto-activados por dependencias: " + ", ".join(_auto_activados))

        st.markdown("**Calidad y Caché**")
        col_c1, col_c2 = st.columns(2)
        mod_selfreview = col_c1.checkbox("Revisión automática por capítulo", value=False)
        use_cache = col_c2.checkbox("Usar caché de capítulos", value=True)
        refresh_cache = col_c2.checkbox("Forzar regeneración completa", value=False)

        submitted = st.form_submit_button("🚀 Iniciar proceso de informe", use_container_width=True)

    curados_confirmados = None
    if submitted or st.session_state.get(f"hitl_step_{empresa}"):
        if not empresa.strip():
            st.error("El nombre de la empresa es obligatorio.")
            st.stop()

        if mod_hitl and not st.session_state.get(f"hitl_confirmed_{empresa}"):
            st.session_state[f"hitl_step_{empresa}"] = True
            curados_confirmados = render_hitl_curation_panel(
                empresa.strip(), "", ciiu.strip() or None
            )
            if curados_confirmados is None:
                return  # Espera a que el analista confirme en la UI
        else:
            curados_confirmados = st.session_state.get(f"hitl_confirmed_{empresa}")

        from ic.shared.config import get_settings

        try:
            settings = get_settings()
        except Exception as e:
            st.error(f"Error cargando configuración: {e}")
            st.stop()

        with st.spinner("Verificando servicios..."):
            ollama_ok, pg_ok = check_services(settings)

        if not ollama_ok or not pg_ok:
            st.error("Uno o más servicios no están disponibles.")
            st.stop()

        progress_bar = st.progress(0.0, text="Iniciando pipeline...")
        step_label = st.empty()

        def on_step(n: int, total: int, label: str) -> None:
            progress_bar.progress(n / total, text=f"[{n}/{total}] {label}")
            step_label.markdown(f"**Paso {n}/{total}:** {label}...")

        try:
            from ic.domain.use_cases.generate_informe import GenerateInforme, InformeParams

            uc = GenerateInforme(settings)
            _todos_caps = mod_tend and mod_eco and mod_conv and mod_acc
            caps_set: set[str] | None = (
                None
                if _todos_caps
                else {
                    c
                    for flag, c in [
                        (mod_tend, "cap3"),
                        (mod_eco, "cap4"),
                        (mod_conv, "cap5"),
                        (mod_acc, "cap6"),
                    ]
                    if flag
                }
            )
            params = InformeParams(
                empresa=empresa.strip(),
                ciiu=ciiu.strip() or None,
                output_path=output_path.strip() or None,
                use_cache=use_cache,
                refresh=refresh_cache,
                selfreview=mod_selfreview,
                discover_globales=mod_globales,
                anclaje_local=mod_local,
                seccion21_determinista=mod_det,
                caps_incluidos=caps_set,
                competidores_curados=curados_confirmados,
            )
            result = uc.run(params, on_step=on_step)

        except Exception as exc:
            progress_bar.empty()
            step_label.empty()
            st.error(f"Error durante la generación: {exc}")
            st.stop()

        progress_bar.progress(1.0, text="✅ Informe completado")
        step_label.empty()
        st.success(f"✅ Informe generado: `{result.ruta_docx}`")

        docx_path = Path(result.ruta_docx)
        col_docx, col_pdf = st.columns(2)
        if docx_path.exists():
            with open(docx_path, "rb") as f:
                col_docx.download_button(
                    label="📄 Descargar informe .docx",
                    data=f,
                    file_name=docx_path.name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )

        if result.ruta_pdf and Path(result.ruta_pdf).exists():
            with open(result.ruta_pdf, "rb") as f:
                col_pdf.download_button(
                    label="📄 Descargar informe .pdf",
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
