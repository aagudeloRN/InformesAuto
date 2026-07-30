"""DT-057/T3 — NER de entidades: wrapper (parser puro, RN-001), upsert idempotente, migración.

Fast (sin spaCy real ni BD): el motor spaCy se inyecta como fake; el parseo/normalización/dedup
es puro. La integración real con spaCy se ejercita en el script de batch, no aquí.
"""

from __future__ import annotations

from ic.data.repositories.entidad_mencion_repo import EntidadMencionRepository, MencionRow
from ic.infrastructure.ner.entity_recognizer import (
    EntityMention,
    EntityRecognizer,
    detect_language,
    normalize_entity,
    parse_mentions,
)

# --- Parser puro / normalización / idioma ---


def test_normalize_entity_quita_sufijos_y_puntuacion():
    assert normalize_entity("Alpina S.A.S.") == "alpina"
    assert normalize_entity("ALPINA sas") == "alpina"
    assert normalize_entity("Grupo  Nutresa S.A.") == "grupo nutresa"
    assert normalize_entity("Colanta Ltda.") == "colanta"


def test_detect_language():
    assert detect_language("The market report of the company is strong") == "en"
    assert detect_language("El informe de mercado de la empresa es sólido") == "es"


def test_parse_mentions_solo_org_y_deduplica():
    spans = [
        ("Alpina S.A.S.", "ORG"),
        ("ALPINA sas", "ORG"),      # mismo normalizado → dedup
        ("Bogotá", "LOC"),           # descartado (lugar)
        ("Juan Valdez", "PER"),      # descartado (persona)
        ("Colanta", "MISC"),         # MISC descartado (ruido en este corpus)
    ]
    ms = parse_mentions(spans)
    norms = sorted(m.normalizada for m in ms)
    assert norms == ["alpina"]
    assert all(isinstance(m, EntityMention) for m in ms)


def test_parse_mentions_descarta_boilerplate_y_corto():
    # Boilerplate etiquetado ORG por spaCy pero que NO es empresa; y 'S.A.' → '' tras normalizar.
    spans = [("ISI Markets", "ORG"), ("the", "ORG"),
             ("All Rights Reserved", "ORG"), ("S.A.", "ORG")]
    assert parse_mentions(spans) == []


def test_parse_mentions_descarta_ocr_y_anios():
    # Artefactos: OCR con letras espaciadas y nombres con año no son empresas.
    spans = [
        ("country comparisons p a g e", "ORG"),   # OCR spacing
        ("World Energy Outlook 2025", "ORG"),      # contiene año
        ("Grupo Nutresa", "ORG"),                  # empresa real → se conserva
    ]
    ms = parse_mentions(spans)
    assert [m.normalizada for m in ms] == ["grupo nutresa"]


class _FakeEnt:
    def __init__(self, text, label):
        self.text = text
        self.label_ = label


class _FakeDoc:
    def __init__(self, ents):
        self.ents = ents


class _FakeNlp:
    """Motor NER falso: 'detecta' solo entidades realmente presentes en el texto (RN-001)."""

    def __init__(self, catalogo):
        self._catalogo = catalogo  # {texto_entidad: etiqueta}

    def __call__(self, texto):
        ents = [_FakeEnt(t, lbl) for t, lbl in self._catalogo.items() if t in texto]
        return _FakeDoc(ents)


class _Settings:
    ner_engine = "spacy"
    ner_spacy_model_en = "fake-en"
    ner_spacy_model_es = "fake-es"


def test_recognizer_extrae_solo_entidades_presentes():
    # Texto inglés → enruta a nlp_en (RN-001: solo entidades presentes).
    nlp_en = _FakeNlp({"Alpina": "ORG", "Nestlé": "ORG", "Bogotá": "LOC"})
    rec = EntityRecognizer(_Settings(), nlp_en=nlp_en)
    ms = rec.extract("The company Alpina competes in the dairy market of Colombia.")
    norms = sorted(m.normalizada for m in ms)
    # Solo Alpina está en el texto; Nestlé no aparece; Bogotá es LOC (descartada).
    assert norms == ["alpina"]


def test_recognizer_enruta_por_idioma():
    nlp_en = _FakeNlp({"English Corp": "ORG"})
    nlp_es = _FakeNlp({"Empresa Local": "ORG"})
    rec = EntityRecognizer(_Settings(), nlp_en=nlp_en, nlp_es=nlp_es)
    # Texto español → usa nlp_es (encuentra 'Empresa Local', no 'English Corp').
    ms = rec.extract("La Empresa Local es líder de mercado en el país")
    assert [m.texto for m in ms] == ["Empresa Local"]


def test_recognizer_texto_vacio():
    rec = EntityRecognizer(_Settings(), nlp_en=_FakeNlp({"X Corp": "ORG"}))
    assert rec.extract("") == []
    assert rec.extract("   ") == []


# --- Upsert idempotente ---


class _FakeResult:
    def __init__(self, rowcount):
        self.rowcount = rowcount


class _DedupSession:
    """Session falsa que simula el UNIQUE (entidad_normalizada, chunk_id) con DO NOTHING."""

    def __init__(self):
        self.claves: set[tuple[str, str]] = set()
        self.sqls: list[str] = []
        self.commits = 0

    def execute(self, sql, params=None):  # noqa: ANN001
        self.sqls.append(str(sql))
        clave = (params["entidad_normalizada"], params["chunk_id"])
        if clave in self.claves:
            return _FakeResult(0)  # conflicto → DO NOTHING
        self.claves.add(clave)
        return _FakeResult(1)

    def commit(self):
        self.commits += 1


def _fila(norm, chunk="11111111-1111-1111-1111-111111111111"):
    return MencionRow(
        entidad_normalizada=norm, entidad_texto=norm.title(), tipo="ORG",
        chunk_id=chunk, documento_id=None, sector="3020", fuente_tipo="informe_emis",
    )


def test_upsert_many_idempotente():
    sess = _DedupSession()
    repo = EntidadMencionRepository(sess)

    filas = [_fila("alpina"), _fila("nutresa")]
    n1 = repo.upsert_many(filas)
    n2 = repo.upsert_many(filas)  # segunda corrida: mismas claves → 0

    assert n1 == 2
    assert n2 == 0
    sql = sess.sqls[-1]
    assert "ON CONFLICT (entidad_normalizada, chunk_id) DO NOTHING" in sql
    assert "candidato" not in sql.lower()  # estado va por parámetro, no literal en el SQL


def test_upsert_vacio_no_escribe():
    sess = _DedupSession()
    assert EntidadMencionRepository(sess).upsert_many([]) == 0
    assert sess.commits == 0


# --- Migración idempotente ---


class _FakeConn:
    def __init__(self, sqls):
        self._sqls = sqls

    def execute(self, sql):
        self._sqls.append(str(sql))

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeEngine:
    def __init__(self):
        self.sqls: list[str] = []

    def begin(self):
        return _FakeConn(self.sqls)


def test_ensure_tabla_es_idempotente():
    from ic.data.models.entidad_mencion import ensure_entidad_menciones_table

    eng = _FakeEngine()
    ensure_entidad_menciones_table(eng)
    ensure_entidad_menciones_table(eng)  # dos veces sin error

    unido = " ".join(eng.sqls)
    assert "CREATE TABLE IF NOT EXISTS" in unido
    assert "CREATE UNIQUE INDEX IF NOT EXISTS" in unido
    assert "entidad_menciones" in unido
