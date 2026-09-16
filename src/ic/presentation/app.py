"""UI Streamlit ? Generador de Informes de Inteligencia Competitiva.

Ejecutar con:
    uv run streamlit run src/ic/presentation/app.py
"""

from __future__ import annotations

import streamlit as st

from ic.presentation.views.view_generar import render_generar
from ic.presentation.views.view_historial import render_historial
from ic.presentation.views.view_repositorio import render_repositorio

st.set_page_config(
    page_title="InformesAuto ? Inteligencia Competitiva",
    page_icon="??",
    layout="wide",
)

st.title("?? Generador de Informes de Inteligencia Competitiva")
st.caption("Generaci?n automatizada de informes estrat?gicos con evidencia y trazabilidad.")

tab_gen, tab_hist, tab_repo = st.tabs(
    ["?? Nuevo informe", "?? Historial", "??? Repositorio sectorial"]
)

with tab_hist:
    render_historial()

with tab_repo:
    render_repositorio()

with tab_gen:
    render_generar()
