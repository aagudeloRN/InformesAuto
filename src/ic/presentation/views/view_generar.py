"""Vista principal de generacion de informes con HITL."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

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
            "C?digo CIIU (opcional)",
            placeholder="Ej: 1081",
            help="Si se omite, se intenta extraer autom?ticamente",
        )
        output_path = st.text_input(
            "Ruta de salida (opcional)",
            placeholder="./output/noel_informe.docx",
            help="Ruta donde se guardar? el .docx. Se crea el directorio si no existe.",
        )

        st.divider()
        st.markdown("**M?dulos del an?lisis**")
        st.caption(
            "Cap 1 (Descripci?n) y GICS siempre se generan ? son la base de todo el pipeline."
        )

        col_m1, col_m2 = st.columns(2)

        with col_m1:
            st.markdown("**Cap 2 ? Competidores**")
            mod_globales = st.checkbox(
                "Descubrir globales (LLM + web)",
                value=True,
                help="Identifica l?deres mundiales del sector y los corrobora en web (?2 fuentes).",
            )
            mod_local = st.checkbox(
                "Jugadores colombianos (reg. + startups)",
                value=True,
                help="Inyecta empresas locales del directorio como regionales y startups.",
            )
            mod_det = st.checkbox(
                "Tabla 2.1 determinista desde KB",
                value=True,
                help="Ensambla la tabla de jugadores clave desde hechos verificados del KB.",
            )

        with col_m2:
            st.markdown("**Caps 3?6**")
            mod_tend = st.checkbox("Cap 3 ? Tendencias sectoriales", value=True)
            mod_eco = st.checkbox("Cap 4 ? Ecosistema empresarial", value=True)
            mod_conv = st.checkbox("Cap 5 ? Convergencia empresarial", value=True)
            mod_acc = st.checkbox("Cap 6 ? Accionables estrat?gicos", value=True)

        _auto_activados: list[str] = []
        if mod_acc and not mod_conv:
            mod_conv = True
            _auto_activados.append("Cap 5 ? Convergencia (requerida por Cap 6)")
        if mod_conv and not mod_tend:
            mod_tend = True
            _auto_activados.append("Cap 3 ? Tendencias (requerida por Cap 5)")
        if mod_conv and not mod_eco:
            mod_eco = True
            _auto_activados.append("Cap 4 ? Ecosistema (requerido por Cap 5)")
        if _auto_activados:
            st.info("Auto-activados por dependencias del DAG: " + ", ".join(_auto_activados))

        st.markdown("**Calidad**")
        mod_selfreview = st.checkbox(
            "Revisi?n autom?tica por cap?tulo",
            value=False,
            help="Loop generar?juez?revisar sobre cada cap?tulo.",
        )

        st.divider()
        st.markdown("**Opciones de cach?**")
        col_c1, col_c2 = st.columns(2)
        use_cache = col_c1.checkbox(
            "Usar cach? de cap?tulos",
            value=True,
            help="Reutiliza cap?tulos ya generados para esta empresa.",
        )
        refresh_cache = col_c2.checkbox(
            "Forzar regeneraci?n completa",
            value=False,
            help="Invalida el cach? y regenera todo desde cero.",
        )

        submitted = st.form_submit_button("?? Generar informe", use_container_width=True)

    if submitted:
        if not empresa.strip():
            st.error("El nombre de la empresa es obligatorio.")
            st.stop()

        from ic.shared.config import get_settings

        try:
            settings = get_settings()
        except Exception as e:
            st.error(
                f"Error cargando configuraci?n: {e}\nVerifica que el archivo `.env` est? presente."
            )
            st.stop()

        with st.spinner("Verificando servicios..."):
            ollama_ok, pg_ok = check_services(settings)

        col1, col2 = st.columns(2)
        with col1:
            if ollama_ok:
                st.success("Ollama ?")
            else:
                st.error(f"Ollama ? ? no disponible en {settings.ollama_base_url}")
        with col2:
            if pg_ok:
                st.success("PostgreSQL ?")
            else:
                st.error("PostgreSQL ? ? no disponible")

        if not ollama_ok or not pg_ok:
            st.error("Uno o m?s servicios no est?n disponibles.")
            st.stop()

        progress_bar = st.progress(0.0, text="Iniciando pipeline...")
        step_label = st.empty()

        def on_step(n: int, total: int, label: str) -> None:
            progress_bar.progress(n / total, text=f"[{n}/{total}] {label}")
            step_label.markdown(f"**Paso {n}/{total}:** {label}?")

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
            )
            result = uc.run(params, on_step=on_step)

        except Exception as exc:
            progress_bar.empty()
            step_label.empty()
            st.error(f"Error durante la generaci?n: {exc}")
            st.stop()

        progress_bar.progress(1.0, text="? Informe completado")
        step_label.empty()
        st.success(f"? Informe generado: `{result.ruta_docx}`")

        docx_path = Path(result.ruta_docx)
        col_docx, col_pdf = st.columns(2)
        if docx_path.exists():
            with open(docx_path, "rb") as f:
                col_docx.download_button(
                    label="?? Descargar informe .docx",
                    data=f,
                    file_name=docx_path.name,
                    mime=(
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    ),
                    use_container_width=True,
                )
        else:
            col_docx.warning(f"El archivo no se encontr? en `{result.ruta_docx}`.")

        if result.ruta_pdf and Path(result.ruta_pdf).exists():
            with open(result.ruta_pdf, "rb") as f:
                col_pdf.download_button(
                    label="?? Descargar informe .pdf",
                    data=f,
                    file_name=Path(result.ruta_pdf).name,
                    mime="application/pdf",
                    use_container_width=True,
                )

        with st.expander("?? Resumen de ejecuci?n"):
            col_t, col_c, col_r = st.columns(3)
            col_t.metric("Tiempo total", f"{result.tiempo_total_s:.0f}s")
            col_c.metric("Costo API", f"${result.costo_usd:.4f} USD")
            col_r.metric("Referencias", str(result.n_referencias))

            if result.tokens_in or result.tokens_out:
                st.caption(f"Tokens: {result.tokens_in:,} entrada / {result.tokens_out:,} salida")
