"""Genera documentos_sectoriales/FuentesEMIS/indice_emis.csv desde los PDFs EMIS (Fase 18, T18.4).

Parsea el nombre de archivo `Autor. (Año). Título.pdf` → campos APA.
Genera columna `sectores_adicionales` (separada por `|`) editable a mano para docs multi-sector.

Uso:
    uv run python scripts/build_emis_index.py
    uv run python scripts/build_emis_index.py \
        --dir documentos_sectoriales/FuentesEMIS --out indice_emis.csv

Idempotente: si el CSV ya existe lo REEMPLAZA (ejecutar cada vez que se añadan docs).
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("build_emis_index")

# Mapeo carpeta → código GICS (25 grupos estándar)
_CARPETA_A_GICS: dict[str, str] = {
    "AlimentosBebidasTabaco": "3020",
    "AutomobilesComponentes": "2510",
    "Bancos": "4010",
    "BienesCapital": "2010",
    "BienesConsumoPrendas": "2520",
    "DistribucionVentaMinorista": "2550",
    "Energia": "1010",
    "EquiposAtencionMedica": "3510",
    "FideicomisosInversionMobiliaria": "6010",
    "GestionDesarrolloMobiliario": "6020",
    "Materiales": "1510",
    "MediosEntretenimiento": "2530",
    "MinoristaBasicosConsumo": "3030",
    "ProductosFarmaceuticos": "3520",
    "ProductosHogarPersonales": "3010",
    "Seguros": "4030",
    "SemiconductoresEquipos": "4530",
    "ServiciosComercialesProfesionales": "2020",
    "ServiciosConsumidor": "2530",
    "ServiciosFinancieros": "4020",
    "ServiciosPublicos": "5510",
    "ServiciosTelecomunicaciones": "5010",
    "SoftwareServicios": "4510",
    "TecnologiaHardwareEquipos": "4520",
    "Transporte": "2030",
}

# Patrón: "Autor. (Año). Título" o "Autor. (Año)  Título" (algunos sin punto tras año)
_PAT = re.compile(r"^(?P<autor>.+?)\.\s+\((?P<año>\d{4})\)[.)]?\s+(?P<titulo>.+)$")


def _parse_filename(stem: str) -> tuple[str, str, str]:
    """Extrae (autor, año, titulo) del stem del archivo. Fallback si no parsea."""
    m = _PAT.match(stem.strip())
    if m:
        return m.group("autor").strip(), m.group("año").strip(), m.group("titulo").strip()
    # Fallback: todo es el título
    return "Desconocido", "s.f.", stem.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera índice CSV del corpus EMIS")
    parser.add_argument(
        "--dir",
        default="documentos_sectoriales/FuentesEMIS",
        help="Carpeta raíz con subcarpetas por sector",
    )
    parser.add_argument(
        "--out",
        default="documentos_sectoriales/FuentesEMIS/indice_emis.csv",
        help="Ruta de salida del CSV",
    )
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    if not root.exists():
        logger.error("Carpeta no encontrada: %s", root)
        return 1

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = Path.cwd() / out_path
    out_path = out_path.resolve()

    filas: list[dict] = []
    sin_gics: list[str] = []

    for carpeta in sorted(root.iterdir()):
        if not carpeta.is_dir():
            continue
        gics = _CARPETA_A_GICS.get(carpeta.name)
        if gics is None:
            sin_gics.append(carpeta.name)
            logger.warning("Carpeta sin mapeo GICS: %s — se omite", carpeta.name)
            continue
        for pdf in sorted(carpeta.glob("*.pdf")):
            autor, año, titulo = _parse_filename(pdf.stem)
            # ruta relativa desde la raíz del repo (sin prefijo documentos_sectoriales/)
            rel = pdf.relative_to(root.parent)
            filas.append(
                {
                    "archivo": str(rel),
                    "sector_gics": gics,
                    "sectores_adicionales": "",  # editable a mano para docs multi-sector
                    "tipo": "INFORME_EMIS",
                    "autor": autor,
                    "año": año,
                    "titulo": titulo,
                    "empresa": "",
                }
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "archivo",
                "sector_gics",
                "sectores_adicionales",
                "tipo",
                "autor",
                "año",
                "titulo",
                "empresa",
            ],
        )
        writer.writeheader()
        writer.writerows(filas)

    logger.info("Generado %s — %d documentos", out_path, len(filas))
    if sin_gics:
        logger.warning("Carpetas sin mapeo GICS (revisar _CARPETA_A_GICS): %s", sin_gics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
