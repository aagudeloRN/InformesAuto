"""Componente de interfaz Streamlit para Curacion Interactiva HITL de Competidores (Spec 007).

Permite al analista inspeccionar, desmarcar competidores no pertinentes y agregar empresas
manuales antes de ejecutar la generacion costosa del informe de Inteligencia Competitiva.
"""

from __future__ import annotations

import streamlit as st

from ic.domain.use_cases.ui_query_services import (
    add_competidor_manual,
    fetch_candidatos_competidores,
)


def render_hitl_curation_panel(
    empresa: str, sector_gics: str, ciiu: str | None = None
) -> dict[str, list[str]] | None:
    """Renderiza el panel interactivo de validacion previa HITL en Streamlit."""
    st.markdown("### 🔍 Paso 1: Curación y Validación Humana de Competidores (HITL)")
    st.info(
        "Inspeccione y ajuste la lista de competidores candidatas antes de redactar el informe. "
        "Las empresas desmarcadas quedarán excluidas de esta generación sin alterar la BD."
    )

    state_key = f"hitl_candidatos_{empresa}_{sector_gics}"
    if state_key not in st.session_state:
        st.session_state[state_key] = fetch_candidatos_competidores(empresa, sector_gics, ciiu)

    candidatos = st.session_state[state_key]
    has_candidates = any(len(v) > 0 for v in candidatos.values())

    if not has_candidates:
        st.warning(
            "No se encontraron candidatos en el KB para este sector. "
            "Puede agregar competidores manualmente abajo."
        )

    curados: dict[str, list[str]] = {"globales": [], "regionales": [], "startups": []}

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("🌍 Pares Globales (2.1.1)")
        for item in candidatos.get("globales", []):
            nombre = item["nombre"]
            checked = st.checkbox(
                f"{nombre} ({item.get('origen', 'KB')})",
                value=True,
                key=f"chk_glob_{nombre}",
            )
            if checked:
                curados["globales"].append(nombre)

    with col2:
        st.subheader("🏙️ Regionales (2.1.2)")
        for item in candidatos.get("regionales", []):
            nombre = item["nombre"]
            checked = st.checkbox(
                f"{nombre} ({item.get('origen', 'Local')})",
                value=True,
                key=f"chk_reg_{nombre}",
            )
            if checked:
                curados["regionales"].append(nombre)

    with col3:
        st.subheader("🚀 Startups (2.1.3)")
        for item in candidatos.get("startups", []):
            nombre = item["nombre"]
            checked = st.checkbox(
                f"{nombre} ({item.get('origen', 'Ecosistema')})",
                value=True,
                key=f"chk_start_{nombre}",
            )
            if checked:
                curados["startups"].append(nombre)

    st.divider()

    with st.expander("➕ Agregar Competidor Manualmente", expanded=not has_candidates):
        with st.form(key=f"form_add_manual_{empresa}"):
            f_col1, f_col2 = st.columns([3, 1])
            with f_col1:
                manual_nombre = st.text_input("Nombre de la empresa competidora")
            with f_col2:
                manual_tier = st.selectbox(
                    "Tier / Segmento", ["Globales", "Regionales", "Startups"]
                )
            submit_add = st.form_submit_button("Añadir competidor")

            if submit_add and manual_nombre.strip():
                tier_key = (
                    "globales"
                    if manual_tier == "Globales"
                    else ("regionales" if manual_tier == "Regionales" else "startups")
                )
                nuevo = add_competidor_manual(manual_nombre, manual_tier, sector_gics)
                st.session_state[state_key][tier_key].append(nuevo)
                st.success(f"Competidor '{manual_nombre}' añadido a {manual_tier}.")
                st.rerun()

    st.markdown("---")
    if st.button(
        "🚀 Confirmar competidores y generar informe", type="primary", use_container_width=True
    ):
        st.session_state[f"hitl_confirmed_{empresa}"] = curados
        return curados

    return None
