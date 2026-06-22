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
    "sistemas, consultoría TI, integración de sistemas, infraestructura de internet y data centers.",
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
