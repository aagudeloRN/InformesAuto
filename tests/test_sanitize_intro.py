"""Tests del saneador de párrafos intro (DT-055, T22.2 Sprint B).

Verifican que `sanitize_intro` retira andamiaje/razonamiento del modelo sin fabricar
contenido (RN-001): fuga → limpio; limpio → inalterado; 100% razonamiento → "".
"""

from ic.domain.chains.chain_intro import sanitize_intro

INTRO_LIMPIO = (
    "El presente capítulo examina el posicionamiento competitivo de la empresa frente "
    "a los principales actores del sector, con foco en sus fortalezas diferenciales."
)


class TestSanitizeIntro:
    def test_intro_limpio_inalterado(self):
        assert sanitize_intro(INTRO_LIMPIO) == INTRO_LIMPIO

    def test_fuga_sofasa_meta_texto(self):
        # Caso real DT-055 (Sofasa): razonamiento en inglés + "Answer" antes del intro.
        crudo = (
            "We need to produce a paragraph intro of 2-3 sentences in Spanish.\n"
            "Answer:\n" + INTRO_LIMPIO
        )
        assert sanitize_intro(crudo) == INTRO_LIMPIO

    def test_bloque_think_eliminado(self):
        crudo = f"<think>Okay, the user wants a Spanish intro.</think>\n{INTRO_LIMPIO}"
        assert sanitize_intro(crudo) == INTRO_LIMPIO

    def test_paren_meta_suelto_eliminado(self):
        crudo = f"(In)\n{INTRO_LIMPIO}"
        assert sanitize_intro(crudo) == INTRO_LIMPIO

    def test_lineas_razonamiento_ingles_filtradas(self):
        crudo = (
            "We should contextualize the chapter.\n"
            "Let me write it now.\n"
            f"{INTRO_LIMPIO}"
        )
        assert sanitize_intro(crudo) == INTRO_LIMPIO

    def test_solo_razonamiento_devuelve_vacio(self):
        crudo = "We need to produce a paragraph intro.\nLet me think about the structure."
        assert sanitize_intro(crudo) == ""

    def test_vacio_devuelve_vacio(self):
        assert sanitize_intro("") == ""

    def test_no_fabrica_contenido(self):
        # RN-001: nunca añade texto que no estuviera en la entrada.
        salida = sanitize_intro(f"Answer: {INTRO_LIMPIO}")
        assert salida == INTRO_LIMPIO
        assert "Answer" not in salida
