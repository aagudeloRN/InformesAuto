import re
import unicodedata

_GICS_CODE_RE = re.compile(r"\(GICS (\d{4})\)")


def _normalize(texto: str) -> str:
    """Minúsculas sin acentos, para comparar nombres de grupo de forma robusta."""
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c)).strip()


# --- Granularidad de sub-sector (DT-061) ---------------------------------------------------------
# Sub-códigos GICS de 6 dígitos DENTRO del grupo 3020 (Alimentos, Bebidas y Tabaco). Sirven para
# anclar competidores de la MISMA sub-actividad (food ≠ beverages ≠ tobacco) sin re-clasificar ni
# reingerir el corpus: solo la empresa analizada (en tiempo de informe) y los pares sembrados
# verificados cargan sub_gics; los candidatos NER siguen en el grupo (3020). Puro, sin modelo.
SUB_GICS_302010_BEVERAGES = "302010"
SUB_GICS_302020_FOOD = "302020"
SUB_GICS_302030_TOBACCO = "302030"

# Mapa keyword → sub-código, evaluado por especificidad (tabaco → bebidas → alimentos). Normalizado
# (minúsculas sin acentos). Conservador: si nada matchea, devuelve None → comportamiento de grupo.
_SUB_GICS_3020_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    (SUB_GICS_302030_TOBACCO, ("tabaco", "tabacal", "cigarrillo", "cigarro", "vapeo")),
    (
        SUB_GICS_302010_BEVERAGES,
        (
            "bebida", "gaseosa", "jugo", "agua embotellada", "cerveza", "cervecer",
            "licor", "aguardiente", "ron", "vino", "refresco", "energizante", "soda",
            "destiler", "hidratante",
        ),
    ),
    (
        SUB_GICS_302020_FOOD,
        (
            "lacte", "leche", "yogur", "queso", "alimento", "aliment", "carnico",
            "carne", "snack", "galleta", "chocolate", "cafe", "panaderia", "molineria",
            "harina", "aceite", "conserva", "embutido", "helado", "confiteria", "cereal",
        ),
    ),
]


def resolve_sub_gics(descripcion: str | None, grupo_code: str | None) -> str | None:
    """Resuelve el sub-código GICS (6 dígitos) de la empresa analizada. Puro, sin modelo (ADR-002).

    Hoy solo refina el grupo 3020 (Alimentos/Bebidas/Tabaco) por keywords de la descripción; para
    cualquier otro grupo, sin descripción o sin match devuelve None → el anclaje conserva el
    comportamiento actual a nivel de grupo (invariante DT-061). No fabrica: solo mapea señales
    presentes en el texto del usuario.
    """
    if grupo_code != "3020" or not descripcion:
        return None
    objetivo = _normalize(descripcion)
    for code, keywords in _SUB_GICS_3020_KEYWORDS:
        if any(kw in objetivo for kw in keywords):
            return code
    return None


def extract_gics_code(grupo_gics: str | None) -> str | None:
    """Extrae el código GICS numérico (4 dígitos) del texto del grupo del LLM.

    Estrategia en dos pasos (el clasificador a veces devuelve solo el nombre del grupo,
    sin el "(GICS XXXX)"):
    1. Regex `\\(GICS (\\d{4})\\)` sobre el texto.
    2. Fallback: resolver el nombre del grupo contra los 25 grupos canónicos (se elige el
       nombre canónico más largo contenido en el texto, evitando falsos positivos).

    Devuelve el código como str (ej. "2530") o None si no se puede resolver.
    """
    if not grupo_gics:
        return None
    match = _GICS_CODE_RE.search(grupo_gics)
    if match:
        return match.group(1)
    objetivo = _normalize(grupo_gics)
    mejor: tuple[int, str] | None = None
    for code, nombre in gics_options():
        nombre_norm = _normalize(nombre)
        if nombre_norm and nombre_norm in objetivo:
            if mejor is None or len(nombre_norm) > mejor[0]:
                mejor = (len(nombre_norm), code)
    return mejor[1] if mejor else None


GICS_GROUPS: list[str] = [
    "Grupo 1 — Energía (GICS 1010): Corporaciones de exploración, extracción, procesamiento y "
    "logística de recursos fósiles. Incluye servicios de equipos para pozos y empresas de "
    "oil/gas/combustibles consumibles, carbón y biodiésel.",
    "Grupo 2 — Materiales (GICS 1510): Extracción y procesamiento de materias primas: químicos "
    "industriales, fertilizantes, polímeros, materiales de construcción, envases y empaques, "
    "metales y minería, papel y productos forestales.",
    "Grupo 3 — Bienes de Capital (GICS 2010): Manufactura de maquinaria e infraestructura "
    "productiva: aeroespacial y defensa, construcción e ingeniería, equipos eléctricos, "
    "conglomerados industriales, maquinaria pesada y distribuidoras B2B industriales.",
    "Grupo 4 — Servicios comerciales y profesionales (GICS 2020): Apoyo operativo a empresas y "
    "gobiernos: impresión comercial, gestión ambiental, seguridad privada, agencias de RRHH, "
    "consultoría, BPO y procesamiento de datos.",
    "Grupo 5 — Transporte (GICS 2030): Operación de redes físicas de carga y pasajeros: carga "
    "aérea/logística, aerolíneas, transporte marítimo, transporte terrestre/ferroviario e "
    "infraestructura de transporte (aeropuertos, puertos, peajes).",
    "Grupo 6 — Automóviles y componentes (GICS 2510): Manufactura de vehículos de transporte "
    "personal y sus componentes: fabricantes de automóviles, camiones ligeros, motocicletas, "
    "y proveedores de repuestos, accesorios y neumáticos.",
    "Grupo 7 — Bienes de consumo duraderos y prendas de vestir (GICS 2520): Manufactura "
    "discrecional de uso prolongado: electrónica de consumo, mobiliario, electrodomésticos, "
    "construcción residencial, equipamiento recreativo, textiles, calzado y bienes de lujo.",
    "Grupo 8 — Servicios al consumidor (GICS 2530): Hospitalidad y entretenimiento vivencial: "
    "hoteles, casinos, cruceros, restaurantes, parques, servicios educativos y cuidado personal.",
    "Grupo 9 — Distribución y venta minorista discrecional (GICS 2550): Comercialización de "
    "bienes no esenciales: distribuidores mayoristas de consumo general, grandes almacenes, "
    "hipermercados de descuento y retail especializado (moda, electrónica, mejoras del hogar).",
    "Grupo 10 — Distribución y venta minorista de productos básicos (GICS 3010): Logística y "
    "retail de bienes esenciales: farmacias, distribuidoras de alimentos B2B, supermercados e "
    "hipermercados de consumo básico diario.",
    "Grupo 11 — Alimentos, bebidas y tabaco (GICS 3020): Producción agroindustrial de alimentos "
    "envasados, carnes, lácteos, bebidas alcohólicas y no alcohólicas, y tabaco.",
    "Grupo 12 — Productos para el hogar y personales (GICS 3030): Manufactura de bienes no "
    "duraderos: detergentes, limpiadores, papel tisú, cosméticos, perfumes, pañales y "
    "suplementos dietéticos.",
    "Grupo 13 — Equipos y servicios de atención médica (GICS 3510): Dispositivos médicos, "
    "suministros hospitalarios, operadores de hospitales/laboratorios, planes de salud y "
    "software médico.",
    "Grupo 14 — Productos farmacéuticos, biotecnología y ciencias de la vida (GICS 3520): "
    "I+D farmacológico, biotecnología, manufactura de medicamentos y servicios de ensayos "
    "clínicos.",
    "Grupo 15 — Bancos (GICS 4010): Instituciones bancarias tradicionales: banca corporativa "
    "y minorista, bancos regionales, cajas de ahorro.",
    "Grupo 16 — Servicios financieros (GICS 4020): Capital markets, banca de inversión, "
    "procesamiento de pagos, finanzas al consumidor, hipotecas y gestión de activos.",
    "Grupo 17 — Seguros (GICS 4030): Emisión de pólizas y cobertura de riesgos: vida, salud, "
    "propiedad, accidentes y reaseguros.",
    "Grupo 18 — Fideicomisos de inversión inmobiliaria — REITs (GICS 6010): Vehículos legales "
    "que adquieren y operan activos inmobiliarios para distribución de rentas (oficinas, retail, "
    "logística, salud, residencial, data centers, torres de telecomunicaciones).",
    "Grupo 19 — Gestión y desarrollo inmobiliario (GICS 6020): Empresas no-REIT de desarrollo, "
    "venta y administración de bienes raíces: promotoras, operadoras y brokers inmobiliarios.",
    "Grupo 20 — Semiconductores y equipos semiconductores (GICS 4530): Diseño y manufactura "
    "de microchips, procesadores, LEDs y maquinaria para fabricación de semiconductores.",
    "Grupo 21 — Tecnología, hardware y equipos (GICS 4520): Diseño y manufactura de dispositivos "
    "electrónicos físicos: equipos de comunicación, smartphones, computadoras, servidores, "
    "componentes electrónicos y manufactura por contrato (EMS).",
    "Grupo 22 — Software y servicios (GICS 4510): Desarrollo de software de aplicación y de "
    "sistemas, consultoría TI, integración de sistemas, infraestructura de internet "
    "y data centers.",
    "Grupo 23 — Medios y entretenimiento (GICS 5020): Creación y distribución de contenido: "
    "publicidad, radiodifusión, cable, editoriales, producción de cine/música, videojuegos y "
    "plataformas digitales/redes sociales.",
    "Grupo 24 — Servicios de telecomunicaciones (GICS 5010): Operadores de conectividad: "
    "telecomunicaciones fijas (fibra, banda ancha, satélite) y telecomunicaciones inalámbricas "
    "(operadores móviles).",
    "Grupo 25 — Servicios públicos (GICS 5510): Generación y distribución de electricidad, gas, "
    "agua y energías renovables (eólica, hidráulica, biomasa, geotermia).",
]


def build_gics_prompt_block() -> str:
    return "\n\n".join(GICS_GROUPS)


def gics_options() -> list[tuple[str, str]]:
    """Devuelve (código, etiqueta) por grupo GICS para selectores de UI.

    Ej: ("2530", "Servicios al consumidor"). La etiqueta es el nombre del grupo
    (tras el guion largo, antes del paréntesis "(GICS ...)").
    """
    options: list[tuple[str, str]] = []
    for grupo in GICS_GROUPS:
        code = extract_gics_code(grupo)
        if not code:
            continue
        nombre = grupo.split("—", 1)[-1].split("(GICS", 1)[0].strip()
        options.append((code, nombre))
    return options
